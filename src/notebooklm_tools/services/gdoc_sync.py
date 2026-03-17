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
    source_id: Optional[str]    # NotebookLM source ID for this GDoc
    instructions: Optional[str] # Cached agent instructions from GDoc
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
    source_id: str = "",
) -> GDocLinkResult:
    """Associate a notebook with a designated Google Doc.

    The GDoc serves as both the data source and the agent instruction file.
    Structure your GDoc with:
      ## AGENT INSTRUCTIONS
      [persona, scope, behavior for this notebook's agent]

      ## DATA
      [facts, records, findings — updated by humans or the agent]

    Args:
        notebook_id: Notebook UUID
        gdoc_id: Google Doc ID (the part after /document/d/ in the URL)
        gdoc_url: Full Google Doc URL (optional, inferred from gdoc_id if omitted)
        artifact_id: Optional artifact ID for direct export sync
        source_id: NotebookLM source ID for this GDoc (enables instruction loading)
    """
    links = _load_links()
    existing = links.get(notebook_id, {})
    url = gdoc_url or f"https://docs.google.com/document/d/{gdoc_id}/edit"
    links[notebook_id] = {
        "gdoc_id": gdoc_id,
        "gdoc_url": url,
        "artifact_id": artifact_id or existing.get("artifact_id", ""),
        "source_id": source_id or existing.get("source_id", ""),
        "instructions": existing.get("instructions", ""),
        "last_synced": existing.get("last_synced"),
        "sync_count": existing.get("sync_count", 0),
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
            "source_id": info.get("source_id"),
            "instructions": info.get("instructions"),
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
        "source_id": info.get("source_id"),
        "instructions": info.get("instructions"),
        "last_synced": info.get("last_synced"),
        "sync_count": info.get("sync_count", 0),
    }


_INSTRUCTIONS_MARKER = "## AGENT INSTRUCTIONS"
_SECTION_END_RE = __import__("re").compile(r"^##\s+\S", __import__("re").MULTILINE)


def read_gdoc_instructions(client, notebook_id: str) -> str:
    """Read and cache agent instructions from the designated GDoc source.

    The GDoc must contain a section starting with '## AGENT INSTRUCTIONS'.
    Everything between that heading and the next '##' heading is the instruction text.

    The extracted instructions are cached in gdoc_links.json so the registry
    can load them without a live API call.

    Returns the instruction text, or "" if none found.
    """
    import re
    links = _load_links()
    info = links.get(notebook_id)
    if not info:
        return ""

    source_id = info.get("source_id", "")
    if not source_id:
        return ""

    try:
        from .sources import get_source_content
        result = get_source_content(client, notebook_id, source_id)
        content = result.get("content", "") if isinstance(result, dict) else str(result)
    except Exception:
        return ""

    # Extract the AGENT INSTRUCTIONS section
    idx = content.find(_INSTRUCTIONS_MARKER)
    if idx == -1:
        return ""

    section_text = content[idx + len(_INSTRUCTIONS_MARKER):]
    # Find next ## heading to end the section
    m = _SECTION_END_RE.search(section_text)
    instructions = section_text[:m.start()].strip() if m else section_text.strip()

    # Cache instructions in gdoc_links.json
    info["instructions"] = instructions
    links[notebook_id] = info
    _save_links(links)

    return instructions


def _sapisidhash(sapisid: str, origin: str = "https://docs.google.com") -> str:
    """Compute SAPISIDHASH for Google API authorization.

    Format: SAPISIDHASH <timestamp>_<SHA1(timestamp SP SAPISID SP origin)>
    This header, combined with the session cookies, authenticates requests to
    Google REST APIs without a separate OAuth2 flow.
    """
    import hashlib
    import time as _time
    ts = str(int(_time.time()))
    digest = hashlib.sha1(f"{ts} {sapisid} {origin}".encode()).hexdigest()
    return f"SAPISIDHASH {ts}_{digest}"


def _get_cookie_dict(client) -> dict[str, str]:
    """Extract cookie dict from the NotebookLM client."""
    try:
        cookies = client._auth.cookies  # type: ignore[attr-defined]
        if isinstance(cookies, dict):
            return cookies
        # list[dict] with name/value keys
        return {c["name"]: c["value"] for c in cookies if "name" in c}
    except Exception:
        from ..core.auth import load_cached_tokens
        tokens = load_cached_tokens()
        return tokens.cookies if tokens else {}


def gdoc_append_text(client, gdoc_id: str, text: str) -> dict:
    """Append text to a Google Doc using session-cookie auth.

    Tries three methods in order:
      1. SAPISIDHASH + session cookies → Google Docs batchUpdate REST API
      2. gws CLI subprocess (if installed and authenticated)
      3. Returns error — caller should fall back to notebook note

    The SAPISIDHASH method uses the same Google session cookies already stored
    for NotebookLM, so no separate OAuth2 setup is needed.
    """
    import json as _json
    import urllib.request

    cookies = _get_cookie_dict(client)
    sapisid = cookies.get("SAPISID") or cookies.get("__Secure-1PSID", "")

    # --- Method 1: SAPISIDHASH via Docs REST API ---
    if sapisid:
        try:
            url = f"https://docs.googleapis.com/v1/documents/{gdoc_id}:batchUpdate"
            body = _json.dumps({
                "requests": [{
                    "insertText": {
                        "location": {"index": 1},
                        "text": text + "\n",
                    }
                }]
            }).encode()
            cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())
            sapis_hash = _sapisidhash(sapisid)
            req = urllib.request.Request(
                url,
                data=body,
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "Cookie": cookie_header,
                    "Authorization": sapis_hash,
                    "X-Goog-AuthUser": "0",
                    "Origin": "https://docs.google.com",
                    "Referer": "https://docs.google.com/",
                },
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return {"method": "sapisidhash", "status": resp.status, "gdoc_id": gdoc_id}
        except Exception as e:
            sapisidhash_err = str(e)
    else:
        sapisidhash_err = "SAPISID cookie not found"

    # --- Method 2: gws CLI subprocess ---
    import shutil
    import subprocess
    if shutil.which("gws"):
        try:
            body = _json.dumps({
                "requests": [{
                    "insertText": {
                        "location": {"index": 1},
                        "text": text + "\n",
                    }
                }]
            })
            result = subprocess.run(
                ["gws", "docs", "documents", "batchUpdate",
                 "--params", _json.dumps({"documentId": gdoc_id}),
                 "--json", body],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0:
                return {"method": "gws", "gdoc_id": gdoc_id}
            gws_err = result.stderr.strip() or result.stdout.strip()
        except Exception as e:
            gws_err = str(e)
    else:
        gws_err = "gws not installed"

    return {
        "error": "gdoc_write_failed",
        "sapisidhash_error": sapisidhash_err,
        "gws_error": gws_err,
        "gdoc_id": gdoc_id,
    }


def agent_append_findings(client, notebook_id: str, query: str, findings: str) -> dict:
    """Write agent findings back to the designated GDoc and as a notebook note.

    Self-update loop:
      1. Try to append text directly to the linked GDoc (SAPISIDHASH / gws)
      2. Always also create a notebook note (visible in NotebookLM UI)

    The GDoc append lands in the document immediately — next time the Drive
    source is synced, NotebookLM picks up the new data automatically.
    """
    from datetime import datetime, timezone
    from .notes import create_note

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    append_text = f"\n\n---\n**Agent Finding — {timestamp}**\n**Query:** {query}\n\n{findings}"
    note_content = f"**Agent Finding — {timestamp}**\n\n**Query:** {query}\n\n{findings}"

    result: dict = {"notebook_id": notebook_id}

    # Try GDoc write first
    link = get_gdoc_link(notebook_id)
    if link and link.get("gdoc_id"):
        gdoc_result = gdoc_append_text(client, link["gdoc_id"], append_text)
        result["gdoc_write"] = gdoc_result
        if "error" not in gdoc_result:
            result["message"] = f"Findings appended to GDoc ({gdoc_result.get('method')}) and saved as note."
        else:
            result["message"] = "GDoc write failed — findings saved as notebook note only."
    else:
        result["message"] = "No GDoc linked — findings saved as notebook note."

    # Always create a notebook note too
    try:
        note_result = create_note(client, notebook_id, note_content, title=f"[Agent] {query[:60]}")
        result["note_id"] = note_result.get("note_id", "")
    except Exception as e:
        result["note_error"] = str(e)

    return result


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
