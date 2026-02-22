"""Downloads service — shared validation and routing for artifact downloads."""

from typing import TypedDict, Optional, Callable, Any

from ..core.client import NotebookLMClient
from .errors import ValidationError, ServiceError

VALID_ARTIFACT_TYPES = (
    "audio", "video", "report", "mind_map", "slide_deck",
    "infographic", "data_table", "quiz", "flashcards",
)

VALID_OUTPUT_FORMATS = ("json", "markdown", "html")

# Types that support async streaming downloads with progress callbacks
STREAMING_TYPES = ("audio", "video", "slide_deck", "infographic")

# Types that support output_format (json/markdown/html)
INTERACTIVE_TYPES = ("quiz", "flashcards")

# Extension map per artifact type (used for default filenames)
DEFAULT_EXTENSIONS = {
    "audio": "m4a",
    "video": "mp4",
    "report": "md",
    "mind_map": "json",
    "slide_deck": "pdf",
    "infographic": "png",
    "data_table": "csv",
    "quiz": "json",        # varies by format
    "flashcards": "json",  # varies by format
}

# Extension map for output formats (quiz/flashcards)
FORMAT_EXTENSIONS = {
    "json": "json",
    "markdown": "md",
    "html": "html",
}


class DownloadResult(TypedDict):
    """Result of a download operation."""
    artifact_type: str
    path: str


def validate_artifact_type(artifact_type: str) -> None:
    """Validate artifact type. Raises ValidationError if invalid."""
    if artifact_type not in VALID_ARTIFACT_TYPES:
        raise ValidationError(
            f"Unknown artifact type '{artifact_type}'. "
            f"Valid types: {', '.join(VALID_ARTIFACT_TYPES)}",
        )


def validate_output_format(output_format: str) -> None:
    """Validate output format for interactive types. Raises ValidationError if invalid."""
    if output_format not in VALID_OUTPUT_FORMATS:
        raise ValidationError(
            f"Invalid output format '{output_format}'. "
            f"Valid formats: {', '.join(VALID_OUTPUT_FORMATS)}",
        )


def get_default_extension(artifact_type: str, output_format: str = "json") -> str:
    """Get default file extension for an artifact type.

    For interactive types (quiz/flashcards), depends on output_format.
    """
    if artifact_type in INTERACTIVE_TYPES:
        return FORMAT_EXTENSIONS.get(output_format, "json")
    return DEFAULT_EXTENSIONS.get(artifact_type, "bin")


def download_sync(
    client: NotebookLMClient,
    notebook_id: str,
    artifact_type: str,
    output_path: str,
    artifact_id: Optional[str] = None,
    output_format: str = "json",
) -> DownloadResult:
    """Download a non-streaming artifact synchronously.

    For: report, mind_map, data_table, quiz, flashcards.

    Args:
        client: Authenticated NotebookLM client
        notebook_id: Notebook UUID
        artifact_type: Type of artifact
        output_path: Path to save file
        artifact_id: Specific artifact ID (optional)
        output_format: For quiz/flashcards: json|markdown|html

    Returns:
        DownloadResult with artifact_type and path

    Raises:
        ValidationError: If artifact_type or output_format is invalid
        ServiceError: If the download fails
    """
    validate_artifact_type(artifact_type)

    if artifact_type in INTERACTIVE_TYPES:
        validate_output_format(output_format)

    try:
        saved_path = _dispatch_sync(
            client, notebook_id, artifact_type,
            output_path, artifact_id, output_format,
        )
    except (ValidationError, ServiceError):
        raise
    except Exception as e:
        raise ServiceError(
            f"Failed to download {artifact_type}: {e}",
            user_message=f"Download failed for {artifact_type}.",
        )

    if not saved_path:
        raise ServiceError(
            f"Download returned no path for {artifact_type}",
            user_message=f"{artifact_type} is not ready or does not exist.",
        )

    return {"artifact_type": artifact_type, "path": saved_path}


async def download_async(
    client: NotebookLMClient,
    notebook_id: str,
    artifact_type: str,
    output_path: str,
    artifact_id: Optional[str] = None,
    output_format: str = "json",
    progress_callback: Optional[Callable[[int, int], None]] = None,
    slide_deck_format: str = "pdf",
) -> DownloadResult:
    """Download a streaming artifact asynchronously.

    For: audio, video, slide_deck, infographic, quiz, flashcards.

    Args:
        client: Authenticated NotebookLM client
        notebook_id: Notebook UUID
        artifact_type: Type of artifact
        output_path: Path to save file
        artifact_id: Specific artifact ID (optional)
        output_format: For quiz/flashcards: json|markdown|html
        progress_callback: Called with (current, total) for progress tracking
        slide_deck_format: For slide_deck only: "pdf" (default) or "pptx"

    Returns:
        DownloadResult with artifact_type and path

    Raises:
        ValidationError: If artifact_type or output_format is invalid
        ServiceError: If the download fails
    """
    validate_artifact_type(artifact_type)

    if artifact_type in INTERACTIVE_TYPES:
        validate_output_format(output_format)

    try:
        saved_path = await _dispatch_async(
            client, notebook_id, artifact_type,
            output_path, artifact_id, output_format,
            progress_callback,
            slide_deck_format=slide_deck_format,
        )
    except (ValidationError, ServiceError):
        raise
    except Exception as e:
        raise ServiceError(
            f"Failed to download {artifact_type}: {e}",
            user_message=f"Download failed for {artifact_type}.",
        )

    if not saved_path:
        raise ServiceError(
            f"Download returned no path for {artifact_type}",
            user_message=f"{artifact_type} is not ready or does not exist.",
        )

    return {"artifact_type": artifact_type, "path": saved_path}


def _dispatch_sync(
    client: NotebookLMClient,
    notebook_id: str,
    artifact_type: str,
    output_path: str,
    artifact_id: Optional[str],
    output_format: str,
) -> str:
    """Route to the correct synchronous client method."""
    if artifact_type == "report":
        return client.download_report(notebook_id, output_path, artifact_id)
    elif artifact_type == "mind_map":
        return client.download_mind_map(notebook_id, output_path, artifact_id)
    elif artifact_type == "data_table":
        return client.download_data_table(notebook_id, output_path, artifact_id)
    else:
        raise ValidationError(
            f"Artifact type '{artifact_type}' requires async download. "
            f"Use download_async() instead.",
        )


async def _dispatch_async(
    client: NotebookLMClient,
    notebook_id: str,
    artifact_type: str,
    output_path: str,
    artifact_id: Optional[str],
    output_format: str,
    progress_callback: Optional[Callable[[int, int], None]],
    slide_deck_format: str = "pdf",
) -> str:
    """Route to the correct async client method."""
    if artifact_type == "audio":
        return await client.download_audio(
            notebook_id, output_path, artifact_id,
            progress_callback=progress_callback,
        )
    elif artifact_type == "video":
        return await client.download_video(
            notebook_id, output_path, artifact_id,
            progress_callback=progress_callback,
        )
    elif artifact_type == "slide_deck":
        return await client.download_slide_deck(
            notebook_id, output_path, artifact_id,
            progress_callback=progress_callback,
            file_format=slide_deck_format,
        )
    elif artifact_type == "infographic":
        return await client.download_infographic(
            notebook_id, output_path, artifact_id,
            progress_callback=progress_callback,
        )
    elif artifact_type == "quiz":
        return await client.download_quiz(
            notebook_id, output_path, artifact_id, output_format,
        )
    elif artifact_type == "flashcards":
        return await client.download_flashcards(
            notebook_id, output_path, artifact_id, output_format,
        )
    else:
        raise ValidationError(
            f"Artifact type '{artifact_type}' is not supported for async download.",
        )
