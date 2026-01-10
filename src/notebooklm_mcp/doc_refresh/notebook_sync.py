"""
NotebookLM source synchronization for doc-refresh.

Handles syncing documentation to NotebookLM notebooks:
- Deterministic source titles for matching
- Add/update/delete sync planning
- Apply sync to NotebookLM via API
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .models import DiscoveryResult, DocItem, HashComparison


# Source title format for deterministic matching
SOURCE_TITLE_FORMAT = "DOC: {repo_key} :: {rel_path}"


@dataclass
class SourceInfo:
    """Information about a NotebookLM source."""

    source_id: str
    title: str
    source_type: str  # "text", "url", "drive", etc.


@dataclass
class SyncAction:
    """A single sync action to perform."""

    action: str  # "add", "update", "delete"
    doc_path: Path
    reason: str
    source_id: Optional[str] = None  # For delete/update
    content_hash: Optional[str] = None  # For add/update


@dataclass
class SyncPlan:
    """Plan for syncing docs to NotebookLM."""

    repo_key: str
    notebook_id: Optional[str]
    actions: list[SyncAction] = field(default_factory=list)
    notebook_exists: bool = False
    needs_create: bool = False

    @property
    def adds(self) -> list[SyncAction]:
        return [a for a in self.actions if a.action == "add"]

    @property
    def updates(self) -> list[SyncAction]:
        return [a for a in self.actions if a.action == "update"]

    @property
    def deletes(self) -> list[SyncAction]:
        return [a for a in self.actions if a.action == "delete"]

    @property
    def has_changes(self) -> bool:
        return len(self.actions) > 0 or self.needs_create


@dataclass
class SyncResult:
    """Result of applying a sync plan."""

    success: bool
    notebook_id: str
    sources_added: int = 0
    sources_updated: int = 0
    sources_deleted: int = 0
    errors: list[str] = field(default_factory=list)
    doc_states: dict[str, dict] = field(default_factory=dict)  # path -> {hash, source_id, updated_at}


def make_source_title(repo_key: str, rel_path: str) -> str:
    """
    Generate a deterministic source title for matching.

    Format: "DOC: {repo_key} :: {rel_path}"
    """
    return SOURCE_TITLE_FORMAT.format(repo_key=repo_key, rel_path=rel_path)


def parse_source_title(title: str) -> tuple[Optional[str], Optional[str]]:
    """
    Parse a source title to extract repo_key and rel_path.

    Returns:
        Tuple of (repo_key, rel_path) or (None, None) if not a doc-refresh source
    """
    if not title.startswith("DOC: "):
        return None, None

    try:
        rest = title[5:]  # Remove "DOC: "
        parts = rest.split(" :: ", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
    except Exception:
        pass

    return None, None


def get_notebook_sources(client: Any, notebook_id: str) -> list[SourceInfo]:
    """
    Get all sources from a NotebookLM notebook.

    Args:
        client: NotebookLMClient instance
        notebook_id: UUID of the notebook

    Returns:
        List of SourceInfo objects
    """
    sources_data = client.get_notebook_sources_with_types(notebook_id)
    sources = []

    for src in sources_data:
        sources.append(
            SourceInfo(
                source_id=src.get("id", ""),
                title=src.get("title", ""),
                source_type=src.get("type", "unknown"),
            )
        )

    return sources


def find_notebook_by_title(client: Any, title: str) -> Optional[str]:
    """
    Find a notebook by exact title match.

    Args:
        client: NotebookLMClient instance
        title: Notebook title to search for

    Returns:
        Notebook ID if found, None otherwise
    """
    notebooks = client.list_notebooks()
    for nb in notebooks:
        if nb.title == title:
            return nb.id
    return None


def ensure_notebook(
    client: Any,
    repo_key: str,
    notebook_map: dict[str, Any],
    apply: bool = False,
) -> tuple[Optional[str], bool]:
    """
    Ensure a notebook exists for the repo.

    Args:
        client: NotebookLMClient instance
        repo_key: Repository key (e.g., "C017_brain-on-tap")
        notebook_map: Loaded notebook_map.yaml data
        apply: If True, create notebook if missing

    Returns:
        Tuple of (notebook_id, was_created)
    """
    notebooks = notebook_map.get("notebooks", {})
    repo_data = notebooks.get(repo_key, {})
    notebook_id = repo_data.get("notebook_id")

    # If we have a stored ID, verify it still exists
    if notebook_id:
        try:
            nb = client.get_notebook(notebook_id)
            if nb:
                return notebook_id, False
        except Exception:
            pass
        # Notebook no longer exists, fall through to create

    # Try to find by expected title
    expected_title = f"{repo_key} Documentation"
    found_id = find_notebook_by_title(client, expected_title)
    if found_id:
        return found_id, False

    # Need to create
    if not apply:
        return None, False

    # Create new notebook
    new_nb = client.create_notebook(title=expected_title)
    if new_nb:
        return new_nb.id, True

    return None, False


def compute_sync_plan(
    discovery: DiscoveryResult,
    hash_comparison: HashComparison,
    notebook_id: Optional[str],
    current_sources: list[SourceInfo],
    notebook_exists: bool,
) -> SyncPlan:
    """
    Compute the sync plan for a repository.

    Args:
        discovery: DiscoveryResult from discover_repo()
        hash_comparison: HashComparison from compare_hashes()
        notebook_id: Current notebook ID (may be None)
        current_sources: List of current sources in notebook
        notebook_exists: Whether notebook exists

    Returns:
        SyncPlan with actions to perform
    """
    repo_key = discovery.repo_name
    plan = SyncPlan(
        repo_key=repo_key,
        notebook_id=notebook_id,
        notebook_exists=notebook_exists,
        needs_create=not notebook_exists,
    )

    # Build a map of existing doc-refresh sources by rel_path
    existing_sources: dict[str, SourceInfo] = {}
    for src in current_sources:
        parsed_repo, parsed_path = parse_source_title(src.title)
        if parsed_repo == repo_key and parsed_path:
            existing_sources[parsed_path] = src

    # Determine actions for each existing doc
    for doc in discovery.existing_docs:
        # Skip directories (check both path suffix and actual filesystem)
        rel_path = str(doc.path)
        if rel_path.endswith("/"):
            continue
        # Also skip if no content_hash (means it's a directory or unreadable)
        if doc.content_hash is None:
            continue
        existing_src = existing_sources.get(rel_path)

        if existing_src:
            # Source exists - check if changed
            if doc.is_changed:
                plan.actions.append(
                    SyncAction(
                        action="update",
                        doc_path=doc.path,
                        reason="Content changed",
                        source_id=existing_src.source_id,
                        content_hash=doc.content_hash,
                    )
                )
            # Remove from existing_sources so we don't delete it
            del existing_sources[rel_path]
        else:
            # Source doesn't exist - add it
            plan.actions.append(
                SyncAction(
                    action="add",
                    doc_path=doc.path,
                    reason="New document" if doc.stored_hash is None else "Missing from notebook",
                    content_hash=doc.content_hash,
                )
            )

    # Any remaining existing_sources are stale (doc no longer exists)
    for rel_path, src in existing_sources.items():
        plan.actions.append(
            SyncAction(
                action="delete",
                doc_path=Path(rel_path),
                reason="Document removed from repo",
                source_id=src.source_id,
            )
        )

    return plan


def apply_sync_plan(
    client: Any,
    plan: SyncPlan,
    repo_path: Path,
) -> SyncResult:
    """
    Apply a sync plan to NotebookLM.

    Args:
        client: NotebookLMClient instance
        plan: SyncPlan to apply
        repo_path: Path to repository root

    Returns:
        SyncResult with outcomes
    """
    result = SyncResult(
        success=True,
        notebook_id=plan.notebook_id or "",
    )

    if not plan.notebook_id:
        result.success = False
        result.errors.append("No notebook ID available")
        return result

    now = datetime.utcnow().isoformat() + "Z"

    # Process deletes first
    for action in plan.deletes:
        try:
            if action.source_id:
                client.delete_source(action.source_id)
                result.sources_deleted += 1
        except Exception as e:
            result.errors.append(f"Failed to delete {action.doc_path}: {e}")

    # Process updates (delete + add)
    for action in plan.updates:
        try:
            # Delete old source
            if action.source_id:
                client.delete_source(action.source_id)

            # Add new source
            full_path = repo_path / action.doc_path
            content = full_path.read_text(encoding="utf-8")
            title = make_source_title(plan.repo_key, str(action.doc_path))

            new_source = client.add_text_source(
                notebook_id=plan.notebook_id,
                text=content,
                title=title,
            )

            if new_source:
                result.sources_updated += 1
                result.doc_states[str(action.doc_path)] = {
                    "hash": action.content_hash,
                    "source_id": new_source.get("id", ""),
                    "updated_at": now,
                }
            else:
                result.errors.append(f"Failed to add updated source for {action.doc_path}")

        except Exception as e:
            result.errors.append(f"Failed to update {action.doc_path}: {e}")

    # Process adds
    for action in plan.adds:
        try:
            full_path = repo_path / action.doc_path
            content = full_path.read_text(encoding="utf-8")
            title = make_source_title(plan.repo_key, str(action.doc_path))

            new_source = client.add_text_source(
                notebook_id=plan.notebook_id,
                text=content,
                title=title,
            )

            if new_source:
                result.sources_added += 1
                result.doc_states[str(action.doc_path)] = {
                    "hash": action.content_hash,
                    "source_id": new_source.get("id", ""),
                    "updated_at": now,
                }
            else:
                result.errors.append(f"Failed to add source for {action.doc_path}")

        except Exception as e:
            result.errors.append(f"Failed to add {action.doc_path}: {e}")

    if result.errors:
        result.success = False

    return result


def format_sync_plan(plan: SyncPlan) -> str:
    """Format a sync plan as human-readable text."""
    lines: list[str] = []
    lines.append(f"# Sync Plan: {plan.repo_key}")
    lines.append("")

    if plan.needs_create:
        lines.append(f"**Notebook:** Will create '{plan.repo_key} Documentation'")
    elif plan.notebook_id:
        lines.append(f"**Notebook ID:** {plan.notebook_id}")
    else:
        lines.append("**Notebook:** Not found (requires --apply to create)")
    lines.append("")

    if not plan.has_changes:
        lines.append("No changes needed - notebook is in sync.")
        return "\n".join(lines)

    lines.append(f"## Actions ({len(plan.actions)} total)")
    lines.append("")

    if plan.adds:
        lines.append(f"### Add ({len(plan.adds)} docs)")
        for action in plan.adds:
            lines.append(f"- {action.doc_path} ({action.reason})")
        lines.append("")

    if plan.updates:
        lines.append(f"### Update ({len(plan.updates)} docs)")
        for action in plan.updates:
            lines.append(f"- {action.doc_path} ({action.reason})")
        lines.append("")

    if plan.deletes:
        lines.append(f"### Delete ({len(plan.deletes)} sources)")
        for action in plan.deletes:
            lines.append(f"- {action.doc_path} ({action.reason})")
        lines.append("")

    return "\n".join(lines)


def format_sync_result(result: SyncResult) -> str:
    """Format a sync result as human-readable text."""
    lines: list[str] = []
    lines.append("# Sync Result")
    lines.append("")
    lines.append(f"**Success:** {'Yes' if result.success else 'No'}")
    lines.append(f"**Notebook ID:** {result.notebook_id}")
    lines.append("")
    lines.append(f"- Sources added: {result.sources_added}")
    lines.append(f"- Sources updated: {result.sources_updated}")
    lines.append(f"- Sources deleted: {result.sources_deleted}")

    if result.errors:
        lines.append("")
        lines.append("## Errors")
        for err in result.errors:
            lines.append(f"- {err}")

    return "\n".join(lines)
