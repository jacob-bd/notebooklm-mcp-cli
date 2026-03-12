"""Google Docs sync tools — link notebooks to dedicated GDocs and sync data."""

from typing import Any, Optional
from ._utils import get_client, logged_tool
from ...services import gdoc_sync as gdoc_service


@logged_tool()
def notebook_gdoc_link(
    notebook_id: str,
    gdoc_id: str,
    gdoc_url: str = "",
    artifact_id: str = "",
) -> dict[str, Any]:
    """Link a notebook to a dedicated Google Doc for data sync.

    Once linked, use notebook_gdoc_sync to push notebook data (summary,
    sources, case files) to the Google Doc.

    Args:
        notebook_id: Notebook UUID
        gdoc_id: Google Doc ID (the part after /document/d/ in the URL)
        gdoc_url: Full GDoc URL (auto-inferred from gdoc_id if not provided)
        artifact_id: Optional artifact ID — if set, artifact_gdoc_sync will export this artifact to the GDoc
    """
    try:
        result = gdoc_service.link_notebook_gdoc(notebook_id, gdoc_id, gdoc_url, artifact_id)
        return {"status": "success", **result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def notebook_gdoc_unlink(notebook_id: str) -> dict[str, Any]:
    """Remove the Google Doc link for a notebook.

    Args:
        notebook_id: Notebook UUID
    """
    try:
        result = gdoc_service.unlink_notebook_gdoc(notebook_id)
        return {"status": "success", **result}
    except ValueError as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def notebook_gdoc_list() -> dict[str, Any]:
    """List all notebooks with linked Google Docs and their sync status."""
    result = gdoc_service.list_gdoc_links()
    return {"status": "success", **result}


@logged_tool()
def notebook_gdoc_sync(
    notebook_id: str,
    gdoc_id: str = "",
    export_artifact: bool = False,
) -> dict[str, Any]:
    """Sync notebook data to its linked Google Doc.

    Compiles the notebook's AI summary, source list, and associated case files
    into a markdown document, saves it as a case file, and records sync metadata.

    If export_artifact=True and an artifact_id is linked, also exports the artifact to GDoc.

    Args:
        notebook_id: Notebook UUID
        gdoc_id: Override GDoc ID (uses stored link if not provided)
        export_artifact: Trigger artifact export to GDoc after compiling (requires linked artifact_id)
    """
    try:
        client = get_client()
        result = gdoc_service.sync_notebook_to_gdoc(
            client, notebook_id,
            gdoc_id=gdoc_id or None,
            export_artifact=export_artifact,
        )
        return {"status": "success", **result}
    except ValueError as e:
        return {"status": "error", "error": str(e)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def notebook_gdoc_sync_all() -> dict[str, Any]:
    """Sync ALL notebooks that have a linked Google Doc.

    Iterates over all notebook↔GDoc links and syncs each one.
    """
    try:
        client = get_client()
        result = gdoc_service.sync_all_linked(client)
        return {"status": "success", **result}
    except Exception as e:
        return {"status": "error", "error": str(e)}
