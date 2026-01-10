"""
Content hashing and change detection for documentation files.

Uses SHA-256 truncated to 12 characters for readability.
"""

import hashlib
from pathlib import Path
from typing import Optional

from .models import DocItem, DiscoveryResult, HashComparison


HASH_PREFIX_LENGTH = 12  # Truncate SHA-256 to this many hex chars


def compute_file_hash(file_path: Path) -> str:
    """
    Compute SHA-256 hash of a file's contents.

    Args:
        file_path: Absolute path to file

    Returns:
        First 12 characters of SHA-256 hex digest
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read in chunks for large files
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()[:HASH_PREFIX_LENGTH]


def compute_content_hash(content: str) -> str:
    """
    Compute SHA-256 hash of string content.

    Args:
        content: Text content to hash

    Returns:
        First 12 characters of SHA-256 hex digest
    """
    sha256 = hashlib.sha256(content.encode("utf-8"))
    return sha256.hexdigest()[:HASH_PREFIX_LENGTH]


def hash_doc_item(doc_item: DocItem, repo_path: Path) -> Optional[str]:
    """
    Compute hash for a doc item.

    Args:
        doc_item: Document to hash
        repo_path: Repository root path

    Returns:
        Hash string, or None if doc doesn't exist or is a directory
    """
    if not doc_item.exists:
        return None

    # Skip directories
    if str(doc_item.path).endswith("/"):
        return None

    full_path = repo_path / doc_item.path
    if not full_path.is_file():
        return None

    return compute_file_hash(full_path)


def compute_all_hashes(
    result: DiscoveryResult,
) -> DiscoveryResult:
    """
    Compute hashes for all existing docs in a discovery result.

    Modifies the docs in place to add content_hash and is_changed.

    Args:
        result: DiscoveryResult with docs to hash

    Returns:
        Same DiscoveryResult with hashes populated
    """
    for doc in result.docs:
        if doc.exists and not str(doc.path).endswith("/"):
            full_path = result.repo_path / doc.path
            if full_path.is_file():
                doc.content_hash = compute_file_hash(full_path)
                # Determine if changed
                if doc.stored_hash is not None:
                    doc.is_changed = doc.content_hash != doc.stored_hash
                else:
                    doc.is_changed = None  # No stored hash to compare

    return result


def compare_hashes(result: DiscoveryResult) -> HashComparison:
    """
    Compare computed hashes against stored hashes.

    Args:
        result: DiscoveryResult with content_hash populated

    Returns:
        HashComparison with categorized docs
    """
    changed: list[DocItem] = []
    unchanged: list[DocItem] = []
    new_docs: list[DocItem] = []

    for doc in result.docs:
        # Skip non-existent docs and directories
        if not doc.exists or str(doc.path).endswith("/"):
            continue

        if doc.content_hash is None:
            continue

        if doc.stored_hash is None:
            # No stored hash means new doc
            new_docs.append(doc)
        elif doc.content_hash != doc.stored_hash:
            changed.append(doc)
        else:
            unchanged.append(doc)

    total = len(changed) + len(unchanged) + len(new_docs)

    return HashComparison(
        total_docs=total,
        changed_docs=changed,
        unchanged_docs=unchanged,
        new_docs=new_docs,
    )


def calculate_change_delta(comparison: HashComparison) -> float:
    """
    Calculate the percentage of tracked docs that have changed.

    Args:
        comparison: HashComparison result

    Returns:
        Float between 0.0 and 1.0 representing change percentage
        Excludes new docs from the calculation (they don't count as "changes")
    """
    return comparison.change_ratio_simple


def should_regenerate_artifacts(
    comparison: HashComparison,
    major_version_bump: bool = False,
    force: bool = False,
    threshold: float = 0.15,
) -> bool:
    """
    Determine if artifacts should be regenerated based on change criteria.

    Regeneration triggers:
    - Force flag is set
    - Major version bump detected
    - Content delta exceeds threshold (default 15%)

    Args:
        comparison: HashComparison result
        major_version_bump: True if major version increased
        force: Force regeneration regardless of other criteria
        threshold: Change percentage threshold (default 0.15 = 15%)

    Returns:
        True if artifacts should be regenerated
    """
    if force:
        return True

    if major_version_bump:
        return True

    delta = calculate_change_delta(comparison)
    return delta > threshold


def generate_hash_dict(result: DiscoveryResult) -> dict[str, str]:
    """
    Generate a dict of path -> hash for storing in notebook_map.yaml.

    Args:
        result: DiscoveryResult with hashes computed

    Returns:
        Dict mapping relative path strings to hash strings
    """
    hashes: dict[str, str] = {}
    for doc in result.docs:
        if doc.content_hash is not None:
            hashes[str(doc.path)] = doc.content_hash
    return hashes
