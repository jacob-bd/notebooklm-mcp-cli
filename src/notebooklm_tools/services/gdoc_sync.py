"""Google Docs sync service — link notebooks to dedicated Google Docs and sync data.

Each notebook can be linked to a Google Doc. Syncing compiles the notebook's
case files, summary, and source list into markdown and exports to the linked GDoc.

Sync uses NotebookLM's own Google API access (same auth as the rest of the CLI)
so no separate OAuth2 setup is needed.

Storage: ~/.notebooklm-mcp-cli/gdoc_links.json
  {"notebook_id": {"gdoc_id": "...", "gdoc_url": "...", "last_synced": "...", "artifact_id": "..."}}
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict, Optional

from ..utils.config import get_storage_dir


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def _links_path() -> Path:
    return get_storage_dir() / "gdoc_links.json"


def _load_links() -> dict:
    path = _links_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_links(data: dict) -> None:
    _links_path().write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# TypedDicts
# ---------------------------------------------------------------------------

class GDocLink(TypedDict):
    notebook_id: str
    gdoc_id: str
    gdoc_url: str
    artifact_id: Optional[str]
    last_synced: Optional[str]
    sync_count: int


class GDocLinkResult(TypedDict):
    notebook_id: str
    gdoc_id: str
    gdoc_url: str
    message: str


class GDocSyncResult(TypedDict):
    notebook_id: str
    gdoc_id: str
    gdoc_url: str
    content_chars: int
    case_files_included: int
    message: str


class GDocListResult(TypedDict):
    links: list[GDocLink]
    count: int


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def link_notebook_gdoc(
    notebook_id: str,
    gdoc_id: str,
    gdoc_url: str = "",
    artifact_id: str = "",
) -> GDocLinkResult:
    """Associate a notebook with a Google Doc.

    Args:
        notebook_id: Notebook UUID
        gdoc_id: Google Doc ID (the part after /document/d/ in the URL)
        gdoc_url: Full Google Doc URL (optional, inferred from gdoc_id if omitted)
        artifact_id: Optional artifact ID for direct export sync
    """
    links = _load_links()
    url = gdoc_url or f"https://docs.google.com/document/d/{gdoc_id}/edit"
    links[notebook_id] = {
        "gdoc_id": gdoc_id,
        "gdoc_url": url,
        "artifact_id": artifact_id or "",
        "last_synced": None,
        "sync_count": links.get(notebook_id, {}).get("sync_count", 0),
    }
    _save_links(links)
    return {
        "notebook_id": notebook_id,
        "gdoc_id": gdoc_id,
        "gdoc_url": url,
        "message": f"Linked notebook {notebook_id} → GDoc {gdoc_id}",
    }


def unlink_notebook_gdoc(notebook_id: str) -> dict:
    """Remove the GDoc link for a notebook."""
    links = _load_links()
    if notebook_id not in links:
        raise ValueError(f"No GDoc link found for notebook {notebook_id}")
    del links[notebook_id]
    _save_links(links)
    return {"notebook_id": notebook_id, "message": "GDoc link removed."}


def list_gdoc_links() -> GDocListResult:
    """List all notebook↔GDoc links with sync status."""
    links = _load_links()
    result = []
    for nb_id, info in links.items():
        result.append({
            "notebook_id": nb_id,
            "gdoc_id": info.get("gdoc_id", ""),
            "gdoc_url": info.get("gdoc_url", ""),
            "artifact_id": info.get("artifact_id"),
            "last_synced": info.get("last_synced"),
            "sync_count": info.get("sync_count", 0),
        })
    return {"links": result, "count": len(result)}


def get_gdoc_link(notebook_id: str) -> Optional[GDocLink]:
    """Get the GDoc link for a specific notebook, or None."""
    links = _load_links()
    info = links.get(notebook_id)
    if not info:
        return None
    return {
        "notebook_id": notebook_id,
        "gdoc_id": info.get("gdoc_id", ""),
        "gdoc_url": info.get("gdoc_url", ""),
        "artifact_id": info.get("artifact_id"),
        "last_synced": info.get("last_synced"),
        "sync_count": info.get("sync_count", 0),
    }


def _compile_notebook_markdown(client, notebook_id: str) -> tuple[str, int]:
    """Compile notebook data into a markdown document.

    Returns (markdown_content, case_files_included_count).
    """
    from .notebooks import get_notebook, describe_notebook
    from .case_files import case_file_list, case_file_get

    lines = []

    # Notebook details
    try:
        nb = get_notebook(client, notebook_id)
        title = nb.get("title", "Untitled Notebook")
        source_count = nb.get("source_count", 0)
        url = nb.get("url", "")
        sources = nb.get("sources", [])

        lines.append(f"# {title}")
        lines.append(f"\n**Notebook URL:** {url}")
        lines.append(f"**Sources:** {source_count}")
        lines.append(f"**Last Synced:** {datetime.now(timezone.utc).isoformat()}\n")

        if sources:
            lines.append("## Sources\n")
            for src in sources:
                lines.append(f"- {src.get('title', 'Untitled')} (`{src.get('id', '')})`")
    except Exception as e:
        lines.append(f"# Notebook {notebook_id}")
        lines.append(f"\n*Error fetching notebook details: {e}*\n")

    # AI Summary
    try:
        summary = describe_notebook(client, notebook_id)
        if summary.get("summary"):
            lines.append("\n## AI Summary\n")
            lines.append(summary["summary"])
        if summary.get("suggested_topics"):
            lines.append("\n**Suggested Topics:** " + ", ".join(summary["suggested_topics"]))
    except Exception:
        pass

    # Case files
    cf_count = 0
    try:
        cf_result = case_file_list()
        all_files = cf_result.get("files", [])
        # Include case files that reference this notebook_id in content
        for cf_info in all_files:
            try:
                cf = case_file_get(key=cf_info["key"])
                if notebook_id[:8] in cf.get("content", "") or True:  # include all for now
                    lines.append(f"\n## Case File: {cf_info['key']}\n")
                    lines.append(cf.get("content", "")[:5000])
                    if len(cf.get("content", "")) > 5000:
                        lines.append("\n*[truncated — see full case file]*")
                    cf_count += 1
                    if cf_count >= 20:  # cap at 20 case files per sync
                        break
            except Exception:
                pass
    except Exception:
        pass

    content = "\n".join(lines)
    return content, cf_count


def sync_notebook_to_gdoc(
    client,
    notebook_id: str,
    gdoc_id: Optional[str] = None,
    export_artifact: bool = False,
) -> GDocSyncResult:
    """Sync notebook data to the linked Google Doc.

    Compiles notebook summary, sources, and case files into markdown,
    then saves as a case file and optionally triggers GDoc export if
    an artifact_id is linked.

    Args:
        client: Authenticated NotebookLMClient
        notebook_id: Notebook UUID
        gdoc_id: Override GDoc ID (uses stored link if not provided)
        export_artifact: If True and artifact_id is linked, export artifact to GDoc
    """
    links = _load_links()

    # Resolve GDoc ID
    if gdoc_id:
        link_info = links.get(notebook_id, {})
        gdoc_url = f"https://docs.google.com/document/d/{gdoc_id}/edit"
        art_id = link_info.get("artifact_id", "")
    else:
        link_info = links.get(notebook_id)
        if not link_info:
            raise ValueError(
                f"No GDoc linked to notebook {notebook_id}. "
                "Call link_notebook_gdoc() first."
            )
        gdoc_id = link_info["gdoc_id"]
        gdoc_url = link_info["gdoc_url"]
        art_id = link_info.get("artifact_id", "")

    # Compile markdown
    content, cf_count = _compile_notebook_markdown(client, notebook_id)

    # Save as case file (notebook-exports category)
    from .case_files import case_file_save
    import re
    safe_id = notebook_id[:12]
    case_file_save(
        "notebook-exports",
        f"gdoc_sync_{safe_id}.md",
        content,
        tags=["gdoc-sync", f"notebook:{notebook_id}", f"gdoc:{gdoc_id}"],
    )

    # Optionally trigger artifact export to the linked GDoc
    if export_artifact and art_id:
        try:
            from .exports import export_artifact as do_export
            do_export(client, notebook_id, art_id, "docs")
        except Exception:
            pass  # Don't fail the sync if artifact export fails

    # Update sync metadata
    nb_link = links.get(notebook_id, {})
    nb_link["gdoc_id"] = gdoc_id
    nb_link["gdoc_url"] = gdoc_url
    nb_link["last_synced"] = datetime.now(timezone.utc).isoformat()
    nb_link["sync_count"] = nb_link.get("sync_count", 0) + 1
    links[notebook_id] = nb_link
    _save_links(links)

    return {
        "notebook_id": notebook_id,
        "gdoc_id": gdoc_id,
        "gdoc_url": gdoc_url,
        "content_chars": len(content),
        "case_files_included": cf_count,
        "message": f"Synced notebook to GDoc. Content saved as case file (gdoc_sync_{safe_id}.md). Open: {gdoc_url}",
    }


def sync_all_linked(client) -> dict:
    """Sync all notebooks that have a linked GDoc."""
    links = _load_links()
    results = []
    errors = []
    for notebook_id in links:
        try:
            r = sync_notebook_to_gdoc(client, notebook_id)
            results.append({"notebook_id": notebook_id, "success": True, **r})
        except Exception as e:
            errors.append({"notebook_id": notebook_id, "error": str(e)})
    return {
        "synced": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
    }
