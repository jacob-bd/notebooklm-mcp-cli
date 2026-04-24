"""Smart select service — tag management and intelligent notebook selection."""

import json
from pathlib import Path

from ..utils.config import get_storage_dir
from ._compat import TypedDict
from .errors import NotFoundError, ValidationError

TAGS_FILE = "tags.json"


class TagEntry(TypedDict):
    """Tag entry for a notebook."""

    notebook_id: str
    notebook_title: str
    tags: list[str]


class TagListResult(TypedDict):
    """Result of listing all tags."""

    entries: list[TagEntry]
    count: int


class SmartSelectResult(TypedDict):
    """Result of smart notebook selection."""

    query: str
    matched_notebooks: list[TagEntry]
    count: int


def _get_tags_path() -> Path:
    """Get path to tags.json file."""
    return get_storage_dir() / TAGS_FILE


def _load_tags() -> dict[str, TagEntry]:
    """Load tags from disk. Returns dict keyed by notebook_id."""
    path = _get_tags_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data
    except (json.JSONDecodeError, KeyError):
        return {}


def _save_tags(tags: dict[str, TagEntry]) -> None:
    """Save tags to disk."""
    path = _get_tags_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(tags, indent=2, ensure_ascii=False), encoding="utf-8")


def tag_add(
    notebook_id: str,
    tags: list[str],
    notebook_title: str = "",
) -> TagEntry:
    """Add tags to a notebook.

    Args:
        notebook_id: Notebook UUID
        tags: List of tags to add
        notebook_title: Optional notebook title for display

    Returns:
        Updated TagEntry

    Raises:
        ValidationError: If tags list is empty
    """
    if not tags:
        raise ValidationError(
            "Tags list cannot be empty.",
            user_message="Please provide at least one tag.",
        )

    tags = [t.strip().lower() for t in tags if t.strip()]
    if not tags:
        raise ValidationError(
            "Tags list contains only empty strings.",
            user_message="Please provide at least one non-empty tag.",
        )

    all_tags = _load_tags()
    existing = all_tags.get(
        notebook_id,
        {
            "notebook_id": notebook_id,
            "notebook_title": notebook_title,
            "tags": [],
        },
    )

    if notebook_title:
        existing["notebook_title"] = notebook_title

    existing_tags = set(existing["tags"])
    existing_tags.update(tags)
    existing["tags"] = sorted(existing_tags)

    all_tags[notebook_id] = existing
    _save_tags(all_tags)

    return existing


def tag_remove(
    notebook_id: str,
    tags: list[str],
) -> TagEntry:
    """Remove tags from a notebook.

    Args:
        notebook_id: Notebook UUID
        tags: List of tags to remove

    Returns:
        Updated TagEntry

    Raises:
        NotFoundError: If notebook has no tags
    """
    all_tags = _load_tags()

    if notebook_id not in all_tags:
        raise NotFoundError(
            f"No tags found for notebook {notebook_id}",
            user_message=f"Notebook {notebook_id} has no tags.",
        )

    tags_to_remove = {t.strip().lower() for t in tags if t.strip()}
    entry = all_tags[notebook_id]
    entry["tags"] = [t for t in entry["tags"] if t not in tags_to_remove]

    if not entry["tags"]:
        del all_tags[notebook_id]
        _save_tags(all_tags)
        return {
            "notebook_id": notebook_id,
            "notebook_title": entry.get("notebook_title", ""),
            "tags": [],
        }

    all_tags[notebook_id] = entry
    _save_tags(all_tags)
    return entry


def tag_list() -> TagListResult:
    """List all tagged notebooks.

    Returns:
        TagListResult with all entries
    """
    all_tags = _load_tags()
    entries = list(all_tags.values())
    return {
        "entries": entries,
        "count": len(entries),
    }


def smart_select(query: str) -> SmartSelectResult:
    """Select notebooks relevant to a query based on tags.

    Uses simple keyword matching: splits query into words and matches
    against notebook tags. Notebooks are ranked by number of matching tags.

    Args:
        query: Natural language query or comma-separated tags

    Returns:
        SmartSelectResult with matched notebooks sorted by relevance

    Raises:
        ValidationError: If query is empty
    """
    if not query or not query.strip():
        raise ValidationError(
            "Query cannot be empty.",
            user_message="Please provide a query for smart selection.",
        )

    all_tags = _load_tags()
    if not all_tags:
        return {
            "query": query,
            "matched_notebooks": [],
            "count": 0,
        }

    query_terms = {t.strip().lower() for t in query.replace(",", " ").split() if t.strip()}

    scored: list[tuple[int, TagEntry]] = []
    for entry in all_tags.values():
        notebook_tags = set(entry["tags"])
        matches = query_terms & notebook_tags
        if matches:
            scored.append((len(matches), entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    matched = [entry for _, entry in scored]

    return {
        "query": query,
        "matched_notebooks": matched,
        "count": len(matched),
    }
