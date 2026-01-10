"""
Doc Refresh Module - Ralph Loop for Documentation Maintenance

This module provides:
- Canonical document manifest (canonical_docs.yaml)
- Repo-to-notebook mapping (notebook_map.yaml)
- Document discovery and validation
- Hash-based change detection
- NotebookLM source synchronization
- Ralph loop prompt (PROMPT.md)

Invoked via: /doc-refresh [--target PATH] [--force] [--docs-only] [--artifacts LIST]
"""

__version__ = "0.2.0"

# Public API
from .discover import discover_repo, get_docs_needing_hash, get_existing_docs
from .hashing import (
    compare_hashes,
    compute_all_hashes,
    compute_content_hash,
    compute_file_hash,
    generate_hash_dict,
    should_regenerate_artifacts,
)
from .manifest import (
    load_manifest,
    load_notebook_map,
    resolve_tier3_root,
    get_stored_hashes,
    get_tier_docs,
)
from .models import (
    DiscoveryResult,
    DocItem,
    HashComparison,
    IssueSeverity,
    Tier,
    ValidationIssue,
    ValidationReport,
)
from .report import (
    format_compact_report,
    format_discovery_report,
    format_for_yaml,
    format_validation_report,
)
from .runner import main as cli_main, run_validation, run_sync
from .notebook_sync import (
    SyncAction,
    SyncPlan,
    SyncResult,
    apply_sync_plan,
    compute_sync_plan,
    ensure_notebook,
    format_sync_plan,
    format_sync_result,
    make_source_title,
)
from .validate import (
    extract_version,
    is_major_version_bump,
    validate_discovery,
    validate_document,
)

__all__ = [
    # Discovery
    "discover_repo",
    "get_docs_needing_hash",
    "get_existing_docs",
    # Hashing
    "compare_hashes",
    "compute_all_hashes",
    "compute_content_hash",
    "compute_file_hash",
    "generate_hash_dict",
    "should_regenerate_artifacts",
    # Manifest
    "load_manifest",
    "load_notebook_map",
    "resolve_tier3_root",
    "get_stored_hashes",
    "get_tier_docs",
    # Models
    "DiscoveryResult",
    "DocItem",
    "HashComparison",
    "IssueSeverity",
    "Tier",
    "ValidationIssue",
    "ValidationReport",
    # Report
    "format_compact_report",
    "format_discovery_report",
    "format_for_yaml",
    "format_validation_report",
    # Runner
    "cli_main",
    "run_validation",
    "run_sync",
    # Sync
    "SyncAction",
    "SyncPlan",
    "SyncResult",
    "apply_sync_plan",
    "compute_sync_plan",
    "ensure_notebook",
    "format_sync_plan",
    "format_sync_result",
    "make_source_title",
    # Validate
    "extract_version",
    "is_major_version_bump",
    "validate_discovery",
    "validate_document",
]
