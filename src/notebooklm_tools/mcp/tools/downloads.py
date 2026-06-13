"""Download tools - Consolidated download_artifact for all artifact types."""

import asyncio
import time

from ...services import ServiceError, ValidationError
from ...services import downloads as downloads_service
from ._utils import ResultDict, error_result, get_client, logged_tool


def _download_transient(message: str) -> bool:
    """Return True for artifact states that may resolve after polling."""
    lowered = message.lower()
    return any(
        phrase in lowered
        for phrase in (
            "not ready",
            "does not exist",
            "still propagating",
            "try again",
            "download failed",
            "is complete, but its media download url is still propagating",
        )
    )


@logged_tool()
def download_artifact(
    notebook_id: str,
    artifact_type: str,
    output_path: str,
    artifact_id: str | None = None,
    output_format: str = "json",
    slide_deck_format: str = "pdf",
    wait: bool = True,
    wait_timeout: float = 180.0,
    poll_interval: float = 5.0,
) -> ResultDict:
    """Download any NotebookLM artifact to a file.

    Unified download tool replacing 9 separate download tools.
    Supports all artifact types: audio, video, report, mind_map, slide_deck,
    infographic, data_table, quiz, flashcards.

    Args:
        notebook_id: Notebook UUID
        artifact_type: Type of artifact to download:
            - audio: Audio Overview (MP4/MP3)
            - video: Video Overview (MP4)
            - report: Report (Markdown)
            - mind_map: Mind Map (JSON)
            - slide_deck: Slide Deck (PDF or PPTX)
            - infographic: Infographic (PNG)
            - data_table: Data Table (CSV)
            - quiz: Quiz (json|markdown|html)
            - flashcards: Flashcards (json|markdown|html)
        output_path: Path to save the file
        artifact_id: Optional specific artifact ID (uses latest if not provided)
        output_format: For quiz/flashcards only: json|markdown|html (default: json)
        slide_deck_format: For slide_deck only: pdf (default) or pptx
        wait: If True, poll while NotebookLM is still generating or propagating the artifact.
        wait_timeout: Maximum seconds to wait when wait=True.
        poll_interval: Seconds between readiness checks.

    Returns:
        dict with status and saved file path

    Example:
        download_artifact(notebook_id="abc123", artifact_type="audio", output_path="podcast.mp3")
        download_artifact(notebook_id="abc123", artifact_type="quiz", output_path="quiz.html", output_format="html")
        download_artifact(notebook_id="abc123", artifact_type="slide_deck", output_path="slides.pptx", slide_deck_format="pptx")
    """
    try:
        client = get_client()
        deadline = time.monotonic() + max(0.0, wait_timeout)

        while True:
            try:
                download_result = asyncio.run(
                    downloads_service.download_async(
                        client,
                        notebook_id,
                        artifact_type,
                        output_path,
                        artifact_id=artifact_id,
                        output_format=output_format,
                        slide_deck_format=slide_deck_format,
                    )
                )
                return {"status": "success", **download_result}
            except ServiceError as e:
                message = f"{e.user_message} {e}"
                if not wait or not _download_transient(message) or time.monotonic() >= deadline:
                    raise
                time.sleep(max(0.5, poll_interval))
    except ValidationError as e:
        message = str(e)
        if message.startswith("Unknown artifact type "):
            message = message.replace("Unknown artifact type", "Unknown artifact_type", 1)
        return error_result(message)
    except ServiceError as e:
        return error_result(e.user_message, hint=e.hint)
    except Exception as e:
        return error_result(str(e))
