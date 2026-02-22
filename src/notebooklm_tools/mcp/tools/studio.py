"""Studio tools - Artifact creation with consolidated studio_create."""

from typing import Any

from ._utils import get_client, logged_tool
from ...services import studio as studio_service, ServiceError, ValidationError
from ...utils.config import get_default_language


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
    # Infographic options
    orientation: str = "landscape",
    detail_level: str = "standard",
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
) -> dict[str, Any]:
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
        - video: video_format (explainer|brief), visual_style (auto_select|classic|whiteboard|kawaii|anime|watercolor|retro_print|heritage|paper_craft)
        - infographic: orientation (landscape|portrait|square), detail_level (concise|standard|detailed)
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

    # Validate type early (before confirmation check)
    try:
        studio_service.validate_artifact_type(artifact_type)
    except ValidationError as e:
        return {"status": "error", "error": str(e)}

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
            settings.update({"format": video_format, "visual_style": visual_style, "language": language})
        elif artifact_type == "infographic":
            settings.update({"orientation": orientation, "detail_level": detail_level, "language": language})
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
            client, notebook_id, artifact_type,
            source_ids=source_ids,
            audio_format=audio_format, audio_length=audio_length,
            video_format=video_format, visual_style=visual_style,
            orientation=orientation, detail_level=detail_level,
            slide_format=slide_format, slide_length=slide_length,
            report_format=report_format, custom_prompt=custom_prompt,
            question_count=question_count, difficulty=difficulty,
            language=language, focus_prompt=focus_prompt,
            title=title, description=description,
        )
        return {
            "status": "success",
            "notebook_url": f"https://notebooklm.google.com/notebook/{notebook_id}",
            **result,
        }
    except (ValidationError, ServiceError) as e:
        return {"status": "error", "error": e.user_message if isinstance(e, ServiceError) else str(e)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def studio_status(
    notebook_id: str,
    action: str = "status",
    artifact_id: str | None = None,
    new_title: str | None = None,
) -> dict[str, Any]:
    """Check studio content generation status and get URLs, or rename an artifact.

    Args:
        notebook_id: Notebook UUID
        action: Action to perform:
            - status (default): List all artifacts with their status and URLs
            - rename: Rename an artifact (requires artifact_id and new_title)
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
        client = get_client()

        if action == "rename":
            result = studio_service.rename_artifact(client, artifact_id, new_title)
            return {
                "status": "success",
                "action": "rename",
                "message": f"Artifact renamed to '{result['new_title']}'",
                **result,
            }

        result = studio_service.get_studio_status(client, notebook_id)
        return {
            "status": "success",
            "notebook_id": notebook_id,
            "summary": {
                "total": result["total"],
                "completed": result["completed"],
                "in_progress": result["in_progress"],
            },
            "artifacts": result["artifacts"],
            "notebook_url": f"https://notebooklm.google.com/notebook/{notebook_id}",
        }
    except (ValidationError, ServiceError) as e:
        return {"status": "error", "error": e.user_message if isinstance(e, ServiceError) else str(e)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def studio_delete(
    notebook_id: str,
    artifact_id: str,
    confirm: bool = False,
) -> dict[str, Any]:
    """Delete studio artifact. IRREVERSIBLE. Requires confirm=True.

    Args:
        notebook_id: Notebook UUID
        artifact_id: Artifact UUID (from studio_status)
        confirm: Must be True after user approval
    """
    if not confirm:
        return {
            "status": "error",
            "error": "Deletion not confirmed. Set confirm=True after user approval.",
            "warning": "This action is IRREVERSIBLE.",
            "hint": "Call studio_status first to list artifacts with their IDs.",
        }

    try:
        client = get_client()
        studio_service.delete_artifact(client, artifact_id, notebook_id)
        return {
            "status": "success",
            "message": f"Artifact {artifact_id} has been permanently deleted.",
            "notebook_id": notebook_id,
        }
    except ServiceError as e:
        return {"status": "error", "error": e.user_message}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def studio_revise(
    notebook_id: str,
    artifact_id: str,
    slide_instructions: list,
    confirm: bool = False,
) -> dict[str, Any]:
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
                ] if slide_instructions else [],
            },
            "note": "This creates a NEW slide deck with revisions applied. The original is not modified. Set confirm=True after user approves.",
        }

    try:
        client = get_client()
        result = studio_service.revise_artifact(
            client, artifact_id, slide_instructions,
        )
        return {
            "status": "success",
            "notebook_url": f"https://notebooklm.google.com/notebook/{notebook_id}",
            **result,
        }
    except (ValidationError, ServiceError) as e:
        return {"status": "error", "error": e.user_message if isinstance(e, ServiceError) else str(e)}
    except Exception as e:
        return {"status": "error", "error": str(e)}
