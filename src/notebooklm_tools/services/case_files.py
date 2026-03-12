"""Case file service — pre-extracted markdown documents for instant local lookup.

Case files are markdown documents stored locally at ~/.notebooklm-mcp-cli/case-files/<category>/<filename>.md
They serve as a fast data layer: pre-built summaries agents can read instantly
without hitting the NotebookLM AI (no rate limits, microsecond reads).
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import TypedDict, Optional

from ..utils.config import get_storage_dir

CATEGORIES = {
    "evidence": "Evidence documents and exhibits",
    "filings": "Court filings and pleadings",
    "discovery": "Discovery documents and requests",
    "correspondence": "Legal correspondence and emails",
    "financial": "Financial records and accounting",
    "property": "Property records and chain of title",
    "notebook-exports": "Exported NotebookLM content",
    "violations": "Violation documentation",
    "timeline": "Timeline reconstructions",
    "research": "Legal research and analysis",
    "general": "General documents",
}


def _case_files_dir() -> Path:
    d = get_storage_dir() / "case-files"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _resolve_path(category: str, filename: str) -> Path:
    """Return the full path for a case file, ensuring .md extension."""
    if not filename.endswith(".md"):
        filename = filename + ".md"
    cat_dir = _case_files_dir() / category
    cat_dir.mkdir(parents=True, exist_ok=True)
    return cat_dir / filename


def _parse_key(key: str) -> tuple[str, str]:
    """Parse 'category/filename.md' into (category, filename)."""
    parts = key.split("/", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid case file key '{key}'. Expected format: 'category/filename.md'")
    return parts[0], parts[1]


class CaseFileSaveResult(TypedDict):
    key: str
    category: str
    filename: str
    path: str
    size_bytes: int
    message: str


class CaseFileGetResult(TypedDict):
    key: str
    category: str
    filename: str
    content: str
    size_bytes: int
    modified_at: str


class CaseFileInfo(TypedDict):
    key: str
    category: str
    filename: str
    size_bytes: int
    modified_at: str


class CaseFileListResult(TypedDict):
    files: list[CaseFileInfo]
    count: int
    category_filter: Optional[str]


class CaseFileSearchResult(TypedDict):
    query: str
    matches: list[dict]
    match_count: int


class CaseFileDeleteResult(TypedDict):
    key: str
    message: str


class CaseFileCategoriesResult(TypedDict):
    categories: list[dict]


def case_file_save(
    category: str,
    filename: str,
    content: str,
    tags: Optional[list[str]] = None,
) -> CaseFileSaveResult:
    """Save or overwrite a case file."""
    if category not in CATEGORIES:
        raise ValueError(f"Unknown category '{category}'. Valid: {', '.join(CATEGORIES)}")
    path = _resolve_path(category, filename)
    # Prepend tags as frontmatter comment if provided
    body = content
    if tags:
        tag_line = "<!-- tags: " + ", ".join(tags) + " -->\n\n"
        body = tag_line + content
    path.write_text(body, encoding="utf-8")
    fname = path.name
    key = f"{category}/{fname}"
    return {
        "key": key,
        "category": category,
        "filename": fname,
        "path": str(path),
        "size_bytes": len(body.encode()),
        "message": f"Saved case file: {key}",
    }


def case_file_get(
    key: Optional[str] = None,
    category: Optional[str] = None,
    filename: Optional[str] = None,
) -> CaseFileGetResult:
    """Get a case file by key or category+filename."""
    if key:
        category, filename = _parse_key(key)
    if not category or not filename:
        raise ValueError("Provide either 'key' or both 'category' and 'filename'.")
    path = _resolve_path(category, filename)
    if not path.exists():
        raise FileNotFoundError(f"Case file not found: {category}/{path.name}")
    content = path.read_text(encoding="utf-8")
    stat = path.stat()
    return {
        "key": f"{category}/{path.name}",
        "category": category,
        "filename": path.name,
        "content": content,
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }


def case_file_list(category: Optional[str] = None) -> CaseFileListResult:
    """List all case files, optionally filtered by category."""
    base = _case_files_dir()
    files: list[CaseFileInfo] = []

    if category:
        categories = [category]
    else:
        categories = [d.name for d in base.iterdir() if d.is_dir()]

    for cat in sorted(categories):
        cat_dir = base / cat
        if not cat_dir.exists():
            continue
        for f in sorted(cat_dir.glob("*.md")):
            stat = f.stat()
            files.append({
                "key": f"{cat}/{f.name}",
                "category": cat,
                "filename": f.name,
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })

    return {"files": files, "count": len(files), "category_filter": category}


def case_file_search(query: str) -> CaseFileSearchResult:
    """Keyword search across all case files (local, instant)."""
    terms = [t.lower() for t in query.split() if t]
    base = _case_files_dir()
    matches = []

    for md_file in sorted(base.rglob("*.md")):
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception:
            continue
        lower = content.lower()
        if all(t in lower for t in terms):
            # Collect matched lines for context
            matched_lines = []
            for i, line in enumerate(content.splitlines(), 1):
                if any(t in line.lower() for t in terms):
                    matched_lines.append({"line": i, "text": line.strip()[:200]})
                    if len(matched_lines) >= 5:
                        break
            rel = md_file.relative_to(base)
            parts = str(rel).split("/", 1)
            cat = parts[0] if len(parts) == 2 else "general"
            fname = parts[1] if len(parts) == 2 else parts[0]
            matches.append({
                "key": f"{cat}/{fname}",
                "category": cat,
                "filename": fname,
                "matched_lines": matched_lines,
                "size_bytes": md_file.stat().st_size,
            })

    return {"query": query, "matches": matches, "match_count": len(matches)}


def case_file_delete(key: str) -> CaseFileDeleteResult:
    """Delete a case file by key."""
    category, filename = _parse_key(key)
    path = _resolve_path(category, filename)
    if not path.exists():
        raise FileNotFoundError(f"Case file not found: {key}")
    path.unlink()
    return {"key": key, "message": f"Deleted case file: {key}"}


def case_file_categories() -> CaseFileCategoriesResult:
    """List categories with file counts and descriptions."""
    base = _case_files_dir()
    result = []
    for cat, desc in CATEGORIES.items():
        cat_dir = base / cat
        count = len(list(cat_dir.glob("*.md"))) if cat_dir.exists() else 0
        result.append({"category": cat, "description": desc, "file_count": count})
    return {"categories": result}


def case_file_from_source(
    client,
    source_id: str,
    category: str = "notebook-exports",
    notebook_id: Optional[str] = None,
) -> CaseFileSaveResult:
    """Extract raw content from a NotebookLM source and save as a case file."""
    from .sources import get_source_content
    result = get_source_content(client, source_id)
    content = result.get("content", "")
    title = result.get("title", source_id)
    # Sanitize title for filename
    safe_title = re.sub(r"[^\w\-]", "_", title)[:80]
    filename = f"{safe_title}_{source_id[:8]}.md"
    body = f"# {title}\n\n**Source ID:** {source_id}\n**Extracted:** {datetime.utcnow().isoformat()}Z\n\n---\n\n{content}"
    return case_file_save(category, filename, body)
