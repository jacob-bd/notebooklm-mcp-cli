"""Studio tools - Artifact creation with consolidated studio_create."""

import json
from typing import Any

from notebooklm_tools.core import constants
from ._utils import get_client, logged_tool


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
    language: str = "en",
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
        - language: BCP-47 code (en, es, fr, de, ja)
        - focus_prompt: Optional focus text

    Example:
        studio_create(notebook_id="abc", artifact_type="audio", confirm=True)
        studio_create(notebook_id="abc", artifact_type="quiz", question_count=5, confirm=True)
    """
    valid_types = [
        "audio", "video", "infographic", "slide_deck", "report",
        "flashcards", "quiz", "data_table", "mind_map"
    ]

    if artifact_type not in valid_types:
        return {
            "status": "error",
            "error": f"Unknown artifact_type '{artifact_type}'. Valid types: {', '.join(valid_types)}",
        }

    # Confirmation check
    if not confirm:
        settings = {
            "notebook_id": notebook_id,
            "artifact_type": artifact_type,
            "source_ids": source_ids or "all sources",
        }
        # Add type-specific settings to confirmation
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

        # Get source IDs if not provided
        if source_ids is None:
            sources = client.get_notebook_sources_with_types(notebook_id)
            source_ids = [s["id"] for s in sources if s.get("id")]

        if not source_ids:
            return {
                "status": "error",
                "error": f"No sources found in notebook. Add sources before creating {artifact_type}.",
            }

        result = None

        if artifact_type == "audio":
            try:
                format_code = constants.AUDIO_FORMATS.get_code(audio_format)
            except ValueError:
                return {
                    "status": "error",
                    "error": f"Unknown audio_format '{audio_format}'. Use: {', '.join(constants.AUDIO_FORMATS.names)}",
                }
            try:
                length_code = constants.AUDIO_LENGTHS.get_code(audio_length)
            except ValueError:
                return {
                    "status": "error",
                    "error": f"Unknown audio_length '{audio_length}'. Use: {', '.join(constants.AUDIO_LENGTHS.names)}",
                }
            result = client.create_audio_overview(
                notebook_id=notebook_id,
                source_ids=source_ids,
                format_code=format_code,
                length_code=length_code,
                language=language,
                focus_prompt=focus_prompt,
            )

        elif artifact_type == "video":
            try:
                format_code = constants.VIDEO_FORMATS.get_code(video_format)
            except ValueError:
                return {
                    "status": "error",
                    "error": f"Unknown video_format '{video_format}'. Use: {', '.join(constants.VIDEO_FORMATS.names)}",
                }
            try:
                style_code = constants.VIDEO_STYLES.get_code(visual_style)
            except ValueError:
                return {
                    "status": "error",
                    "error": f"Unknown visual_style '{visual_style}'. Use: {', '.join(constants.VIDEO_STYLES.names)}",
                }
            result = client.create_video_overview(
                notebook_id=notebook_id,
                source_ids=source_ids,
                format_code=format_code,
                visual_style_code=style_code,
                language=language,
                focus_prompt=focus_prompt,
            )

        elif artifact_type == "infographic":
            try:
                orientation_code = constants.INFOGRAPHIC_ORIENTATIONS.get_code(orientation)
            except ValueError:
                return {
                    "status": "error",
                    "error": f"Unknown orientation '{orientation}'. Use: {', '.join(constants.INFOGRAPHIC_ORIENTATIONS.names)}",
                }
            try:
                detail_code = constants.INFOGRAPHIC_DETAILS.get_code(detail_level)
            except ValueError:
                return {
                    "status": "error",
                    "error": f"Unknown detail_level '{detail_level}'. Use: {', '.join(constants.INFOGRAPHIC_DETAILS.names)}",
                }
            result = client.create_infographic(
                notebook_id=notebook_id,
                source_ids=source_ids,
                orientation_code=orientation_code,
                detail_level_code=detail_code,
                language=language,
                focus_prompt=focus_prompt,
            )

        elif artifact_type == "slide_deck":
            try:
                format_code = constants.SLIDE_DECK_FORMATS.get_code(slide_format)
            except ValueError:
                return {
                    "status": "error",
                    "error": f"Unknown slide_format '{slide_format}'. Use: {', '.join(constants.SLIDE_DECK_FORMATS.names)}",
                }
            try:
                length_code = constants.SLIDE_DECK_LENGTHS.get_code(slide_length)
            except ValueError:
                return {
                    "status": "error",
                    "error": f"Unknown slide_length '{slide_length}'. Use: {', '.join(constants.SLIDE_DECK_LENGTHS.names)}",
                }
            result = client.create_slide_deck(
                notebook_id=notebook_id,
                source_ids=source_ids,
                format_code=format_code,
                length_code=length_code,
                language=language,
                focus_prompt=focus_prompt,
            )

        elif artifact_type == "report":
            result = client.create_report(
                notebook_id=notebook_id,
                source_ids=source_ids,
                report_format=report_format,
                custom_prompt=custom_prompt,
                language=language,
            )

        elif artifact_type == "flashcards":
            try:
                difficulty_code = constants.FLASHCARD_DIFFICULTIES.get_code(difficulty)
            except ValueError:
                return {
                    "status": "error",
                    "error": f"Unknown difficulty '{difficulty}'. Use: {', '.join(constants.FLASHCARD_DIFFICULTIES.names)}",
                }
            result = client.create_flashcards(
                notebook_id=notebook_id,
                source_ids=source_ids,
                difficulty_code=difficulty_code,
            )

        elif artifact_type == "quiz":
            try:
                difficulty_code = constants.FLASHCARD_DIFFICULTIES.get_code(difficulty)
            except ValueError:
                return {
                    "status": "error",
                    "error": f"Unknown difficulty '{difficulty}'. Use: {', '.join(constants.FLASHCARD_DIFFICULTIES.names)}",
                }
            result = client.create_quiz(
                notebook_id=notebook_id,
                source_ids=source_ids,
                question_count=question_count,
                difficulty=difficulty_code,
            )

        elif artifact_type == "data_table":
            if not description:
                return {
                    "status": "error",
                    "error": "description is required for data_table",
                }
            result = client.create_data_table(
                notebook_id=notebook_id,
                source_ids=source_ids,
                description=description,
                language=language,
            )

        elif artifact_type == "mind_map":
            # Mind map requires two steps: generate then save
            gen_result = client.generate_mind_map(
                notebook_id=notebook_id,
                source_ids=source_ids
            )
            if not gen_result or not gen_result.get("mind_map_json"):
                return {"status": "error", "error": "Failed to generate mind map"}

            save_result = client.save_mind_map(
                notebook_id=notebook_id,
                mind_map_json=gen_result["mind_map_json"],
                source_ids=source_ids,
                title=title,
            )

            if save_result:
                try:
                    mind_map_data = json.loads(save_result.get("mind_map_json", "{}"))
                    root_name = mind_map_data.get("name", "Unknown")
                    children_count = len(mind_map_data.get("children", []))
                except json.JSONDecodeError:
                    root_name = "Unknown"
                    children_count = 0

                return {
                    "status": "success",
                    "artifact_type": "mind_map",
                    "artifact_id": save_result["mind_map_id"],
                    "title": save_result.get("title", title),
                    "root_name": root_name,
                    "children_count": children_count,
                    "message": "Mind map created successfully.",
                    "notebook_url": f"https://notebooklm.google.com/notebook/{notebook_id}",
                }
            return {"status": "error", "error": "Failed to save mind map"}

        if result:
            return {
                "status": "success",
                "artifact_type": artifact_type,
                "artifact_id": result.get("artifact_id"),
                "generation_status": result.get("status"),
                "message": f"{artifact_type.replace('_', ' ').title()} generation started. Use studio_status to check progress.",
                "notebook_url": f"https://notebooklm.google.com/notebook/{notebook_id}",
            }
        return {"status": "error", "error": f"Failed to create {artifact_type}"}

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
    """
    try:
        client = get_client()

        # Handle rename action
        if action == "rename":
            if not artifact_id:
                return {
                    "status": "error",
                    "error": "artifact_id is required for action='rename'",
                }
            if not new_title:
                return {
                    "status": "error",
                    "error": "new_title is required for action='rename'",
                }
            
            success = client.rename_studio_artifact(artifact_id, new_title)
            if success:
                return {
                    "status": "success",
                    "action": "rename",
                    "artifact_id": artifact_id,
                    "new_title": new_title,
                    "message": f"Artifact renamed to '{new_title}'",
                }
            return {"status": "error", "error": "Failed to rename artifact"}

        # Default: status action
        artifacts = client.poll_studio_status(notebook_id)

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
            pass

        # Separate by status
        completed = [a for a in artifacts if a.get("status") == "completed"]
        in_progress = [a for a in artifacts if a.get("status") == "in_progress"]

        return {
            "status": "success",
            "notebook_id": notebook_id,
            "summary": {
                "total": len(artifacts),
                "completed": len(completed),
                "in_progress": len(in_progress),
            },
            "artifacts": artifacts,
            "notebook_url": f"https://notebooklm.google.com/notebook/{notebook_id}",
        }
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
        result = client.delete_studio_artifact(artifact_id, notebook_id)

        if result:
            return {
                "status": "success",
                "message": f"Artifact {artifact_id} has been permanently deleted.",
                "notebook_id": notebook_id,
            }
        return {"status": "error", "error": "Failed to delete artifact"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
