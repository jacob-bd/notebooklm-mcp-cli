"""
Filesystem discovery for canonical documentation.

Scans a repository to:
1. Detect tier classification (simple/complex/kitted)
2. Discover all canonical documents per tier
3. Build a DiscoveryResult for validation
"""

from pathlib import Path
from typing import Any, Optional

from .manifest import (
    get_alternate_names,
    get_stored_hashes,
    get_tier_docs,
    load_manifest,
    load_notebook_map,
    resolve_tier3_root,
)
from .models import DiscoveryResult, DocItem, Tier


def discover_repo(
    repo_path: Path,
    manifest: Optional[dict[str, Any]] = None,
    notebook_map: Optional[dict[str, Any]] = None,
) -> DiscoveryResult:
    """
    Discover canonical documentation in a repository.

    Args:
        repo_path: Absolute path to the repository root
        manifest: Pre-loaded manifest (loads default if None)
        notebook_map: Pre-loaded notebook map (loads default if None)

    Returns:
        DiscoveryResult with tier classification and discovered docs
    """
    if manifest is None:
        manifest = load_manifest()
    if notebook_map is None:
        notebook_map = load_notebook_map()

    repo_name = repo_path.name
    stored_hashes = get_stored_hashes(notebook_map, repo_name)

    # Discover Tier 1 docs (always checked)
    tier1_docs = _discover_tier_docs(repo_path, manifest, 1, stored_hashes)

    # Discover Tier 2 docs (always checked, but not required)
    tier2_docs = _discover_tier_docs(repo_path, manifest, 2, stored_hashes)

    # Determine if repo has Tier 3 docs
    tier3_root = resolve_tier3_root(repo_path, repo_name, manifest)
    tier3_docs: list[DocItem] = []

    if tier3_root:
        tier3_docs = _discover_tier3_docs(
            repo_path, tier3_root, manifest, stored_hashes
        )

    # Classify repo tier based on what exists
    tier = _classify_tier(tier1_docs, tier2_docs, tier3_docs, tier3_root)

    all_docs = tier1_docs + tier2_docs + tier3_docs

    return DiscoveryResult(
        repo_path=repo_path,
        repo_name=repo_name,
        tier=tier,
        tier3_root=tier3_root,
        docs=all_docs,
    )


def _discover_tier_docs(
    repo_path: Path,
    manifest: dict[str, Any],
    tier: int,
    stored_hashes: dict[str, str],
) -> list[DocItem]:
    """Discover documents for a specific tier (1 or 2)."""
    docs: list[DocItem] = []
    tier_docs = get_tier_docs(manifest, tier)

    for doc_def in tier_docs:
        doc_path = doc_def["path"]
        full_path = repo_path / doc_path

        # Check if file/directory exists
        exists = full_path.exists()

        # For files, also check alternate names
        if not exists and not doc_path.endswith("/"):
            for alt_name in get_alternate_names(doc_def):
                alt_path = repo_path / alt_name
                if alt_path.exists():
                    exists = True
                    doc_path = alt_name  # Use the actual found path
                    break

        doc_item = DocItem(
            path=Path(doc_path),
            tier=tier,
            purpose=doc_def.get("purpose", ""),
            exists=exists,
            required=doc_def.get("required", False),
            stored_hash=stored_hashes.get(doc_path),
        )
        docs.append(doc_item)

    return docs


def _discover_tier3_docs(
    repo_path: Path,
    tier3_root: Path,
    manifest: dict[str, Any],
    stored_hashes: dict[str, str],
) -> list[DocItem]:
    """
    Discover Tier 3 documents within the resolved tier3_root.

    Tier 3 docs are defined in the manifest with paths like "OVERVIEW.md"
    which get resolved relative to the tier3_root.
    """
    docs: list[DocItem] = []
    tier3_docs = get_tier_docs(manifest, 3)

    for doc_def in tier3_docs:
        # Tier 3 paths are relative to tier3_root
        doc_filename = doc_def["path"]
        full_path = tier3_root / doc_filename

        exists = full_path.exists()

        # Check alternate names
        if not exists:
            for alt_name in get_alternate_names(doc_def):
                alt_path = tier3_root / alt_name
                if alt_path.exists():
                    exists = True
                    doc_filename = alt_name
                    break

        # Store path relative to repo root for consistency
        relative_path = full_path.relative_to(repo_path)
        if exists:
            # Use actual found path
            relative_path = (tier3_root / doc_filename).relative_to(repo_path)

        doc_item = DocItem(
            path=relative_path,
            tier=3,
            purpose=doc_def.get("purpose", ""),
            exists=exists,
            required=doc_def.get("required", False),
            stored_hash=stored_hashes.get(str(relative_path)),
        )
        docs.append(doc_item)

    return docs


def _classify_tier(
    tier1_docs: list[DocItem],
    tier2_docs: list[DocItem],
    tier3_docs: list[DocItem],
    tier3_root: Optional[Path],
) -> Tier:
    """
    Classify repository tier based on what documentation exists.

    Classification logic:
    - KITTED: Has Tier 3 root AND at least one Tier 3 doc exists
    - COMPLEX: Has any Tier 2 doc existing (CLAUDE.md, glossary, folders)
    - SIMPLE: Only Tier 1 docs present
    """
    # Check for Tier 3 (kitted)
    if tier3_root and any(d.exists for d in tier3_docs):
        return Tier.KITTED

    # Check for Tier 2 (complex)
    if any(d.exists for d in tier2_docs):
        return Tier.COMPLEX

    # Default to simple
    return Tier.SIMPLE


def get_existing_docs(result: DiscoveryResult) -> list[DocItem]:
    """Get only docs that exist on disk."""
    return [d for d in result.docs if d.exists]


def get_docs_needing_hash(result: DiscoveryResult) -> list[DocItem]:
    """
    Get docs that exist and need hash computation.

    Returns docs that:
    - Exist on disk
    - Are files (not directories)
    """
    return [
        d for d in result.docs
        if d.exists and not str(d.path).endswith("/")
    ]
