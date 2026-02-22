"""Sources service — shared validation and logic for source management."""

from typing import TypedDict, Optional

from ..core.client import NotebookLMClient
from .errors import ValidationError, ServiceError

VALID_SOURCE_TYPES = ("url", "text", "drive", "file")
VALID_DRIVE_DOC_TYPES = ("doc", "slides", "sheets", "pdf")

# MIME type mapping for Drive doc types
DRIVE_MIME_TYPES = {
    "doc": "application/vnd.google-apps.document",
    "slides": "application/vnd.google-apps.presentation",
    "sheets": "application/vnd.google-apps.spreadsheet",
    "pdf": "application/pdf",
}


class AddSourceResult(TypedDict):
    """Result of adding a source."""
    source_type: str
    source_id: str
    title: str


class DriveSourceInfo(TypedDict, total=False):
    """Info about a Drive source including freshness."""
    id: str
    title: str
    type: str
    stale: Optional[bool]
    drive_doc_id: Optional[str]


class SyncResult(TypedDict):
    """Result of syncing Drive sources."""
    source_id: str
    synced: bool
    error: Optional[str]


class SourceContentResult(TypedDict):
    """Result of getting source content."""
    content: str
    title: str
    source_type: str
    char_count: int


class RenameResult(TypedDict):
    """Result of renaming a source."""
    source_id: str
    title: str


class DescribeResult(TypedDict):
    """Result of describing a source."""
    summary: str
    keywords: list[str]


class DriveListResult(TypedDict):
    """Result of listing Drive sources."""
    drive_sources: list[DriveSourceInfo]
    other_sources: list[dict]
    drive_count: int
    stale_count: int


def validate_source_type(source_type: str) -> None:
    """Validate source type. Raises ValidationError if invalid."""
    if source_type not in VALID_SOURCE_TYPES:
        raise ValidationError(
            f"Unknown source type '{source_type}'. "
            f"Valid types: {', '.join(VALID_SOURCE_TYPES)}",
        )


def resolve_drive_mime_type(doc_type: str) -> str:
    """Convert doc_type shorthand to MIME type.

    Returns the MIME type string, falling back to Google Doc MIME type.
    """
    return DRIVE_MIME_TYPES.get(doc_type, DRIVE_MIME_TYPES["doc"])


def add_source(
    client: NotebookLMClient,
    notebook_id: str,
    source_type: str,
    *,
    url: Optional[str] = None,
    text: Optional[str] = None,
    title: Optional[str] = None,
    file_path: Optional[str] = None,
    document_id: Optional[str] = None,
    doc_type: str = "doc",
    wait: bool = False,
    wait_timeout: float = 120.0,
) -> AddSourceResult:
    """Add a source to a notebook.

    Centralizes validation and routing for all source types.

    Args:
        client: Authenticated NotebookLM client
        notebook_id: Notebook UUID
        source_type: Type of source (url, text, drive, file)
        url: URL to add (required for source_type=url)
        text: Text content (required for source_type=text)
        title: Display title (optional)
        file_path: Local file path (required for source_type=file)
        document_id: Drive document ID (required for source_type=drive)
        doc_type: Drive doc type: doc|slides|sheets|pdf
        wait: Wait for source processing
        wait_timeout: Max seconds to wait

    Returns:
        AddSourceResult with source_type, source_id, title

    Raises:
        ValidationError: If source_type or required params are invalid
        ServiceError: If the add operation fails
    """
    validate_source_type(source_type)

    try:
        if source_type == "url":
            if not url:
                raise ValidationError("url is required for source_type='url'")
            result = client.add_url_source(notebook_id, url, wait=wait, wait_timeout=wait_timeout)
            return _extract_result(result, "url", url)

        elif source_type == "text":
            if not text:
                raise ValidationError("text is required for source_type='text'")
            effective_title = title or "Pasted Text"
            result = client.add_text_source(
                notebook_id, text, effective_title,
                wait=wait, wait_timeout=wait_timeout,
            )
            return _extract_result(result, "text", effective_title)

        elif source_type == "drive":
            if not document_id:
                raise ValidationError("document_id is required for source_type='drive'")
            effective_title = title or "Drive Document"
            mime_type = resolve_drive_mime_type(doc_type)
            result = client.add_drive_source(
                notebook_id, document_id, effective_title, mime_type,
                wait=wait, wait_timeout=wait_timeout,
            )
            return _extract_result(result, "drive", effective_title)

        elif source_type == "file":
            if not file_path:
                raise ValidationError("file_path is required for source_type='file'")
            result = client.add_file(notebook_id, file_path, wait=wait, wait_timeout=wait_timeout)
            fallback_title = str(file_path).split("/")[-1]
            return _extract_result(result, "file", fallback_title)

    except (ValidationError, ServiceError):
        raise
    except Exception as e:
        raise ServiceError(
            f"Failed to add {source_type} source: {e}",
            user_message=f"Could not add {source_type} source.",
        )

    # Should never reach here due to validate_source_type above
    raise ServiceError(f"Unexpected source type: {source_type}")


def _extract_result(
    result: Optional[dict], source_type: str, fallback_title: str,
) -> AddSourceResult:
    """Extract AddSourceResult from client response."""
    if not result or not result.get("id"):
        raise ServiceError(
            f"Failed to add {source_type} source — no ID returned",
            user_message=f"Failed to add {source_type} source.",
        )
    return {
        "source_type": source_type,
        "source_id": result["id"],
        "title": result.get("title", fallback_title),
    }


def list_drive_sources(
    client: NotebookLMClient,
    notebook_id: str,
) -> DriveListResult:
    """List sources with Drive freshness status.

    Args:
        client: Authenticated NotebookLM client
        notebook_id: Notebook UUID

    Returns:
        DriveListResult with drive/other sources and counts

    Raises:
        ServiceError: If listing fails
    """
    try:
        sources = client.get_notebook_sources_with_types(notebook_id)
    except Exception as e:
        raise ServiceError(
            f"Failed to list sources: {e}",
            user_message="Could not list notebook sources.",
        )

    drive_sources: list[DriveSourceInfo] = []
    other_sources: list[dict] = []

    for source in sources:
        source_info: dict = {
            "id": source.get("id"),
            "title": source.get("title"),
            "type": source.get("source_type_name"),
        }

        if source.get("can_sync"):
            is_fresh = client.check_source_freshness(source["id"])
            source_info["stale"] = not is_fresh if is_fresh is not None else None
            source_info["drive_doc_id"] = source.get("drive_doc_id")
            drive_sources.append(source_info)
        else:
            other_sources.append(source_info)

    return {
        "drive_sources": drive_sources,
        "other_sources": other_sources,
        "drive_count": len(drive_sources),
        "stale_count": sum(1 for s in drive_sources if s.get("stale")),
    }


def sync_drive_sources(
    client: NotebookLMClient,
    source_ids: list[str],
) -> list[SyncResult]:
    """Sync Drive sources with latest content.

    Args:
        client: Authenticated NotebookLM client
        source_ids: Source UUIDs to sync

    Returns:
        List of SyncResult per source

    Raises:
        ServiceError: If the sync operation fails entirely
    """
    if not source_ids:
        raise ValidationError("No source IDs provided for sync.")

    results: list[SyncResult] = []
    for source_id in source_ids:
        try:
            result = client.sync_drive_source(source_id)
            results.append({"source_id": source_id, "synced": bool(result), "error": None})
        except Exception as e:
            results.append({"source_id": source_id, "synced": False, "error": str(e)})

    return results


def rename_source(
    client: NotebookLMClient,
    notebook_id: str,
    source_id: str,
    new_title: str,
) -> RenameResult:
    """Rename a source in a notebook.

    Args:
        client: Authenticated NotebookLM client
        notebook_id: Notebook UUID containing the source
        source_id: Source UUID to rename
        new_title: New display title

    Returns:
        RenameResult with source_id and new title

    Raises:
        ValidationError: If new_title is empty
        ServiceError: If rename fails
    """
    if not new_title or not new_title.strip():
        raise ValidationError("new_title cannot be empty.")

    try:
        result = client.rename_source(notebook_id, source_id, new_title.strip())
        if not result:
            raise ServiceError(
                f"Rename returned no data for source {source_id}",
                user_message="Failed to rename source.",
            )
        return {
            "source_id": result["id"],
            "title": result["title"],
        }
    except (ValidationError, ServiceError):
        raise
    except Exception as e:
        raise ServiceError(
            f"Failed to rename source {source_id}: {e}",
            user_message="Failed to rename source.",
        )


def delete_source(
    client: NotebookLMClient,
    source_id: str,
) -> None:
    """Delete a source permanently.

    Args:
        client: Authenticated NotebookLM client
        source_id: Source UUID

    Raises:
        ServiceError: If deletion fails
    """
    try:
        result = client.delete_source(source_id)
        if not result:
            raise ServiceError(
                f"Delete returned falsy for source {source_id}",
                user_message="Failed to delete source.",
            )
    except ServiceError:
        raise
    except Exception as e:
        raise ServiceError(
            f"Failed to delete source {source_id}: {e}",
            user_message="Failed to delete source.",
        )


def describe_source(
    client: NotebookLMClient,
    source_id: str,
) -> DescribeResult:
    """Get AI-generated source summary with keywords.

    Args:
        client: Authenticated NotebookLM client
        source_id: Source UUID

    Returns:
        DescribeResult with summary and keywords

    Raises:
        ServiceError: If describe fails
    """
    try:
        result = client.get_source_guide(source_id)
        if not result:
            raise ServiceError(
                f"No description returned for source {source_id}",
                user_message="Failed to get source summary.",
            )
        return {
            "summary": result.get("summary", ""),
            "keywords": result.get("keywords", []),
        }
    except ServiceError:
        raise
    except Exception as e:
        raise ServiceError(
            f"Failed to describe source {source_id}: {e}",
            user_message="Failed to get source summary.",
        )


def get_source_content(
    client: NotebookLMClient,
    source_id: str,
) -> SourceContentResult:
    """Get raw text content of a source (no AI processing).

    Args:
        client: Authenticated NotebookLM client
        source_id: Source UUID

    Returns:
        SourceContentResult with content, title, type, and char_count

    Raises:
        ServiceError: If content retrieval fails
    """
    try:
        result = client.get_source_fulltext(source_id)
        if not result:
            raise ServiceError(
                f"No content returned for source {source_id}",
                user_message="Failed to get source content.",
            )
        content = result.get("content", "")
        return {
            "content": content,
            "title": result.get("title", ""),
            "source_type": result.get("type", "unknown"),
            "char_count": len(content),
        }
    except ServiceError:
        raise
    except Exception as e:
        raise ServiceError(
            f"Failed to get content for source {source_id}: {e}",
            user_message="Failed to get source content.",
        )
