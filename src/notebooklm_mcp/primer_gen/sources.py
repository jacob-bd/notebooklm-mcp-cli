"""
Source document gathering for primer generation.

Collects canonical documents from a repository based on tier classification.
"""

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from ..doc_refresh.discover import discover_repo
from ..doc_refresh.manifest import load_manifest, load_notebook_map
from ..doc_refresh.models import DiscoveryResult, Tier


@dataclass
class SourceDoc:
    """A source document with its content."""
    path: Path          # Relative path from repo root
    tier: int           # 1, 2, or 3
    name: str           # Filename without path
    content: str        # File content
    purpose: str        # Document purpose (from manifest)


@dataclass
class RepoSources:
    """All source documents gathered from a repository."""
    repo_id: str
    repo_path: Path
    tier: Tier
    repo_sha: str
    docs: list[SourceDoc] = field(default_factory=list)
    meta_yaml: Optional[dict[str, Any]] = None

    # Quick accessors by document name
    @property
    def readme(self) -> Optional[SourceDoc]:
        return next((d for d in self.docs if d.name.upper() == "README.MD"), None)

    @property
    def meta_yaml_doc(self) -> Optional[SourceDoc]:
        return next((d for d in self.docs if d.name.upper() == "META.YAML"), None)

    @property
    def claude_md(self) -> Optional[SourceDoc]:
        return next((d for d in self.docs if d.name.upper() == "CLAUDE.MD"), None)

    @property
    def tier3_docs(self) -> list[SourceDoc]:
        return [d for d in self.docs if d.tier == 3]

    def get_tier3_doc(self, name: str) -> Optional[SourceDoc]:
        """Get a specific Tier 3 doc by base name (e.g., 'OVERVIEW.md')."""
        name_upper = name.upper()
        return next(
            (d for d in self.tier3_docs if d.name.upper() == name_upper),
            None
        )


def gather_sources(repo_path: Path) -> RepoSources:
    """
    Gather all source documents from a repository.

    Args:
        repo_path: Absolute path to the repository root

    Returns:
        RepoSources with all discovered documents and their content
    """
    repo_path = Path(repo_path).resolve()
    repo_id = repo_path.name

    # Use existing discovery to find docs
    discovery = discover_repo(repo_path)

    # Get git SHA
    repo_sha = _get_git_sha(repo_path)

    # Load content for all existing docs
    docs: list[SourceDoc] = []
    for doc_item in discovery.existing_docs:
        full_path = repo_path / doc_item.path
        try:
            content = full_path.read_text(encoding="utf-8")
            docs.append(SourceDoc(
                path=doc_item.path,
                tier=doc_item.tier,
                name=doc_item.path.name,
                content=content,
                purpose=doc_item.purpose,
            ))
        except Exception:
            # Skip docs we can't read
            continue

    # Add RELATIONS.yaml if present and not already discovered
    relations_path = repo_path / "RELATIONS.yaml"
    if relations_path.exists():
        relations_in_docs = any(d.name.upper() == "RELATIONS.YAML" for d in docs)
        if not relations_in_docs:
            try:
                content = relations_path.read_text(encoding="utf-8")
                docs.append(SourceDoc(
                    path=Path("RELATIONS.yaml"),
                    tier=1,  # Tier 1 - canonical
                    name="RELATIONS.yaml",
                    content=content,
                    purpose="Cross-repo boundaries and dependencies",
                ))
            except Exception:
                pass

    # Parse META.yaml if present
    meta_yaml = None
    meta_doc = next((d for d in docs if d.name.upper() == "META.YAML"), None)
    if meta_doc:
        try:
            meta_yaml = yaml.safe_load(meta_doc.content)
        except Exception:
            pass

    return RepoSources(
        repo_id=repo_id,
        repo_path=repo_path,
        tier=discovery.tier,
        repo_sha=repo_sha,
        docs=docs,
        meta_yaml=meta_yaml,
    )


def _get_git_sha(repo_path: Path) -> str:
    """Get short git SHA for the repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=7", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def get_repo_entry_from_map(repo_id: str) -> Optional[dict[str, Any]]:
    """Get notebook entry for a repo from notebook_map.yaml."""
    notebook_map = load_notebook_map()
    notebooks = notebook_map.get("notebooks", {})
    return notebooks.get(repo_id)
