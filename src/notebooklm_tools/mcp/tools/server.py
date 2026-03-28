"""Server tools - Server info."""

import os
from typing import Any

from notebooklm_tools import __version__

from ._utils import logged_tool


@logged_tool()
def server_info() -> dict[str, Any]:
    """Get server version and mode info.

    Returns:
        dict with version and configuration info.
    """
    mode = os.environ.get("NOTEBOOKLM_MODE", "personal")
    project_id = os.environ.get("NOTEBOOKLM_PROJECT_ID", "")
    location = os.environ.get("NOTEBOOKLM_LOCATION", "global")

    info = {
        "status": "success",
        "version": __version__,
        "mode": mode,
        "fork": "Robiton/notebooklm-mcp-cli (enterprise fork)",
    }

    if mode == "enterprise":
        info["project_id"] = project_id
        info["location"] = location
        info["api"] = "Discovery Engine REST API (stable)"
        info["supported_operations"] = [
            "notebook_list", "notebook_create", "notebook_get", "notebook_delete",
            "source_add (URL, text, YouTube, Drive, file upload)",
            "source_delete",
            "audio_overview (generate, delete)",
            "podcast_create (standalone, no notebook needed)",
            "notebook_share",
        ]
        info["unsupported_operations"] = [
            "chat/query", "video", "reports", "flashcards", "quizzes",
            "infographics", "slides", "mind_maps", "notes", "research",
            "rename_notebook",
        ]

    return info
