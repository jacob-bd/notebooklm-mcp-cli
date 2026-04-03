"""Source tools - Source management with consolidated source_add."""

from typing import Any

from ...services import ServiceError
from ...services import sources as sources_service
from ._utils import coerce_list, get_client, logged_tool


def _paywall_check_url(url: str) -> dict[str, Any] | None:
    """Check a single URL for paywall/login walls.

    Returns a paywall error dict if blocked, None if OK to proceed.
    Respects config sources.paywall_check and sources.approved_domains.
    """
    from urllib.parse import urlparse

    from ...utils.config import get_config
    config = get_config()
    if not config.sources.paywall_check:
        return None

    domain = urlparse(url).netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]

    # Skip check if domain is in user's approved list
    for approved in config.sources.approved_domains:
        if domain == approved or domain.endswith("." + approved):
            return None

    check = sources_service.check_url_accessibility(url)
    if not check["likely_paywall"]:
        return None

    return {
        "status": "paywall_detected",
        "url": url,
        "domain": check["domain"],
        "reason": check["reason"],
        "message": (
            f"This URL appears to require a login or paid subscription: {url}\n"
            "NotebookLM may not be able to access the content."
        ),
        "hint": (
            f"If you have an account on {check['domain']!r}, add it to your approved domains so "
            "future checks are skipped:\n"
            f"  nlm config set sources.approved_domains [\"{check['domain']}\"]\n"
            "To add this URL anyway, call source_add with skip_paywall_check=True."
        ),
    }


@logged_tool()
def source_add(
    notebook_id: str,
    source_type: str,
    url: str | None = None,
    urls: list[str] | None = None,
    text: str | None = None,
    title: str | None = None,
    file_path: str | None = None,
    document_id: str | None = None,
    doc_type: str = "doc",
    wait: bool = False,
    wait_timeout: float = 120.0,
    skip_paywall_check: bool = False,
) -> dict[str, Any]:
    """Add a source to a notebook. Unified tool for all source types.

    Supports: url, text, drive, file

    For URL sources, a paywall/login check is performed before adding. If the URL
    appears to require authentication or a subscription, the tool returns a
    "paywall_detected" status with instructions. Set skip_paywall_check=True to
    bypass (e.g. the user confirms they have an account on that site).

    Args:
        notebook_id: Notebook UUID
        source_type: Type of source to add:
            - url: Web page or YouTube URL
            - text: Pasted text content
            - drive: Google Drive document
            - file: Local file upload (PDF, text, audio)
        url: URL to add (for source_type=url)
        urls: List of URLs to add in bulk (for source_type=url, alternative to url)
        text: Text content to add (for source_type=text)
        title: Display title (for text sources)
        file_path: Local file path (for source_type=file)
        document_id: Google Drive document ID (for source_type=drive)
        doc_type: Drive doc type: doc|slides|sheets|pdf (for source_type=drive)
        wait: If True, wait for source processing to complete before returning
        wait_timeout: Max seconds to wait if wait=True (default 120)
        skip_paywall_check: If True, skip paywall/login check and add URL anyway

    Example:
        source_add(notebook_id="abc", source_type="url", url="https://example.com")
        source_add(notebook_id="abc", source_type="url", urls=["https://a.com", "https://b.com"])
        source_add(notebook_id="abc", source_type="url", url="https://ft.com/article", skip_paywall_check=True)
        source_add(notebook_id="abc", source_type="file", file_path="/path/to/doc.pdf", wait=True)
    """
    try:
        client = get_client()

        # Coerce list params from MCP clients (may arrive as strings)
        urls = coerce_list(urls)

        # Bulk URL add: when urls list is provided
        if urls and source_type == "url":
            # Paywall check each URL individually; skip those that are blocked
            if not skip_paywall_check:
                blocked = []
                allowed_urls = []
                for u in urls:
                    pw = _paywall_check_url(u)
                    if pw:
                        blocked.append(pw)
                    else:
                        allowed_urls.append(u)

                if blocked and not allowed_urls:
                    # All URLs blocked
                    return {
                        "status": "paywall_detected",
                        "message": f"All {len(blocked)} URL(s) appear to require login or payment.",
                        "blocked": blocked,
                        "hint": "Set skip_paywall_check=True to add anyway, or use approved_domains.",
                    }

                if blocked:
                    # Partial — add allowed, report blocked
                    result = sources_service.add_sources(
                        client,
                        notebook_id,
                        [{"source_type": "url", "url": u} for u in allowed_urls],
                        wait=wait,
                        wait_timeout=wait_timeout,
                    )
                    return {
                        "status": "partial",
                        "ready": wait,
                        "added_count": result["added_count"],
                        "failed_count": result["failed_count"] + len(blocked),
                        "results": result["results"],
                        "failures": result["failures"],
                        "paywall_blocked": blocked,
                        "message": (
                            f"Added {result['added_count']} URL(s). "
                            f"{len(blocked)} URL(s) skipped — possible paywall/login required."
                        ),
                    }
            else:
                allowed_urls = urls

            result = sources_service.add_sources(
                client,
                notebook_id,
                [{"source_type": "url", "url": u} for u in allowed_urls],
                wait=wait,
                wait_timeout=wait_timeout,
            )
            out: dict[str, Any] = {"ready": wait, **result}
            out["status"] = "success" if not result["failures"] else "partial"
            if result["failures"]:
                out["message"] = (
                    f"Added {result['added_count']} URL(s). "
                    f"{result['failed_count']} failed — see 'failures' for details."
                )
            return out

        # Single URL: paywall check
        if source_type == "url" and url and not skip_paywall_check:
            pw = _paywall_check_url(url)
            if pw:
                return pw

        # Single source add (existing behavior)
        result_single = sources_service.add_source(
            client,
            notebook_id,
            source_type,
            url=url,
            text=text,
            title=title,
            file_path=file_path,
            document_id=document_id,
            doc_type=doc_type,
            wait=wait,
            wait_timeout=wait_timeout,
        )
        return {"status": "success", "ready": wait, **result_single}
    except ServiceError as e:
        err = {"status": "error", "error": e.user_message}
        if getattr(e, "hint", None):
            err["hint"] = e.hint
        return err
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
        err = {"status": "error", "error": e.user_message}
        if getattr(e, "hint", None):
            err["hint"] = e.hint
        return err
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
        # Coerce list params from MCP clients (may arrive as strings)
        source_ids = coerce_list(source_ids)
        results = sources_service.sync_drive_sources(client, source_ids)
        synced_count = sum(1 for r in results if r.get("synced"))
        return {
            "status": "success",
            "synced_count": synced_count,
            "total_count": len(source_ids),
            "results": results,
        }
    except ServiceError as e:
        err = {"status": "error", "error": e.user_message}
        if getattr(e, "hint", None):
            err["hint"] = e.hint
        return err
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
        err = {"status": "error", "error": e.user_message}
        if getattr(e, "hint", None):
            err["hint"] = e.hint
        return err
    except Exception as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def source_delete(
    source_id: str | None = None,
    source_ids: list[str] | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Delete source(s) permanently. IRREVERSIBLE. Requires confirm=True.

    Args:
        source_id: Source UUID to delete (single)
        source_ids: List of source UUIDs to delete (bulk, alternative to source_id)
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

        # Coerce list params from MCP clients (may arrive as strings)
        source_ids = coerce_list(source_ids)

        # Bulk delete: when source_ids list is provided
        if source_ids:
            sources_service.delete_sources(client, source_ids)
            return {
                "status": "success",
                "message": f"{len(source_ids)} sources have been permanently deleted.",
                "deleted_count": len(source_ids),
            }

        # Single delete (existing behavior)
        if not source_id:
            return {"status": "error", "error": "Either source_id or source_ids is required."}

        sources_service.delete_source(client, source_id)
        return {
            "status": "success",
            "message": f"Source {source_id} has been permanently deleted.",
        }
    except ServiceError as e:
        err = {"status": "error", "error": e.user_message}
        if getattr(e, "hint", None):
            err["hint"] = e.hint
        return err
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
        err = {"status": "error", "error": e.user_message}
        if getattr(e, "hint", None):
            err["hint"] = e.hint
        return err
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
        err = {"status": "error", "error": e.user_message}
        if getattr(e, "hint", None):
            err["hint"] = e.hint
        return err
    except Exception as e:
        return {"status": "error", "error": str(e)}
