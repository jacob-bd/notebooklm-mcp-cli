"""Source tools - Source management with consolidated source_add."""

from typing import Any

from ._utils import get_client, logged_tool
from ...services import sources as sources_service, ServiceError


@logged_tool()
def source_add(
    notebook_id: str,
    source_type: str,
    url: str | None = None,
    text: str | None = None,
    title: str | None = None,
    file_path: str | None = None,
    document_id: str | None = None,
    doc_type: str = "doc",
    wait: bool = False,
    wait_timeout: float = 120.0,
) -> dict[str, Any]:
    """Add a source to a notebook. Unified tool for all source types.

    Supports: url, text, drive, file

    Args:
        notebook_id: Notebook UUID
        source_type: Type of source to add:
            - url: Web page or YouTube URL
            - text: Pasted text content
            - drive: Google Drive document
            - file: Local file upload (PDF, text, audio)
        url: URL to add (for source_type=url)
        text: Text content to add (for source_type=text)
        title: Display title (for text sources)
        file_path: Local file path (for source_type=file)
        document_id: Google Drive document ID (for source_type=drive)
        doc_type: Drive doc type: doc|slides|sheets|pdf (for source_type=drive)
        wait: If True, wait for source processing to complete before returning
        wait_timeout: Max seconds to wait if wait=True (default 120)

    Example:
        source_add(notebook_id="abc", source_type="url", url="https://example.com")
        source_add(notebook_id="abc", source_type="url", url="https://example.com", wait=True)
        source_add(notebook_id="abc", source_type="file", file_path="/path/to/doc.pdf", wait=True)
    """
    try:
        client = get_client()
        result = sources_service.add_source(
            client, notebook_id, source_type,
            url=url, text=text, title=title,
            file_path=file_path, document_id=document_id,
            doc_type=doc_type, wait=wait, wait_timeout=wait_timeout,
        )
        return {"status": "success", "ready": wait, **result}
    except ServiceError as e:
        return {"status": "error", "error": e.user_message}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def source_list_drive(notebook_id: str) -> dict[str, Any]:
    """List sources with types and Drive freshness status.

    Use before source_sync_drive to identify stale sources.

    Args:
        notebook_id: Notebook UUID
    """
    try:
        client = get_client()
        result = sources_service.list_drive_sources(client, notebook_id)
        return {"status": "success", "notebook_id": notebook_id, **result}
    except ServiceError as e:
        return {"status": "error", "error": e.user_message}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def source_sync_drive(source_ids: list[str], confirm: bool = False) -> dict[str, Any]:
    """Sync Drive sources with latest content. Requires confirm=True.

    Call source_list_drive first to identify stale sources.

    Args:
        source_ids: Source UUIDs to sync
        confirm: Must be True after user approval
    """
    if not confirm:
        return {
            "status": "error",
            "error": "Sync not confirmed. Set confirm=True after user approval.",
            "hint": "Call source_list_drive first to see which sources are stale.",
        }

    try:
        client = get_client()
        results = sources_service.sync_drive_sources(client, source_ids)
        synced_count = sum(1 for r in results if r.get("synced"))
        return {
            "status": "success",
            "synced_count": synced_count,
            "total_count": len(source_ids),
            "results": results,
        }
    except ServiceError as e:
        return {"status": "error", "error": e.user_message}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def source_rename(notebook_id: str, source_id: str, new_title: str) -> dict[str, Any]:
    """Rename a source in a notebook.

    Args:
        notebook_id: Notebook UUID containing the source
        source_id: Source UUID to rename
        new_title: New display title for the source
    """
    try:
        client = get_client()
        result = sources_service.rename_source(client, notebook_id, source_id, new_title)
        return {"status": "success", **result}
    except ServiceError as e:
        return {"status": "error", "error": e.user_message}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def source_delete(source_id: str, confirm: bool = False) -> dict[str, Any]:
    """Delete source permanently. IRREVERSIBLE. Requires confirm=True.

    Args:
        source_id: Source UUID to delete
        confirm: Must be True after user approval
    """
    if not confirm:
        return {
            "status": "error",
            "error": "Deletion not confirmed. Set confirm=True after user approval.",
            "warning": "This action is IRREVERSIBLE.",
        }

    try:
        client = get_client()
        sources_service.delete_source(client, source_id)
        return {
            "status": "success",
            "message": f"Source {source_id} has been permanently deleted.",
        }
    except ServiceError as e:
        return {"status": "error", "error": e.user_message}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def source_describe(source_id: str) -> dict[str, Any]:
    """Get AI-generated source summary with keyword chips.

    Args:
        source_id: Source UUID

    Returns: summary (markdown with **bold** keywords), keywords list
    """
    try:
        client = get_client()
        result = sources_service.describe_source(client, source_id)
        return {"status": "success", **result}
    except ServiceError as e:
        return {"status": "error", "error": e.user_message}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def source_get_content(source_id: str) -> dict[str, Any]:
    """Get raw text content of a source (no AI processing).

    Returns the original indexed text from PDFs, web pages, pasted text,
    or YouTube transcripts. Much faster than notebook_query for content export.

    Args:
        source_id: Source UUID

    Returns: content (str), title (str), source_type (str), char_count (int)
    """
    try:
        client = get_client()
        result = sources_service.get_source_content(client, source_id)
        return {"status": "success", **result}
    except ServiceError as e:
        return {"status": "error", "error": e.user_message}
    except Exception as e:
        return {"status": "error", "error": str(e)}
