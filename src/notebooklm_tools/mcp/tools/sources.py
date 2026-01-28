"""Source tools - Source management with consolidated source_add."""

from typing import Any

from ._utils import get_client, logged_tool


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

    Example:
        source_add(notebook_id="abc", source_type="url", url="https://example.com")
        source_add(notebook_id="abc", source_type="text", text="Content here", title="My Notes")
        source_add(notebook_id="abc", source_type="file", file_path="/path/to/doc.pdf")
        source_add(notebook_id="abc", source_type="drive", document_id="doc123", doc_type="doc")
    """
    valid_types = ["url", "text", "drive", "file"]
    if source_type not in valid_types:
        return {
            "status": "error",
            "error": f"Unknown source_type '{source_type}'. Valid types: {', '.join(valid_types)}",
        }

    try:
        client = get_client()

        if source_type == "url":
            if not url:
                return {"status": "error", "error": "url is required for source_type='url'"}
            result = client.add_url_source(notebook_id, url)
            if result and result.get("id"):
                return {
                    "status": "success",
                    "source_type": "url",
                    "source_id": result["id"],
                    "title": result.get("title", url),
                    "url": url,
                }

        elif source_type == "text":
            if not text:
                return {"status": "error", "error": "text is required for source_type='text'"}
            result = client.add_text_source(notebook_id, text, title or "Pasted Text")
            if result and result.get("id"):
                return {
                    "status": "success",
                    "source_type": "text",
                    "source_id": result["id"],
                    "title": result.get("title", title or "Pasted Text"),
                }

        elif source_type == "drive":
            if not document_id:
                return {"status": "error", "error": "document_id is required for source_type='drive'"}
            
            # Convert doc_type shorthand to MIME type
            mime_types = {
                "doc": "application/vnd.google-apps.document",
                "slides": "application/vnd.google-apps.presentation",
                "sheets": "application/vnd.google-apps.spreadsheet",
                "pdf": "application/pdf",
            }
            mime_type = mime_types.get(doc_type, "application/vnd.google-apps.document")
            
            result = client.add_drive_source(
                notebook_id, document_id, title or "Drive Document", mime_type
            )
            if result and result.get("id"):
                return {
                    "status": "success",
                    "source_type": "drive",
                    "source_id": result["id"],
                    "title": result.get("title", title),
                    "doc_type": doc_type,
                }

        elif source_type == "file":
            if not file_path:
                return {"status": "error", "error": "file_path is required for source_type='file'"}
            result = client.upload_file(notebook_id, file_path)
            if result and result.get("source_id"):
                return {
                    "status": "success",
                    "source_type": "file",
                    "source_id": result["source_id"],
                    "title": result.get("title", file_path.split("/")[-1]),
                    "file_path": file_path,
                    "method": result.get("method", "unknown"),
                }

        return {"status": "error", "error": f"Failed to add {source_type} source"}
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
        sources = client.get_notebook_sources_with_types(notebook_id)

        # Check freshness for Drive sources
        drive_sources = []
        other_sources = []

        for source in sources:
            source_info = {
                "id": source.get("id"),
                "title": source.get("title"),
                "type": source.get("source_type_name"),  # Use correct key from client
            }

            # Use can_sync flag from client to identify Drive sources
            if source.get("can_sync"):
                # Check if stale - client returns bool (True=fresh, False=stale)
                is_fresh = client.check_source_freshness(source["id"])
                source_info["stale"] = not is_fresh if is_fresh is not None else None
                source_info["drive_doc_id"] = source.get("drive_doc_id")
                drive_sources.append(source_info)
            else:
                other_sources.append(source_info)

        return {
            "status": "success",
            "notebook_id": notebook_id,
            "drive_sources": drive_sources,
            "other_sources": other_sources,
            "drive_count": len(drive_sources),
            "stale_count": sum(1 for s in drive_sources if s.get("stale")),
        }
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
        results = []

        for source_id in source_ids:
            try:
                result = client.sync_drive_source(source_id)
                results.append({"source_id": source_id, "synced": bool(result)})
            except Exception as e:
                results.append({"source_id": source_id, "synced": False, "error": str(e)})

        synced_count = sum(1 for r in results if r.get("synced"))
        return {
            "status": "success",
            "synced_count": synced_count,
            "total_count": len(source_ids),
            "results": results,
        }
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
        result = client.delete_source(source_id)

        if result:
            return {
                "status": "success",
                "message": f"Source {source_id} has been permanently deleted.",
            }
        return {"status": "error", "error": "Failed to delete source"}
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
        result = client.get_source_guide(source_id)

        if result:
            return {
                "status": "success",
                "summary": result.get("summary", ""),
                "keywords": result.get("keywords", []),
            }
        return {"status": "error", "error": "Failed to get source summary"}
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
        result = client.get_source_fulltext(source_id)

        if result:
            content = result.get("content", "")
            return {
                "status": "success",
                "content": content,
                "title": result.get("title", ""),
                "source_type": result.get("type", "unknown"),
                "char_count": len(content),
            }
        return {"status": "error", "error": "Failed to get source content"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
