"""
Data models for doc-refresh validation and discovery.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class Tier(Enum):
    """Repository documentation tier classification."""
    SIMPLE = "simple"      # Tier 1 only
    COMPLEX = "complex"    # Tier 1 + 2
    KITTED = "kitted"      # Tier 1 + 2 + 3


class IssueSeverity(Enum):
    """Validation issue severity levels."""
    ERROR = "error"        # Must fix
    WARNING = "warning"    # Should fix
    INFO = "info"          # FYI


@dataclass
class DocItem:
    """A discovered document with its metadata."""
    path: Path                          # Relative path from repo root
    tier: int                           # 1, 2, or 3
    purpose: str                        # From manifest
    exists: bool                        # Whether file exists
    required: bool                      # Whether file must exist
    content_hash: Optional[str] = None  # SHA-256 prefix (12 chars)
    stored_hash: Optional[str] = None   # Hash from notebook_map.yaml
    is_changed: Optional[bool] = None   # True if hash differs from stored


@dataclass
class DiscoveryResult:
    """Result of scanning a repo for canonical docs."""
    repo_path: Path
    repo_name: str
    tier: Tier
    tier3_root: Optional[Path]          # Resolved Tier 3 path (if kitted)
    docs: list[DocItem] = field(default_factory=list)

    @property
    def tier1_docs(self) -> list[DocItem]:
        return [d for d in self.docs if d.tier == 1]

    @property
    def tier2_docs(self) -> list[DocItem]:
        return [d for d in self.docs if d.tier == 2]

    @property
    def tier3_docs(self) -> list[DocItem]:
        return [d for d in self.docs if d.tier == 3]

    @property
    def existing_docs(self) -> list[DocItem]:
        return [d for d in self.docs if d.exists]

    @property
    def missing_required(self) -> list[DocItem]:
        return [d for d in self.docs if d.required and not d.exists]


@dataclass
class ValidationIssue:
    """A single validation issue found in a document."""
    doc_path: Path
    rule: str                           # Rule ID (e.g., "has_metadata_header")
    severity: IssueSeverity
    message: str
    line_number: Optional[int] = None   # If applicable
    context: Optional[str] = None       # Snippet or additional info


@dataclass
class HashComparison:
    """Result of comparing doc hashes to stored values."""
    total_docs: int
    changed_docs: list[DocItem]
    unchanged_docs: list[DocItem]
    new_docs: list[DocItem]             # Docs with no stored hash

    @property
    def change_ratio_simple(self) -> float:
        """Simple ratio: changed / total (excludes new docs from ratio)."""
        tracked = self.total_docs - len(self.new_docs)
        if tracked == 0:
            return 0.0
        return len(self.changed_docs) / tracked


@dataclass
class ValidationReport:
    """Complete validation report for a repo."""
    discovery: DiscoveryResult
    issues: list[ValidationIssue] = field(default_factory=list)
    hash_comparison: Optional[HashComparison] = None

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == IssueSeverity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == IssueSeverity.WARNING]

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def is_valid(self) -> bool:
        """True if no errors (warnings OK)."""
        return not self.has_errors
