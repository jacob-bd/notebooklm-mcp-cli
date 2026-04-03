"""Standalone Podcast tool — Enterprise only, no notebook required.

Uses the Discovery Engine Podcast API (v1, stable) to generate podcasts
from raw text content. Does NOT require a NotebookLM Enterprise license,
only the roles/discoveryengine.podcastApiUser IAM role.
"""

import os
from typing import Any

from ._utils import get_client, logged_tool


@logged_tool()
def podcast_create(
    text: str | list[str],
    title: str = "",
    description: str = "",
    focus: str = "",
    length: str = "STANDARD",
    language: str = "en",
) -> dict[str, Any]:
    """Generate a standalone podcast from text (Enterprise only, no notebook needed).

    Args:
        text: Text content to turn into a podcast. Can be a single string
              or a list of strings (each becomes a separate context).
        title: Optional podcast title
        description: Optional podcast description
        focus: Optional topic focus prompt to guide the podcast
        length: "SHORT" (~4-5 min) or "STANDARD" (~10 min)
        language: Language code (default: "en")

    Returns:
        Dictionary with operation name for tracking and downloading.
    """
    if os.environ.get("NOTEBOOKLM_MODE", "personal").lower() != "enterprise":
        return {
            "status": "error",
            "error": "Standalone podcast creation is only available in enterprise mode. "
                     "Set NOTEBOOKLM_MODE=enterprise.",
        }

    client = get_client()
    if not hasattr(client, "create_podcast"):
        return {
            "status": "error",
            "error": "Podcast API not available on this client.",
        }

    text_list = [text] if isinstance(text, str) else text

    try:
        result = client.create_podcast(
            text_contents=text_list,
            title=title,
            description=description,
            focus=focus,
            length=length,
            language=language,
        )
        if result:
            return {
                "status": "success",
                "message": "Podcast generation started. Use the operation name to download when complete.",
                "operation_name": result.get("name", ""),
                "raw": result,
            }
        return {"status": "error", "error": "No response from Podcast API."}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def podcast_download(
    operation_name: str,
    output_path: str = "",
) -> dict[str, Any]:
    """Download a completed standalone podcast.

    Args:
        operation_name: The operation name from podcast_create response
        output_path: Local file path to save the MP3 (default: ~/Downloads/podcast.mp3)

    Returns:
        Dictionary with the downloaded file path.
    """
    if os.environ.get("NOTEBOOKLM_MODE", "personal").lower() != "enterprise":
        return {"status": "error", "error": "Only available in enterprise mode."}

    client = get_client()
    if not hasattr(client, "download_podcast"):
        return {"status": "error", "error": "Podcast API not available on this client."}

    if not output_path:
        output_path = os.path.expanduser("~/Downloads/podcast.mp3")

    try:
        path = client.download_podcast(operation_name, output_path)
        return {
            "status": "success",
            "file_path": path,
            "message": f"Podcast downloaded to {path}",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
