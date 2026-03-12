"""Case file tools - Fast local document store for pre-extracted data."""

from typing import Any, Optional
from ._utils import get_client, logged_tool
from ...services import case_files as cf_service


@logged_tool()
def case_file_list(category: str = "") -> dict[str, Any]:
    """List all case files, optionally filtered by category.

    Args:
        category: Filter by category (evidence, filings, discovery, correspondence,
                  financial, property, notebook-exports, violations, timeline, research, general).
                  Leave empty to list all.
    """
    result = cf_service.case_file_list(category or None)
    return {"status": "success", **result}


@logged_tool()
def case_file_get(
    key: str = "",
    category: str = "",
    filename: str = "",
) -> dict[str, Any]:
    """Get a case file's content by key (e.g. 'evidence/MASTER_INDEX.md') or category+filename.

    Args:
        key: Full key like 'evidence/MASTER_EVIDENCE_INDEX.md'
        category: Category name (use with filename)
        filename: Filename within category (use with category)
    """
    try:
        result = cf_service.case_file_get(
            key=key or None,
            category=category or None,
            filename=filename or None,
        )
        return {"status": "success", **result}
    except (ValueError, FileNotFoundError) as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def case_file_save(
    category: str,
    filename: str,
    content: str,
    tags: list[str] = [],
) -> dict[str, Any]:
    """Save or overwrite a case file.

    Args:
        category: Category (evidence, filings, discovery, etc.)
        filename: Filename (without .md extension is fine)
        content: Markdown content to save
        tags: Optional list of tag strings for metadata
    """
    try:
        result = cf_service.case_file_save(category, filename, content, tags or None)
        return {"status": "success", **result}
    except ValueError as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def case_file_search(query: str) -> dict[str, Any]:
    """Search case files by keyword. Instant local search — no API calls.

    Args:
        query: Space-separated keywords (all must match)
    """
    result = cf_service.case_file_search(query)
    return {"status": "success", **result}


@logged_tool()
def case_file_delete(
    key: str,
    confirm: bool = False,
) -> dict[str, Any]:
    """Delete a case file permanently.

    Args:
        key: Full key like 'evidence/MASTER_EVIDENCE_INDEX.md'
        confirm: Must be True to confirm deletion
    """
    if not confirm:
        return {
            "status": "error",
            "error": "Deletion not confirmed. Set confirm=True after user approval.",
            "warning": "This action is IRREVERSIBLE.",
        }
    try:
        result = cf_service.case_file_delete(key)
        return {"status": "success", **result}
    except (ValueError, FileNotFoundError) as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def case_file_categories() -> dict[str, Any]:
    """List all case file categories with descriptions and file counts."""
    result = cf_service.case_file_categories()
    return {"status": "success", **result}


@logged_tool()
def case_file_from_source(
    source_id: str,
    category: str = "notebook-exports",
    notebook_id: str = "",
) -> dict[str, Any]:
    """Extract raw content from a NotebookLM source and save as a case file.

    Args:
        source_id: Source UUID
        category: Category to save under (default: notebook-exports)
        notebook_id: Notebook UUID (optional, for context)
    """
    try:
        client = get_client()
        result = cf_service.case_file_from_source(
            client, source_id, category
        )
        return {"status": "success", **result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def batch_drive_to_case(
    notebook_id: str,
    category: str = "notebook-exports",
) -> dict[str, Any]:
    """Bulk extract all sources from a notebook and save as case files.

    Args:
        notebook_id: Notebook UUID
        category: Category to save under (default: notebook-exports)
    """
    from ...services.sources import list_drive_sources
    from concurrent.futures import ThreadPoolExecutor, as_completed

    try:
        client = get_client()
        sources_result = list_drive_sources(client, notebook_id)
        # Combine drive and non-drive sources
        drive_sources = sources_result.get("drive_sources", [])
        other_sources = sources_result.get("other_sources", [])
        sources = drive_sources + other_sources

        results = []
        errors = []

        def extract_one(src):
            try:
                r = cf_service.case_file_from_source(
                    client, src["id"], category
                )
                return {"source_id": src["id"], "key": r["key"], "success": True}
            except Exception as ex:
                return {"source_id": src["id"], "error": str(ex), "success": False}

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(extract_one, s): s for s in sources}
            for future in as_completed(futures):
                r = future.result()
                if r["success"]:
                    results.append(r)
                else:
                    errors.append(r)

        return {
            "status": "success",
            "notebook_id": notebook_id,
            "category": category,
            "extracted": len(results),
            "failed": len(errors),
            "files": results,
            "errors": errors,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
