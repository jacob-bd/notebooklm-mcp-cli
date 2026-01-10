"""
CLI runner for doc-refresh validation, NotebookLM sync, and artifact refresh.

Provides a simple interface for running validation from the command line
or programmatically from the Ralph loop.
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Optional

import yaml

from .artifact_refresh import (
    ArtifactPlan,
    ArtifactResult,
    apply_artifact_plan,
    compute_artifact_plan,
    format_artifact_plan,
    format_artifact_result,
    parse_artifact_list,
)
from .discover import discover_repo
from .hashing import compare_hashes, compute_all_hashes
from .manifest import load_manifest, load_notebook_map, DEFAULT_NOTEBOOK_MAP_PATH
from .models import HashComparison, ValidationReport
from .notebook_sync import (
    SyncPlan,
    SyncResult,
    apply_sync_plan,
    compute_sync_plan,
    ensure_notebook,
    format_sync_plan,
    format_sync_result,
    get_notebook_sources,
)
from .report import (
    format_compact_report,
    format_discovery_report,
    format_validation_report,
)
from .validate import is_major_version_bump, validate_discovery


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


def run_sync(
    repo_path: Path,
    apply: bool = False,
    verbose: bool = False,
) -> tuple[ValidationReport, HashComparison, SyncPlan, Optional[SyncResult]]:
    """
    Run validation and compute/apply NotebookLM sync.

    Args:
        repo_path: Absolute path to repository root
        apply: If True, apply changes to NotebookLM
        verbose: If True, print progress messages

    Returns:
        Tuple of (ValidationReport, HashComparison, SyncPlan, SyncResult or None)
    """
    # First run validation
    report, comparison = run_validation(repo_path, dry_run=not apply, verbose=verbose)

    if comparison is None:
        raise RuntimeError("Hash comparison failed")

    # Load notebook map for sync
    notebook_map = load_notebook_map()
    repo_key = repo_path.name

    if verbose:
        print("  Phase 4: Computing sync plan...")

    # Get client for NotebookLM operations
    try:
        from ..server import get_client
        client = get_client()
    except Exception as e:
        if verbose:
            print(f"    Warning: Could not initialize NotebookLM client: {e}")
        # Return plan with no notebook access
        plan = SyncPlan(
            repo_key=repo_key,
            notebook_id=None,
            notebook_exists=False,
            needs_create=True,
        )
        # Add all existing docs as "add" actions
        for doc in report.discovery.existing_docs:
            if not str(doc.path).endswith("/"):
                from .notebook_sync import SyncAction
                plan.actions.append(
                    SyncAction(
                        action="add",
                        doc_path=doc.path,
                        reason="Initial sync",
                        content_hash=doc.content_hash,
                    )
                )
        return report, comparison, plan, None

    # Ensure notebook exists (or get existing)
    notebook_id, was_created = ensure_notebook(client, repo_key, notebook_map, apply=apply)

    if verbose:
        if was_created:
            print(f"    Created notebook: {notebook_id}")
        elif notebook_id:
            print(f"    Found notebook: {notebook_id}")
        else:
            print("    Notebook not found (requires --apply to create)")

    # Get current sources if notebook exists
    current_sources = []
    if notebook_id:
        current_sources = get_notebook_sources(client, notebook_id)
        if verbose:
            print(f"    Current sources: {len(current_sources)}")

    # Compute sync plan
    plan = compute_sync_plan(
        discovery=report.discovery,
        hash_comparison=comparison,
        notebook_id=notebook_id,
        current_sources=current_sources,
        notebook_exists=notebook_id is not None,
    )

    if verbose:
        print(f"    Planned: {len(plan.adds)} adds, {len(plan.updates)} updates, {len(plan.deletes)} deletes")

    # Apply if requested
    sync_result = None
    if apply and plan.has_changes:
        if not notebook_id:
            # Need to create notebook first
            notebook_id, _ = ensure_notebook(client, repo_key, notebook_map, apply=True)
            plan.notebook_id = notebook_id

        if notebook_id:
            if verbose:
                print("  Phase 5: Applying sync...")
            sync_result = apply_sync_plan(client, plan, repo_path)

            if verbose:
                print(f"    Added: {sync_result.sources_added}")
                print(f"    Updated: {sync_result.sources_updated}")
                print(f"    Deleted: {sync_result.sources_deleted}")
                if sync_result.errors:
                    print(f"    Errors: {len(sync_result.errors)}")

            # Update notebook_map.yaml with new state
            if sync_result.success or sync_result.doc_states:
                _update_notebook_map(repo_key, notebook_id, sync_result, verbose)

    return report, comparison, plan, sync_result


def _update_notebook_map(
    repo_key: str,
    notebook_id: str,
    sync_result: SyncResult,
    verbose: bool = False,
) -> None:
    """Update notebook_map.yaml with sync results."""
    try:
        notebook_map = load_notebook_map()

        if "notebooks" not in notebook_map:
            notebook_map["notebooks"] = {}

        if repo_key not in notebook_map["notebooks"]:
            notebook_map["notebooks"][repo_key] = {}

        repo_data = notebook_map["notebooks"][repo_key]
        repo_data["notebook_id"] = notebook_id

        # Update docs with new state
        if "docs" not in repo_data:
            repo_data["docs"] = {}

        for path, state in sync_result.doc_states.items():
            repo_data["docs"][path] = state

        # Write back
        with open(DEFAULT_NOTEBOOK_MAP_PATH, "w") as f:
            yaml.dump(notebook_map, f, default_flow_style=False, sort_keys=False)

        if verbose:
            print(f"    Updated notebook_map.yaml with {len(sync_result.doc_states)} doc states")

    except Exception as e:
        if verbose:
            print(f"    Warning: Failed to update notebook_map.yaml: {e}")


def run_artifacts(
    repo_path: Path,
    notebook_id: str,
    hash_comparison: HashComparison,
    apply: bool = False,
    force: bool = False,
    artifacts: Optional[str] = None,
    verbose: bool = False,
) -> tuple[ArtifactPlan, Optional[ArtifactResult]]:
    """
    Compute and optionally apply artifact refresh.

    Args:
        repo_path: Absolute path to repository root
        notebook_id: NotebookLM notebook UUID
        hash_comparison: Result of hash comparison
        apply: If True, create artifacts
        force: Force regeneration regardless of threshold
        artifacts: Comma-separated artifact subset (None = Standard 7)
        verbose: If True, print progress messages

    Returns:
        Tuple of (ArtifactPlan, ArtifactResult or None)
    """
    repo_key = repo_path.name

    # Check for major version bump in META.yaml
    major_bump = _detect_major_version_bump(repo_path, hash_comparison, verbose)

    # Parse artifact subset
    artifact_types = parse_artifact_list(artifacts)

    if verbose:
        print("  Phase 6: Computing artifact plan...")
        print(f"    Force: {force}")
        print(f"    Major version bump: {major_bump}")
        print(f"    Artifacts: {[a.value for a in artifact_types]}")

    # Compute artifact plan
    plan = compute_artifact_plan(
        repo_key=repo_key,
        notebook_id=notebook_id,
        hash_comparison=hash_comparison,
        major_version_bump=major_bump,
        force=force,
        artifact_subset=artifact_types,
    )

    if verbose:
        print(f"    Triggered: {plan.triggered}")
        if plan.triggered:
            print(f"    Reason: {plan.trigger_reason}")
        print(f"    Create: {len(plan.creates)} artifacts")

    # Apply if requested
    artifact_result = None
    if apply and plan.has_work:
        if verbose:
            print("  Phase 7: Creating artifacts...")

        try:
            from ..server import get_client
            client = get_client()
            artifact_result = apply_artifact_plan(
                client=client,
                plan=plan,
                verbose=verbose,
            )

            if verbose:
                print(f"    Created: {artifact_result.artifacts_created}")
                print(f"    Failed: {artifact_result.artifacts_failed}")
                if artifact_result.errors:
                    for err in artifact_result.errors:
                        print(f"    Error: {err}")

        except Exception as e:
            if verbose:
                print(f"    Error: Failed to apply artifacts: {e}")
            artifact_result = ArtifactResult(
                success=False,
                errors=[str(e)],
            )

    return plan, artifact_result


def _detect_major_version_bump(
    repo_path: Path,
    hash_comparison: HashComparison,
    verbose: bool = False,
) -> bool:
    """
    Detect if META.yaml has a major version bump.

    Compares stored vs current version in META.yaml.
    """
    # Find META.yaml in changed docs
    meta_changed = any(
        str(doc.path) == "META.yaml" for doc in hash_comparison.changed_docs
    )

    if not meta_changed:
        return False

    # Read current META.yaml
    meta_path = repo_path / "META.yaml"
    if not meta_path.exists():
        return False

    try:
        with open(meta_path, "r") as f:
            meta = yaml.safe_load(f)

        current_version = meta.get("version")
        # For now, we don't have stored version easily accessible
        # This would need to be enhanced to compare against stored version
        # For Round 3, we'll consider any META.yaml change with version field
        # as potentially major - the is_major_version_bump function compares two versions

        if verbose and current_version:
            print(f"    META.yaml version: {current_version}")

        # Since we don't have the old version stored easily, return False
        # A more complete implementation would read the old content hash
        # and compare versions
        return False

    except Exception:
        return False


def main(args: Optional[list[str]] = None) -> int:
    """
    CLI entrypoint for doc-refresh validation and sync.

    Args:
        args: Command line arguments (uses sys.argv if None)

    Returns:
        Exit code (0 for success, 1 for validation issues, 2 for error)
    """
    parser = argparse.ArgumentParser(
        prog="doc-refresh",
        description="Validate canonical documentation and sync to NotebookLM",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=None,
        help="Path to repository (default: current directory)",
    )
    parser.add_argument(
        "repo_path",
        type=Path,
        nargs="?",
        default=None,
        help="Path to repository (positional, alternative to --target)",
    )

    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--validate-only",
        action="store_true",
        help="Only run validation (no sync)",
    )
    mode_group.add_argument(
        "--sync-only",
        action="store_true",
        help="Skip validation, only sync to NotebookLM",
    )
    mode_group.add_argument(
        "--full",
        action="store_true",
        help="Run full validation and sync",
    )

    # Apply vs dry-run
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

    # Artifact options
    parser.add_argument(
        "--artifacts",
        type=str,
        default=None,
        help="Comma-separated artifact subset (e.g., 'audio,mind_map,briefing'). Default: Standard 7",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force artifact regeneration regardless of change threshold",
    )
    parser.add_argument(
        "--skip-artifacts",
        action="store_true",
        help="Skip artifact refresh phase entirely",
    )

    # Output options
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

    # Resolve repo path (--target takes precedence)
    repo_path = parsed.target or parsed.repo_path or Path.cwd()
    repo_path = repo_path.resolve()

    if not repo_path.exists():
        print(f"Error: Repository path does not exist: {repo_path}", file=sys.stderr)
        return 2

    if not repo_path.is_dir():
        print(f"Error: Not a directory: {repo_path}", file=sys.stderr)
        return 2

    apply = parsed.apply
    dry_run = not apply

    # Determine mode
    do_validate = not parsed.sync_only
    do_sync = parsed.sync_only or parsed.full

    # Gate sync operations
    if do_sync and dry_run:
        # Dry-run sync: show plan only
        pass
    elif do_sync and not apply:
        # This shouldn't happen due to logic above, but be safe
        pass

    try:
        if do_sync:
            # Run sync (includes validation unless --sync-only)
            report, comparison, plan, sync_result = run_sync(
                repo_path=repo_path,
                apply=apply,
                verbose=parsed.verbose,
            )

            # Output results
            if parsed.discovery_only:
                print(format_discovery_report(report.discovery))
            elif parsed.compact:
                print(format_compact_report(report))
            else:
                if do_validate:
                    print(format_validation_report(report))
                    print()
                print(format_sync_plan(plan))

                if sync_result:
                    print()
                    print(format_sync_result(sync_result))

            # Artifact refresh phase (after sync, if notebook exists)
            artifact_plan = None
            artifact_result = None

            if not parsed.skip_artifacts and plan.notebook_id:
                artifact_plan, artifact_result = run_artifacts(
                    repo_path=repo_path,
                    notebook_id=plan.notebook_id,
                    hash_comparison=comparison,
                    apply=apply,
                    force=parsed.force,
                    artifacts=parsed.artifacts,
                    verbose=parsed.verbose,
                )

                if not parsed.compact and not parsed.discovery_only:
                    print()
                    print(format_artifact_plan(artifact_plan))
                    if artifact_result:
                        print()
                        print(format_artifact_result(artifact_result))

            # Return code
            if artifact_result and not artifact_result.success:
                return 1
            if sync_result and not sync_result.success:
                return 1
            elif not report.is_valid:
                return 1
            return 0

        else:
            # Validation only
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
