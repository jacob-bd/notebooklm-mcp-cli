"""
PROJECT_PRIMER.md generator orchestration.

Main entry point for generating primers from repository documentation.
"""

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from .render import render_primer
from .sources import RepoSources, gather_sources


@dataclass
class GenerationResult:
    """Result of primer generation."""
    repo_id: str
    primer_path: Path
    primer_hash: str
    repo_sha: str
    generated_at: str
    tier: str                           # Resolved tier (detected or overridden)
    tier_detected: str                  # What the generator actually found
    source_count: int
    success: bool
    error: Optional[str] = None
    warnings: list[str] = None          # Compliance/quality warnings

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


def generate_primer(
    repo_path: Path,
    output_path: Optional[Path] = None,
) -> GenerationResult:
    """
    Generate a PROJECT_PRIMER.md for a repository.

    Args:
        repo_path: Path to the repository root
        output_path: Where to write the primer (default: repo_path/PROJECT_PRIMER.md)

    Returns:
        GenerationResult with metadata about the generated primer
    """
    repo_path = Path(repo_path).resolve()
    repo_id = repo_path.name

    if output_path is None:
        output_path = repo_path / "PROJECT_PRIMER.md"
    else:
        output_path = Path(output_path).resolve()

    generated_at = datetime.now().isoformat(timespec="seconds")

    try:
        # Gather sources
        sources = gather_sources(repo_path)

        # Detect tier and check for target override
        tier_detected = sources.tier.value
        tier_target = _get_tier_target(repo_id)
        tier_resolved = tier_target if tier_target else tier_detected

        # Collect warnings
        warnings = []

        # Check for tier mismatch
        if tier_target and tier_target != tier_detected:
            warnings.append(
                f"Tier mismatch: detected={tier_detected}, target={tier_target}"
            )

        # Check for RELATIONS.yaml (required by Betty Protocol canon)
        has_relations = any(d.name.upper() == "RELATIONS.YAML" for d in sources.docs)
        if not has_relations:
            warnings.append(
                "Boundaries incomplete: RELATIONS.yaml missing (required by canon)"
            )

        # Render primer
        primer_content = render_primer(sources)

        # Calculate hash
        primer_hash = _compute_hash(primer_content)

        # Write output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(primer_content, encoding="utf-8")

        return GenerationResult(
            repo_id=repo_id,
            primer_path=output_path,
            primer_hash=primer_hash,
            repo_sha=sources.repo_sha,
            generated_at=generated_at,
            tier=tier_resolved,
            tier_detected=tier_detected,
            source_count=len(sources.docs),
            success=True,
            warnings=warnings,
        )

    except Exception as e:
        return GenerationResult(
            repo_id=repo_id,
            primer_path=output_path,
            primer_hash="",
            repo_sha="",
            generated_at=generated_at,
            tier="unknown",
            tier_detected="unknown",
            source_count=0,
            success=False,
            error=str(e),
        )


def _compute_hash(content: str) -> str:
    """Compute SHA-256 hash prefix for content."""
    full_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return f"sha256:{full_hash[:12]}"


def _get_tier_target(repo_id: str) -> Optional[str]:
    """Get target tier from notebook_map.yaml primers section if defined."""
    try:
        from ..doc_refresh.manifest import load_notebook_map

        notebook_map = load_notebook_map()
        primers = notebook_map.get("primers", {})
        primer_entry = primers.get(repo_id, {})
        return primer_entry.get("tier_target") or primer_entry.get("tier")
    except Exception:
        return None


def get_workspace_root() -> Path:
    """Get workspace root from notebook_map.yaml."""
    from ..doc_refresh.manifest import load_notebook_map

    notebook_map = load_notebook_map()
    workspace_root = notebook_map.get("workspace_root", "~/SyncedProjects")
    return Path(workspace_root).expanduser()


def resolve_repo_path(repo_id: str) -> Optional[Path]:
    """Resolve repo_id to full path using workspace root."""
    workspace_root = get_workspace_root()
    repo_path = workspace_root / repo_id

    if repo_path.exists():
        return repo_path
    return None
