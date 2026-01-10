"""
Manifest loading and Tier 3 path resolution.
"""

from pathlib import Path
from typing import Any, Optional

import yaml


# Default manifest location (relative to this module)
DEFAULT_MANIFEST_PATH = Path(__file__).parent / "canonical_docs.yaml"
DEFAULT_NOTEBOOK_MAP_PATH = Path(__file__).parent / "notebook_map.yaml"


def load_manifest(manifest_path: Optional[Path] = None) -> dict[str, Any]:
    """Load the canonical docs manifest YAML."""
    path = manifest_path or DEFAULT_MANIFEST_PATH
    with open(path, "r") as f:
        return yaml.safe_load(f)


def load_notebook_map(map_path: Optional[Path] = None) -> dict[str, Any]:
    """Load the notebook mapping YAML."""
    path = map_path or DEFAULT_NOTEBOOK_MAP_PATH
    with open(path, "r") as f:
        return yaml.safe_load(f)


def resolve_tier3_root(
    repo_path: Path,
    repo_name: str,
    manifest: dict[str, Any],
) -> Optional[Path]:
    """
    Resolve the Tier 3 documentation root for a repo.

    Resolution order:
    1. Check repo_overrides for explicit tier3_root
    2. Try each tier3_candidate in order, using first that exists
    3. Return None if no Tier 3 docs found

    Args:
        repo_path: Absolute path to the repository
        repo_name: Repository folder name (e.g., "C017_brain-on-tap")
        manifest: Loaded manifest dict

    Returns:
        Absolute path to Tier 3 root, or None if not found
    """
    # Check for repo-specific override
    overrides = manifest.get("repo_overrides", {})
    if repo_name in overrides:
        override = overrides[repo_name]
        if "tier3_root" in override:
            tier3_path = repo_path / override["tier3_root"]
            if tier3_path.exists():
                return tier3_path

    # Try tier3_candidates in order
    candidates = manifest.get("tier3_candidates", ["docs/"])
    for candidate in candidates:
        # Support {repo_name} template
        resolved = candidate.replace("{repo_name}", _extract_short_name(repo_name))
        candidate_path = repo_path / resolved
        if candidate_path.exists():
            return candidate_path

    return None


def _extract_short_name(repo_name: str) -> str:
    """
    Extract short name from repo folder name.

    Examples:
        "C017_brain-on-tap" -> "brain_on_tap"
        "P051_mcp-servers" -> "mcp_servers"
        "some-repo" -> "some_repo"
    """
    # Remove prefix like C017_, P051_, etc.
    parts = repo_name.split("_", 1)
    if len(parts) == 2 and parts[0][0].isalpha() and parts[0][1:].isdigit():
        name = parts[1]
    else:
        name = repo_name

    # Convert hyphens to underscores
    return name.replace("-", "_")


def get_tier_docs(manifest: dict[str, Any], tier: int) -> list[dict[str, Any]]:
    """Get document definitions for a specific tier."""
    tier_key = f"tier{tier}"
    tier_data = manifest.get("tiers", {}).get(tier_key, {})
    return tier_data.get("documents", [])


def get_tier3_path_prefix(manifest: dict[str, Any]) -> str:
    """Get the Tier 3 path prefix template from manifest."""
    tier3 = manifest.get("tiers", {}).get("tier3", {})
    return tier3.get("path_prefix", "{tier3_root}")


def get_alternate_names(doc_def: dict[str, Any]) -> list[str]:
    """Get alternate names for a document (e.g., SECURITY_AND_PRIVACY.md)."""
    return doc_def.get("alternate_names", [])


def get_stored_hashes(notebook_map: dict[str, Any], repo_name: str) -> dict[str, str]:
    """
    Get stored document hashes for a repo from notebook_map.yaml.

    Returns:
        Dict mapping doc path (str) to hash (str)
    """
    notebooks = notebook_map.get("notebooks", {})
    repo_data = notebooks.get(repo_name, {})
    return repo_data.get("doc_hashes", {})
