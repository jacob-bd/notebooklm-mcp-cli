"""Studio tools - Artifact creation with consolidated studio_create."""

from typing import Any

from ...services import ServiceError, ValidationError
from ...services import studio as studio_service
from ...utils.config import get_base_url, get_default_language
from ._utils import ResultDict, coerce_list, error_result, get_client, logged_tool


def _normalize_studio_validation_error(message: str) -> str:
    """Preserve historical MCP wire wording for invalid artifact_type."""
    if message.startswith("Unknown artifact type "):
        return message.replace("Unknown artifact type", "Unknown artifact_type", 1)
    return message


@logged_tool()
def studio_create(
    notebook_id: str,
    artifact_type: str,
    source_ids: list[str] | None = None,
    confirm: bool = False,
    # Audio/Video options
    audio_format: str = "deep_dive",
    audio_length: str = "default",
    video_format: str = "explainer",
    visual_style: str = "auto_select",
    video_style_prompt: str = "",
    # Infographic options
    orientation: str = "landscape",
    detail_level: str = "standard",
    infographic_style: str = "auto_select",
    # Slide deck options
    slide_format: str = "detailed_deck",
    slide_length: str = "default",
    # Report options
    report_format: str = "Briefing Doc",
    custom_prompt: str = "",
    # Quiz options
    question_count: int = 2,
    # Shared options
    difficulty: str = "medium",
    language: str = "",
    focus_prompt: str = "",
    # Mind map options
    title: str = "Mind Map",
    # Data table options
    description: str = "",
) -> ResultDict:
    """Create any NotebookLM studio artifact. Unified creation tool.

    Supports: audio, video, infographic, slide_deck, report, flashcards, quiz, data_table, mind_map

    Args:
        notebook_id: Notebook UUID
        artifact_type: Type of artifact to create:
            - audio: Audio Overview (podcast)
            - video: Video Overview
            - infographic: Visual infographic
            - slide_deck: Presentation slides (PDF)
            - report: Text report (Briefing Doc, Study Guide, etc.)
            - flashcards: Study flashcards
            - quiz: Multiple choice quiz
            - data_table: Structured data table
            - mind_map: Visual mind map
        source_ids: Source IDs to use (default: all sources)
        confirm: Must be True after user approval

        Type-specific options:
        - audio: audio_format (deep_dive|brief|critique|debate), audio_length (short|default|long)
        - video: video_format (explainer|brief|cinematic), visual_style (auto_select|custom|classic|whiteboard|kawaii|anime|watercolor|retro_print|heritage|paper_craft), video_style_prompt
        - infographic: orientation (landscape|portrait|square), detail_level (concise|standard|detailed), infographic_style (auto_select|sketch_note|professional|bento_grid|editorial|instructional|bricks|clay|anime|kawaii|scientific)
        - slide_deck: slide_format (detailed_deck|presenter_slides), slide_length (short|default)
        - report: report_format (Briefing Doc|Study Guide|Blog Post|Create Your Own), custom_prompt
        - flashcards: difficulty (easy|medium|hard)
        - quiz: question_count (int), difficulty (easy|medium|hard)
        - data_table: description (required)
        - mind_map: title

        Common options:
        - language: BCP-47 code (en, es, fr, de, ja). Defaults to NOTEBOOKLM_HL env var or 'en'
        - focus_prompt: Optional focus text

    Example:
        studio_create(notebook_id="abc", artifact_type="audio", confirm=True)
        studio_create(notebook_id="abc", artifact_type="quiz", question_count=5, confirm=True)
    """
    if not language:
        language = get_default_language()

    # Coerce list params from MCP clients (may arrive as strings)
    source_ids = coerce_list(source_ids)

    # Validate type early (before confirmation check)
    try:
        studio_service.validate_artifact_type(artifact_type)
    except ValidationError as e:
        return error_result(_normalize_studio_validation_error(str(e)))

    # Confirmation check — show settings preview
    if not confirm:
        settings: dict[str, Any] = {
            "notebook_id": notebook_id,
            "artifact_type": artifact_type,
            "source_ids": source_ids or "all sources",
        }
        if artifact_type == "audio":
            settings.update({"format": audio_format, "length": audio_length, "language": language})
        elif artifact_type == "video":
            settings.update(
                {"format": video_format, "visual_style": visual_style, "language": language}
            )
            if video_style_prompt:
                settings["video_style_prompt"] = video_style_prompt
        elif artifact_type == "infographic":
            settings.update(
                {
                    "orientation": orientation,
                    "detail_level": detail_level,
                    "infographic_style": infographic_style,
                    "language": language,
                }
            )
        elif artifact_type == "slide_deck":
            settings.update({"format": slide_format, "length": slide_length, "language": language})
        elif artifact_type == "report":
            settings.update({"format": report_format, "language": language})
        elif artifact_type in ("flashcards", "quiz"):
            settings.update({"difficulty": difficulty})
            if artifact_type == "quiz":
                settings["question_count"] = question_count
        elif artifact_type == "data_table":
            settings.update({"description": description, "language": language})
        elif artifact_type == "mind_map":
            settings.update({"title": title})
        if focus_prompt:
            settings["focus_prompt"] = focus_prompt

        return {
            "status": "pending_confirmation",
            "message": f"Please confirm these settings before creating {artifact_type}:",
            "settings": settings,
            "note": "Set confirm=True after user approves these settings.",
        }

    try:
        client = get_client()
        result = studio_service.create_artifact(
            client,
            notebook_id,
            artifact_type,
            source_ids=source_ids,
            audio_format=audio_format,
            audio_length=audio_length,
            video_format=video_format,
            visual_style=visual_style,
            video_style_prompt=video_style_prompt,
            orientation=orientation,
            detail_level=detail_level,
            infographic_style=infographic_style,
            slide_format=slide_format,
            slide_length=slide_length,
            report_format=report_format,
            custom_prompt=custom_prompt,
            question_count=question_count,
            difficulty=difficulty,
            language=language,
            focus_prompt=focus_prompt,
            title=title,
            description=description,
        )
        artifact_status = result.get("status")
        result_payload = dict(result)
        if artifact_status is not None:
            result_payload["artifact_status"] = artifact_status
            result_payload.pop("status", None)
        return {
            **result_payload,
            "status": "success",
            "notebook_url": f"{get_base_url()}/notebook/{notebook_id}",
        }
    except ValidationError as e:
        return error_result(_normalize_studio_validation_error(str(e)))
    except ServiceError as e:
        return error_result(e.user_message)
    except Exception as e:
        return error_result(str(e))


@logged_tool()
def studio_status(
    notebook_id: str,
    action: str = "status",
    artifact_id: str | None = None,
    new_title: str | None = None,
) -> ResultDict:
    """Check studio content generation status and get URLs, or rename an artifact.

    Args:
        notebook_id: Notebook UUID
        action: Action to perform:
            - status (default): List all artifacts with their status and URLs
            - rename: Rename an artifact (requires artifact_id and new_title)
            - list_types: List all supported artifact types with their options
        artifact_id: Required for action="rename" - the artifact UUID to rename
        new_title: Required for action="rename" - the new title for the artifact

    Returns:
        Dictionary with status and results.
        For action="status":
            - status: "success"
            - artifacts: List of artifacts, each containing:
                - artifact_id: UUID
                - title: Artifact title
                - type: audio, video, report, etc.
                - status: completed, in_progress, failed
                - url: URL to view/download (if applicable)
                - custom_instructions: The custom prompt/focus instructions used to generate the artifact (if any)
            - summary: Counts of total, completed, in_progress
    """
    try:
        if action == "list_types":
            from .studio_advanced import _get_studio_types

            return _get_studio_types()

        client = get_client()

        if action == "rename":
            if not artifact_id:
                return error_result("artifact_id is required for action=rename")
            if not new_title:
                return error_result("new_title is required for action=rename")
            rename_result = studio_service.rename_artifact(client, artifact_id, new_title)
            return {
                "status": "success",
                "action": "rename",
                "message": f"Artifact renamed to '{rename_result['new_title']}'",
                **rename_result,
            }

        status_result = studio_service.get_studio_status(client, notebook_id)
        return {
            "status": "success",
            "notebook_id": notebook_id,
            "summary": {
                "total": status_result["total"],
                "completed": status_result["completed"],
                "in_progress": status_result["in_progress"],
            },
            "artifacts": status_result["artifacts"],
            "notebook_url": f"{get_base_url()}/notebook/{notebook_id}",
        }
    except (ValidationError, ServiceError) as e:
        message = e.user_message if isinstance(e, ServiceError) else str(e)
        return error_result(message)
    except Exception as e:
        return error_result(str(e))


@logged_tool()
def studio_delete(
    notebook_id: str,
    artifact_id: str,
    confirm: bool = False,
) -> ResultDict:
    """Delete studio artifact. IRREVERSIBLE. Requires confirm=True.

    Args:
        notebook_id: Notebook UUID
        artifact_id: Artifact UUID (from studio_status)
        confirm: Must be True after user approval
    """
    if not confirm:
        return error_result(
            "Deletion not confirmed. Set confirm=True after user approval.",
            warning="This action is IRREVERSIBLE.",
            hint="Call studio_status first to list artifacts with their IDs.",
        )

    try:
        if not artifact_id:
            return error_result("artifact_id is required.")
        client = get_client()
        studio_service.delete_artifact(client, artifact_id, notebook_id)
        return {
            "status": "success",
            "message": f"Artifact {artifact_id} has been permanently deleted.",
            "notebook_id": notebook_id,
        }
    except ServiceError as e:
        return error_result(e.user_message, hint=e.hint)
    except Exception as e:
        return error_result(str(e))


@logged_tool()
def studio_revise(
    notebook_id: str,
    artifact_id: str,
    slide_instructions: list[studio_service.SlideInstruction],
    confirm: bool = False,
) -> ResultDict:
    """Revise individual slides in an existing slide deck. Creates a NEW artifact.

    Only slide decks support revision. The original artifact is not modified.
    Poll studio_status after calling to check when the new deck is ready.

    Args:
        notebook_id: Notebook UUID
        artifact_id: UUID of the existing slide deck to revise (from studio_status)
        slide_instructions: List of revision instructions, each with:
            - slide: Slide number (1-based, slide 1 = first slide)
            - instruction: Text describing the desired change
            Example: [{"slide": 1, "instruction": "Make the title larger"}]
        confirm: Must be True after user approval

    Example:
        studio_revise(
            notebook_id="abc",
            artifact_id="xyz",
            slide_instructions=[
                {"slide": 1, "instruction": "Make the title larger"},
                {"slide": 3, "instruction": "Remove the image"}
            ],
            confirm=True
        )
    """
    if not confirm:
        return {
            "status": "pending_confirmation",
            "message": "Please confirm before revising slide deck:",
            "settings": {
                "notebook_id": notebook_id,
                "artifact_id": artifact_id,
                "slides_to_revise": [
                    f"Slide {s.get('slide', '?')}: {s.get('instruction', '')}"
                    for s in slide_instructions
                ]
                if slide_instructions
                else [],
            },
            "note": "This creates a NEW slide deck with revisions applied. The original is not modified. Set confirm=True after user approves.",
        }

    try:
        if not artifact_id:
            return error_result("artifact_id is required.")
        if not slide_instructions:
            return error_result("slide_instructions must not be empty.")
        client = get_client()
        result = studio_service.revise_artifact(
            client,
            artifact_id,
            slide_instructions,
        )
        return {
            "status": "success",
            "notebook_url": f"{get_base_url()}/notebook/{notebook_id}",
            **result,
        }
    except (ValidationError, ServiceError) as e:
        message = e.user_message if isinstance(e, ServiceError) else str(e)
        return error_result(message)
    except Exception as e:
        return error_result(str(e))
