"""
CLI runner for doc-refresh validation.

Provides a simple interface for running validation from the command line
or programmatically from the Ralph loop.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from .discover import discover_repo
from .hashing import compare_hashes, compute_all_hashes
from .manifest import load_manifest, load_notebook_map
from .models import HashComparison, ValidationReport
from .report import (
    format_compact_report,
    format_discovery_report,
    format_validation_report,
)
from .validate import validate_discovery


def run_validation(
    repo_path: Path,
    dry_run: bool = True,
    verbose: bool = False,
) -> tuple[ValidationReport, Optional[HashComparison]]:
    """
    Run full validation pipeline on a repository.

    Args:
        repo_path: Absolute path to repository root
        dry_run: If True, only report (no changes). Default True.
        verbose: If True, print progress messages

    Returns:
        Tuple of (ValidationReport, HashComparison or None)
    """
    if verbose:
        print(f"Validating: {repo_path}")

    # Load manifest and notebook map
    manifest = load_manifest()
    notebook_map = load_notebook_map()

    # Phase 1: Discovery
    if verbose:
        print("  Phase 1: Discovering documents...")
    result = discover_repo(repo_path, manifest, notebook_map)

    if verbose:
        print(f"    Tier: {result.tier.value}")
        print(f"    Docs found: {len(result.existing_docs)}/{len(result.docs)}")

    # Phase 2: Compute hashes
    if verbose:
        print("  Phase 2: Computing hashes...")
    result = compute_all_hashes(result)

    # Phase 3: Compare hashes
    comparison = compare_hashes(result)

    if verbose:
        print(f"    Changed: {len(comparison.changed_docs)}")
        print(f"    Unchanged: {len(comparison.unchanged_docs)}")
        print(f"    New: {len(comparison.new_docs)}")

    # Phase 4: Validate documents
    if verbose:
        print("  Phase 3: Validating documents...")
    report = validate_discovery(result)
    report.hash_comparison = comparison

    if verbose:
        print(f"    Errors: {len(report.errors)}")
        print(f"    Warnings: {len(report.warnings)}")
        print(f"    Valid: {report.is_valid}")

    return report, comparison


def main(args: Optional[list[str]] = None) -> int:
    """
    CLI entrypoint for doc-refresh validation.

    Args:
        args: Command line arguments (uses sys.argv if None)

    Returns:
        Exit code (0 for valid, 1 for invalid, 2 for error)
    """
    parser = argparse.ArgumentParser(
        prog="doc-refresh",
        description="Validate canonical documentation in a repository",
    )
    parser.add_argument(
        "repo_path",
        type=Path,
        nargs="?",
        default=Path.cwd(),
        help="Path to repository (default: current directory)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Report only, no changes (default)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (opposite of --dry-run)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print progress messages",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Output compact one-line summary",
    )
    parser.add_argument(
        "--discovery-only",
        action="store_true",
        help="Only show discovery report (skip validation)",
    )

    parsed = parser.parse_args(args)

    # Resolve repo path
    repo_path = parsed.repo_path.resolve()
    if not repo_path.exists():
        print(f"Error: Repository path does not exist: {repo_path}", file=sys.stderr)
        return 2

    if not repo_path.is_dir():
        print(f"Error: Not a directory: {repo_path}", file=sys.stderr)
        return 2

    dry_run = not parsed.apply

    try:
        # Run validation
        report, comparison = run_validation(
            repo_path=repo_path,
            dry_run=dry_run,
            verbose=parsed.verbose,
        )

        # Output results
        if parsed.discovery_only:
            print(format_discovery_report(report.discovery))
        elif parsed.compact:
            print(format_compact_report(report))
        else:
            print(format_validation_report(report))

        # Return appropriate exit code
        if report.is_valid:
            return 0
        else:
            return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if parsed.verbose:
            import traceback
            traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
