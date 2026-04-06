"""Studio advanced — helper for studio type reference data."""

from typing import Any


def _get_studio_types() -> dict[str, Any]:
    """Return reference of all artifact types and their configurable parameters.

    Called by studio_status(action="list_types").
    """
    types_info = {
        "audio": {
            "description": "Audio Overview (podcast-style)",
            "options": {
                "audio_format": ["deep_dive", "brief", "critique", "debate"],
                "audio_length": ["short", "default", "long"],
                "language": "BCP-47 code (en, es, fr, de, ja, etc.)",
                "focus_prompt": "Optional focus topic",
            },
        },
        "video": {
            "description": "Video Overview",
            "options": {
                "video_format": ["explainer", "brief", "cinematic"],
                "visual_style": [
                    "auto_select",
                    "custom",
                    "classic",
                    "whiteboard",
                    "kawaii",
                    "anime",
                    "watercolor",
                    "retro_print",
                    "heritage",
                    "paper_craft",
                ],
                "video_style_prompt": "Optional custom visual style text (requires visual_style=custom; not supported for cinematic)",
                "language": "BCP-47 code",
                "focus_prompt": "Optional focus topic",
            },
        },
        "infographic": {
            "description": "Visual infographic",
            "options": {
                "orientation": ["landscape", "portrait", "square"],
                "detail_level": ["concise", "standard", "detailed"],
                "language": "BCP-47 code",
                "focus_prompt": "Optional focus topic",
            },
        },
        "slide_deck": {
            "description": "Presentation slides (PDF)",
            "options": {
                "slide_format": ["detailed_deck", "presenter_slides"],
                "slide_length": ["short", "default"],
                "language": "BCP-47 code",
                "focus_prompt": "Optional focus topic",
            },
        },
        "report": {
            "description": "Text report",
            "options": {
                "report_format": ["Briefing Doc", "Study Guide", "Blog Post", "Create Your Own"],
                "custom_prompt": "Custom instructions (for Create Your Own)",
                "language": "BCP-47 code",
            },
        },
        "flashcards": {
            "description": "Study flashcards",
            "options": {
                "difficulty": ["easy", "medium", "hard"],
                "focus_prompt": "Optional focus topic",
            },
        },
        "quiz": {
            "description": "Multiple choice quiz",
            "options": {
                "question_count": "Number of questions (default: 2)",
                "difficulty": ["easy", "medium", "hard"],
                "focus_prompt": "Optional focus topic",
            },
        },
        "data_table": {
            "description": "Structured data table",
            "options": {
                "description": "REQUIRED - description of what data to extract",
                "language": "BCP-47 code",
            },
        },
        "mind_map": {
            "description": "Visual mind map",
            "options": {
                "title": "Mind map title (default: Mind Map)",
            },
        },
    }

    return {
        "status": "success",
        "types": types_info,
        "count": len(types_info),
        "usage": "Use studio_create(notebook_id, artifact_type, ...) to create any type.",
    }
