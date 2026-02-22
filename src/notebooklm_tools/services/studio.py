"""Studio service — artifact creation, status, rename, delete.

Centralizes:
- Artifact type validation
- Constants code resolution (audio/video/slide/infographic/flashcard formats)
- Source ID resolution (fetch all when none provided)
- Mind map two-step pattern (generate → save)
- Result validation (artifact_id exists)
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Optional, TypedDict

from notebooklm_tools.core import constants
from .errors import ServiceError, ValidationError

if TYPE_CHECKING:
    from notebooklm_tools.core.client import NotebookLMClient

# ---------- Constants ----------

VALID_ARTIFACT_TYPES = frozenset([
    "audio", "video", "infographic", "slide_deck", "report",
    "flashcards", "quiz", "data_table", "mind_map",
])


# ---------- TypedDicts ----------

class CreateResult(TypedDict):
    """Result of creating a studio artifact."""
    artifact_type: str
    artifact_id: str
    status: str
    message: str


class MindMapResult(TypedDict):
    """Result of creating a mind map."""
    artifact_type: str
    artifact_id: str
    title: str
    root_name: str
    children_count: int
    message: str


class ArtifactInfo(TypedDict, total=False):
    """Studio artifact info."""
    artifact_id: str
    type: str
    title: str
    status: str
    created_at: Optional[str]
    url: Optional[str]


class StatusResult(TypedDict):
    """Result of polling studio status."""
    artifacts: list[ArtifactInfo]
    total: int
    completed: int
    in_progress: int


class RenameResult(TypedDict):
    """Result of renaming an artifact."""
    artifact_id: str
    new_title: str


# ---------- Validation ----------

def validate_artifact_type(artifact_type: str) -> None:
    """Validate that artifact_type is one of the supported types.

    Raises:
        ValidationError: If artifact_type is invalid
    """
    if artifact_type not in VALID_ARTIFACT_TYPES:
        raise ValidationError(
            f"Unknown artifact type '{artifact_type}'. "
            f"Valid types: {', '.join(sorted(VALID_ARTIFACT_TYPES))}",
        )


def resolve_code(mapper: constants.CodeMapper, name: str, label: str) -> int:
    """Resolve a human-readable name to an integer code via constants.CodeMapper.

    Args:
        mapper: The CodeMapper instance (e.g. constants.AUDIO_FORMATS)
        name: The name to resolve (e.g. "deep_dive")
        label: Human-readable label for error messages (e.g. "audio format")

    Returns:
        The integer code

    Raises:
        ValidationError: If name is unknown
    """
    try:
        return mapper.get_code(name)
    except ValueError:
        raise ValidationError(
            f"Unknown {label} '{name}'. Valid options: {', '.join(mapper.names)}",
        )


def _resolve_source_ids(
    client: "NotebookLMClient",
    notebook_id: str,
    source_ids: Optional[list[str]],
) -> list[str]:
    """Resolve source IDs: use provided list or fetch all from notebook.

    Raises:
        ServiceError: If no sources found in notebook
    """
    if source_ids:
        return source_ids

    try:
        sources = client.get_notebook_sources_with_types(notebook_id)
        ids = [s["id"] for s in sources if s.get("id")]
    except Exception as e:
        raise ServiceError(
            f"Failed to fetch sources: {e}",
            user_message="Could not retrieve notebook sources.",
        )

    if not ids:
        raise ValidationError(
            f"No sources found in notebook. Add sources before creating artifacts.",
        )
    return ids


def _validate_result(result: dict | None, artifact_type: str) -> str:
    """Validate creation result has an artifact_id.

    Returns:
        The artifact_id

    Raises:
        ServiceError: If result is missing or has no artifact_id
    """
    if not result or not result.get("artifact_id"):
        raise ServiceError(
            f"NotebookLM rejected {artifact_type.replace('_', ' ')} creation — no artifact returned.",
            user_message=(
                f"NotebookLM rejected {artifact_type.replace('_', ' ')} creation. "
                f"Try again later or create from NotebookLM UI for diagnosis."
            ),
        )
    return result["artifact_id"]


# ---------- Creation ----------

def create_artifact(
    client: "NotebookLMClient",
    notebook_id: str,
    artifact_type: str,
    *,
    source_ids: Optional[list[str]] = None,
    # Audio
    audio_format: str = "deep_dive",
    audio_length: str = "default",
    # Video
    video_format: str = "explainer",
    visual_style: str = "auto_select",
    # Infographic
    orientation: str = "landscape",
    detail_level: str = "standard",
    # Slide deck
    slide_format: str = "detailed_deck",
    slide_length: str = "default",
    # Report
    report_format: str = "Briefing Doc",
    custom_prompt: str = "",
    # Quiz
    question_count: int = 2,
    # Shared
    difficulty: str = "medium",
    language: str = "en",
    focus_prompt: str = "",
    # Mind map
    title: str = "Mind Map",
    # Data table
    description: str = "",
) -> CreateResult | MindMapResult:
    """Create a studio artifact. Unified function for all 9 artifact types.

    Handles type validation, code resolution, source ID resolution,
    and result validation. Mind maps use the two-step generate→save pattern.

    Returns:
        CreateResult for standard artifacts, MindMapResult for mind maps

    Raises:
        ValidationError: Invalid artifact type, format, or missing required fields
        ServiceError: API call failures
    """
    validate_artifact_type(artifact_type)
    resolved_ids = _resolve_source_ids(client, notebook_id, source_ids)

    try:
        if artifact_type == "mind_map":
            return _create_mind_map(client, notebook_id, resolved_ids, title)

        result = _dispatch_create(
            client, notebook_id, artifact_type, resolved_ids,
            audio_format=audio_format, audio_length=audio_length,
            video_format=video_format, visual_style=visual_style,
            orientation=orientation, detail_level=detail_level,
            slide_format=slide_format, slide_length=slide_length,
            report_format=report_format, custom_prompt=custom_prompt,
            question_count=question_count, difficulty=difficulty,
            language=language, focus_prompt=focus_prompt,
            description=description,
        )

        artifact_id = _validate_result(result, artifact_type)
        return CreateResult(
            artifact_type=artifact_type,
            artifact_id=artifact_id,
            status=result.get("status", "in_progress"),
            message=f"{artifact_type.replace('_', ' ').title()} generation started.",
        )

    except (ValidationError, ServiceError):
        raise
    except Exception as e:
        raise ServiceError(
            f"Failed to create {artifact_type}: {e}",
            user_message=f"Could not create {artifact_type.replace('_', ' ')}.",
        )


def _dispatch_create(
    client: "NotebookLMClient",
    notebook_id: str,
    artifact_type: str,
    source_ids: list[str],
    **kwargs,
) -> dict | None:
    """Dispatch to the appropriate client method based on artifact_type."""

    if artifact_type == "audio":
        format_code = resolve_code(constants.AUDIO_FORMATS, kwargs["audio_format"], "audio format")
        length_code = resolve_code(constants.AUDIO_LENGTHS, kwargs["audio_length"], "audio length")
        return client.create_audio_overview(
            notebook_id, source_ids=source_ids,
            format_code=format_code, length_code=length_code,
            language=kwargs["language"], focus_prompt=kwargs["focus_prompt"],
        )

    elif artifact_type == "video":
        format_code = resolve_code(constants.VIDEO_FORMATS, kwargs["video_format"], "video format")
        style_code = resolve_code(constants.VIDEO_STYLES, kwargs["visual_style"], "visual style")
        return client.create_video_overview(
            notebook_id, source_ids=source_ids,
            format_code=format_code, visual_style_code=style_code,
            language=kwargs["language"], focus_prompt=kwargs["focus_prompt"],
        )

    elif artifact_type == "infographic":
        orientation_code = resolve_code(constants.INFOGRAPHIC_ORIENTATIONS, kwargs["orientation"], "orientation")
        detail_code = resolve_code(constants.INFOGRAPHIC_DETAILS, kwargs["detail_level"], "detail level")
        return client.create_infographic(
            notebook_id, source_ids=source_ids,
            orientation_code=orientation_code, detail_level_code=detail_code,
            language=kwargs["language"], focus_prompt=kwargs["focus_prompt"],
        )

    elif artifact_type == "slide_deck":
        format_code = resolve_code(constants.SLIDE_DECK_FORMATS, kwargs["slide_format"], "slide format")
        length_code = resolve_code(constants.SLIDE_DECK_LENGTHS, kwargs["slide_length"], "slide length")
        return client.create_slide_deck(
            notebook_id, source_ids=source_ids,
            format_code=format_code, length_code=length_code,
            language=kwargs["language"], focus_prompt=kwargs["focus_prompt"],
        )

    elif artifact_type == "report":
        return client.create_report(
            notebook_id, source_ids=source_ids,
            report_format=kwargs["report_format"],
            custom_prompt=kwargs["custom_prompt"],
            language=kwargs["language"],
        )

    elif artifact_type == "flashcards":
        difficulty_code = resolve_code(constants.FLASHCARD_DIFFICULTIES, kwargs["difficulty"], "difficulty")
        return client.create_flashcards(
            notebook_id, source_ids=source_ids,
            difficulty_code=difficulty_code,
            focus_prompt=kwargs["focus_prompt"],
        )

    elif artifact_type == "quiz":
        difficulty_code = resolve_code(constants.FLASHCARD_DIFFICULTIES, kwargs["difficulty"], "difficulty")
        return client.create_quiz(
            notebook_id, source_ids=source_ids,
            question_count=kwargs["question_count"],
            difficulty=difficulty_code,
            focus_prompt=kwargs["focus_prompt"],
        )

    elif artifact_type == "data_table":
        if not kwargs["description"]:
            raise ValidationError("description is required for data_table")
        return client.create_data_table(
            notebook_id, source_ids=source_ids,
            description=kwargs["description"],
            language=kwargs["language"],
        )

    return None  # unreachable after validate_artifact_type


def _create_mind_map(
    client: "NotebookLMClient",
    notebook_id: str,
    source_ids: list[str],
    title: str,
) -> MindMapResult:
    """Two-step mind map creation: generate → save.

    Raises:
        ServiceError: If generation or save fails
    """
    gen_result = client.generate_mind_map(
        notebook_id=notebook_id, source_ids=source_ids,
    )
    if not gen_result or not gen_result.get("mind_map_json"):
        raise ServiceError(
            "Failed to generate mind map — no JSON returned",
            user_message="Mind map generation failed.",
        )

    save_result = client.save_mind_map(
        notebook_id,
        gen_result["mind_map_json"],
        source_ids=source_ids,
        title=title,
    )
    if not save_result:
        raise ServiceError(
            "Failed to save mind map",
            user_message="Mind map could not be saved.",
        )

    # Parse mind map JSON for metadata
    try:
        mind_map_data = json.loads(save_result.get("mind_map_json", "{}"))
        root_name = mind_map_data.get("name", "Unknown")
        children_count = len(mind_map_data.get("children", []))
    except json.JSONDecodeError:
        root_name = "Unknown"
        children_count = 0

    return MindMapResult(
        artifact_type="mind_map",
        artifact_id=save_result["mind_map_id"],
        title=save_result.get("title", title),
        root_name=root_name,
        children_count=children_count,
        message="Mind map created successfully.",
    )


# ---------- Status ----------

def get_studio_status(
    client: "NotebookLMClient",
    notebook_id: str,
) -> StatusResult:
    """Get status of all studio artifacts including mind maps.

    Returns:
        StatusResult with artifact list and summary counts

    Raises:
        ServiceError: If polling fails
    """
    try:
        artifacts = client.poll_studio_status(notebook_id)
    except Exception as e:
        raise ServiceError(
            f"Failed to poll studio status: {e}",
            user_message="Could not retrieve studio status.",
        )

    # Also fetch mind maps
    try:
        mind_maps = client.list_mind_maps(notebook_id)
        for mm in mind_maps:
            artifacts.append({
                "artifact_id": mm.get("mind_map_id"),
                "type": "mind_map",
                "title": mm.get("title", "Mind Map"),
                "status": "completed",
                "created_at": mm.get("created_at"),
            })
    except Exception:
        pass  # Mind maps are optional

    completed = [a for a in artifacts if a.get("status") == "completed"]
    in_progress = [a for a in artifacts if a.get("status") == "in_progress"]

    return StatusResult(
        artifacts=artifacts,
        total=len(artifacts),
        completed=len(completed),
        in_progress=len(in_progress),
    )


# ---------- Rename ----------

def rename_artifact(
    client: "NotebookLMClient",
    artifact_id: str,
    new_title: str,
) -> RenameResult:
    """Rename a studio artifact.

    Returns:
        RenameResult with artifact_id and new_title

    Raises:
        ValidationError: If parameters are missing
        ServiceError: If rename fails
    """
    if not artifact_id:
        raise ValidationError("artifact_id is required for rename")
    if not new_title:
        raise ValidationError("new_title is required for rename")

    try:
        success = client.rename_studio_artifact(artifact_id, new_title)
        if not success:
            raise ServiceError(
                f"Rename returned falsy for artifact {artifact_id}",
                user_message="Failed to rename artifact.",
            )
        return RenameResult(artifact_id=artifact_id, new_title=new_title)
    except (ValidationError, ServiceError):
        raise
    except Exception as e:
        raise ServiceError(
            f"Failed to rename artifact: {e}",
            user_message="Could not rename artifact.",
        )


# ---------- Delete ----------

def delete_artifact(
    client: "NotebookLMClient",
    artifact_id: str,
    notebook_id: str,
) -> None:
    """Delete a studio artifact permanently.

    Raises:
        ServiceError: If deletion fails
    """
    try:
        result = client.delete_studio_artifact(artifact_id, notebook_id=notebook_id)
        if not result:
            raise ServiceError(
                f"Delete returned falsy for artifact {artifact_id}",
                user_message="Failed to delete artifact.",
            )
    except ServiceError:
        raise
    except Exception as e:
        raise ServiceError(
            f"Failed to delete artifact: {e}",
            user_message="Could not delete artifact.",
        )
