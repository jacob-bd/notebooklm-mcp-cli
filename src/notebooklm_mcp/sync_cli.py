#!/usr/bin/env python3
"""
notebooklm-sync: Deterministic CLI for syncing docs to NotebookLM.

Usage:
    notebooklm-sync "My Notebook" file1.md file2.md
    notebooklm-sync "My Notebook" docs/*.md --audio
    notebooklm-sync --repo C012_round-table --tier3 --audio
    notebooklm-sync --list
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .auth import load_cached_tokens
from .api_client import NotebookLMClient
from .doc_refresh.manifest import (
    MAX_ORPHAN_FAILURES,
    add_orphan_source,
    ensure_notebook_map_defaults,
    get_orphan_ledger,
    load_notebook_map as load_notebook_map_manifest,
    record_orphan_failure,
    remove_orphan_source,
    save_notebook_map as save_notebook_map_manifest,
)
from .doc_refresh.notebook_sync import (
    DELETE_RETRY_ATTEMPTS,
    delete_source_with_retry,
)
from .doc_refresh.runner import run_artifacts, run_sync, run_validation

# Paths - use central config directory for consistent access regardless of install method
CONFIG_DIR = Path.home() / ".config" / "notebooklm-mcp"
NOTEBOOK_MAP_PATH = CONFIG_DIR / "notebook_map.yaml"
RECEIPTS_DIR = CONFIG_DIR / "sync_receipts"
WORKSPACE_ROOT = Path.home() / "SyncedProjects"
REFRESH_LOG_PATH = CONFIG_DIR / "refresh.log"
MAX_REFRESH_LOG_BYTES = 5 * 1024 * 1024


def try_get_client() -> Optional[NotebookLMClient]:
    """Return authenticated NotebookLM client if cached auth is available."""
    tokens = load_cached_tokens()
    if not tokens:
        return None

    return NotebookLMClient(
        cookies=tokens.cookies,
        csrf_token=tokens.csrf_token,
        session_id=tokens.session_id,
    )


def get_client() -> NotebookLMClient:
    """Get authenticated NotebookLM client or exit with a helpful message."""
    client = try_get_client()
    if client is None:
        print("Error: No cached auth tokens found.", file=sys.stderr)
        print("Run 'notebooklm-mcp-auth' first to authenticate.", file=sys.stderr)
        sys.exit(1)
    return client


def load_notebook_map() -> dict:
    """Load the notebook map YAML."""
    return load_notebook_map_manifest(NOTEBOOK_MAP_PATH)


def save_notebook_map(data: dict) -> None:
    """Save the notebook map YAML."""
    save_notebook_map_manifest(data, NOTEBOOK_MAP_PATH)


def compute_file_hash(file_path: Path, length: int = 12) -> str:
    """Compute SHA256 hash of file content."""
    content = file_path.read_bytes()
    return hashlib.sha256(content).hexdigest()[:length]


def list_notebooks() -> None:
    """List all existing notebooks."""
    client = get_client()
    notebooks = client.list_notebooks()

    if not notebooks:
        print("No notebooks found.")
        return

    print(f"Found {len(notebooks)} notebook(s):\n")
    for nb in notebooks:
        print(f"  [{nb.id[:8]}...] {nb.title} ({nb.source_count} sources)")


def find_notebook_by_id(client: NotebookLMClient, notebook_id: str):
    """Find existing notebook by ID."""
    notebooks = client.list_notebooks()
    for nb in notebooks:
        if nb.id == notebook_id:
            return nb
    return None


def find_notebook_by_name(client: NotebookLMClient, name: str):
    """Find existing notebook by exact name match."""
    notebooks = client.list_notebooks()
    for nb in notebooks:
        if nb.title == name:
            return nb
    return None


def discover_tier3_docs(repo_path: Path) -> list[Path]:
    """Auto-discover Tier 3 documentation files in a repo.

    Tier 3 docs include:
    - README.md, CLAUDE.md, PROJECT_PRIMER.md (root)
    - docs/*.md (Tier 3 docs folder)
    - 10_docs/*.md and 10_docs/**/*.md (Betty Protocol docs)
    """
    docs = []

    # Root-level docs
    for name in ["README.md", "CLAUDE.md", "PROJECT_PRIMER.md", "RELATIONS.yaml"]:
        path = repo_path / name
        if path.exists():
            docs.append(path)

    # docs/ folder (standard Tier 3)
    docs_folder = repo_path / "docs"
    if docs_folder.exists():
        docs.extend(sorted(docs_folder.glob("*.md")))
        # Also check subdirectories
        for subdir in docs_folder.iterdir():
            if subdir.is_dir():
                docs.extend(sorted(subdir.glob("*.md")))

    # 10_docs/ folder (Betty Protocol)
    betty_docs = repo_path / "10_docs"
    if betty_docs.exists():
        docs.extend(sorted(betty_docs.glob("*.md")))
        # Also check subdirectories
        for subdir in betty_docs.iterdir():
            if subdir.is_dir():
                docs.extend(sorted(subdir.glob("*.md")))

    return docs


def write_receipt(
    repo_id: str | None,
    notebook_name: str,
    notebook_id: str,
    files_synced: list[dict],
    audio_requested: bool,
    audio_focus: str,
) -> Path:
    """Write a JSON receipt for this sync run."""
    RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    receipt_name = f"{timestamp}_{repo_id or 'manual'}_sync.json"
    receipt_path = RECEIPTS_DIR / receipt_name

    receipt = {
        "timestamp": timestamp,
        "repo_id": repo_id,
        "notebook_name": notebook_name,
        "notebook_id": notebook_id,
        "notebook_url": f"https://notebooklm.google.com/notebook/{notebook_id}",
        "files_synced": files_synced,
        "summary": {
            "total": len(files_synced),
            "added": sum(1 for f in files_synced if f["action"] == "added"),
            "replaced": sum(1 for f in files_synced if f["action"] == "replaced"),
            "skipped": sum(1 for f in files_synced if f["action"] == "skipped"),
            "failed": sum(1 for f in files_synced if f["action"] == "failed"),
        },
        "audio_overview": {
            "requested": audio_requested,
            "focus": audio_focus if audio_requested else None,
        },
    }

    receipt_path.write_text(json.dumps(receipt, indent=2))
    return receipt_path


def write_batch_receipt(
    summary: dict[str, Any],
) -> Path:
    """Write a JSON receipt for a batch refresh run."""
    RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    receipt_name = f"{timestamp}_batch_refresh.json"
    receipt_path = RECEIPTS_DIR / receipt_name

    payload = {
        "timestamp": timestamp,
        "mode": "batch_refresh",
        **summary,
    }
    receipt_path.write_text(json.dumps(payload, indent=2))
    return receipt_path


def append_refresh_log(lines: list[str]) -> None:
    """Append run output lines to refresh.log."""
    if not lines:
        return

    REFRESH_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if REFRESH_LOG_PATH.exists() and REFRESH_LOG_PATH.stat().st_size > MAX_REFRESH_LOG_BYTES:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archived = REFRESH_LOG_PATH.with_name(f"refresh.log.{stamp}.bak")
        REFRESH_LOG_PATH.rename(archived)

    with REFRESH_LOG_PATH.open("a", encoding="utf-8") as f:
        for line in lines:
            f.write(f"{line}\n")


def _batch_log(lines: list[str], message: str, echo: bool = True) -> None:
    """Record a batch log line and optionally echo to stdout."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    line = f"[{timestamp}] {message}"
    lines.append(line)
    if echo:
        print(message)


def _sweep_orphans_for_repo(
    client: NotebookLMClient,
    notebook_map: dict[str, Any],
    repo_id: str,
) -> dict[str, int]:
    """Sweep orphaned sources for one repo and persist counters in notebook_map."""
    stats = {
        "attempted": 0,
        "cleaned": 0,
        "failed": 0,
        "skipped": 0,
    }
    ledger = get_orphan_ledger(notebook_map, repo_id, create=False)
    if not ledger:
        return stats

    for source_id, info in list(ledger.items()):
        if not source_id:
            continue

        if isinstance(info, dict) and info.get("disabled"):
            stats["skipped"] += 1
            continue

        stats["attempted"] += 1
        try:
            deleted = client.delete_source(source_id)
            if deleted:
                remove_orphan_source(notebook_map, repo_id, source_id)
                stats["cleaned"] += 1
            else:
                record_orphan_failure(
                    notebook_map,
                    repo_id,
                    source_id,
                    error="delete_source returned False",
                    max_failures=MAX_ORPHAN_FAILURES,
                )
                stats["failed"] += 1
        except Exception as e:
            record_orphan_failure(
                notebook_map,
                repo_id,
                source_id,
                error=str(e),
                max_failures=MAX_ORPHAN_FAILURES,
            )
            stats["failed"] += 1

    return stats


def prompt_for_artifacts(notebook_name: str, changes_made: int) -> bool:
    """Prompt user before generating artifacts."""
    if changes_made == 0:
        print("\nNo changes were made to the notebook.")
        response = input("Generate audio overview anyway? [y/N]: ").strip().lower()
    else:
        print(f"\n{changes_made} document(s) were updated in the notebook.")
        response = input("Generate audio overview with updated sources? [y/N]: ").strip().lower()

    return response in ("y", "yes")


def sync_files(
    notebook_name: str,
    files: list[Path],
    repo_id: str | None = None,
    create_audio: bool = False,
    audio_focus: str = "",
    interactive: bool = True,
) -> None:
    """Sync files to a NotebookLM notebook with idempotence and replacement."""
    client = get_client()
    notebook_map = load_notebook_map()
    notebook_map = ensure_notebook_map_defaults(notebook_map)

    if repo_id:
        sweep_stats = _sweep_orphans_for_repo(client, notebook_map, repo_id)
        if sweep_stats["attempted"] > 0:
            print(
                "Orphan sweep: "
                f"{sweep_stats['cleaned']} cleaned, "
                f"{sweep_stats['failed']} failed, "
                f"{sweep_stats['skipped']} skipped"
            )

    # Check if notebook exists in map for this repo
    existing_entry = notebook_map.get("notebooks", {}).get(repo_id) if repo_id else None
    mapped_notebook_id = existing_entry.get("notebook_id") if existing_entry else None

    # Priority: 1) Use mapped notebook_id, 2) Search by name, 3) Create new
    notebook = None

    if mapped_notebook_id:
        # Try to find the notebook we used before (by ID, regardless of current name)
        notebook = find_notebook_by_id(client, mapped_notebook_id)
        if notebook:
            print(f"Found mapped notebook: {notebook.title} ({notebook.source_count} sources)")
            if notebook.title != notebook_name:
                print(f"  Note: Notebook name differs from repo name (using existing)")

    if not notebook:
        # Fall back to searching by exact name
        notebook = find_notebook_by_name(client, notebook_name)
        if notebook:
            print(f"Found notebook by name: {notebook_name} ({notebook.source_count} sources)")

    if not notebook:
        # Create new notebook
        print(f"Creating new notebook: {notebook_name}")
        notebook = client.create_notebook(notebook_name)
        if not notebook:
            print("Error: Failed to create notebook.", file=sys.stderr)
            sys.exit(1)
        print(f"Created notebook: {notebook.id}")

    # Only use existing doc hashes for idempotence if we're using the SAME notebook
    # This prevents accidentally deleting sources from a different notebook
    existing_docs = {}
    same_notebook = mapped_notebook_id == notebook.id
    if existing_entry and same_notebook:
        existing_docs = existing_entry.get("docs", {})
        print(f"Using existing doc hashes from notebook_map (same notebook)")
    elif existing_entry and not same_notebook:
        print(f"Note: notebook_map has different notebook_id - starting fresh (no replacements)")

    # Process each file
    files_synced = []
    source_ids = []
    changes_made = 0
    new_orphans: list[str] = []

    for file_path in files:
        if not file_path.exists():
            files_synced.append({
                "path": str(file_path),
                "action": "skipped",
                "reason": "not_found",
            })
            print(f"  Skipping (not found): {file_path}")
            continue

        content = file_path.read_text(encoding="utf-8")
        current_hash = compute_file_hash(file_path)

        # Determine relative path for storage
        if repo_id:
            try:
                rel_path = str(file_path.relative_to(WORKSPACE_ROOT / repo_id))
            except ValueError:
                rel_path = file_path.name
        else:
            rel_path = file_path.name

        # Check if file is unchanged (idempotence)
        existing_doc = existing_docs.get(rel_path, {})
        old_source_id = existing_doc.get("source_id")

        if existing_doc.get("hash") == current_hash:
            files_synced.append({
                "path": rel_path,
                "hash": current_hash,
                "action": "skipped",
                "reason": "unchanged",
                "source_id": old_source_id,
            })
            if old_source_id:
                source_ids.append(old_source_id)
            print(f"  Skipping (unchanged): {rel_path}")
            continue

        # File is new or changed.
        # For replacements, add first then delete old source to prevent data loss.
        if old_source_id:
            print(f"  Replacing: {rel_path} ({len(content):,} chars)...", end=" ")
        else:
            print(f"  Adding: {rel_path} ({len(content):,} chars)...", end=" ")

        result = client.add_text_source(notebook.id, content, title=file_path.name)

        if not result:
            files_synced.append({
                "path": rel_path,
                "hash": current_hash,
                "action": "failed",
                "reason": "add_failed",
            })
            print("FAILED")
            continue

        new_source_id = result["id"]
        source_ids.append(new_source_id)
        changes_made += 1

        if old_source_id:
            deleted, attempts, _ = delete_source_with_retry(
                client=client,
                source_id=old_source_id,
                max_attempts=DELETE_RETRY_ATTEMPTS,
            )
            if deleted:
                files_synced.append({
                    "path": rel_path,
                    "hash": current_hash,
                    "action": "replaced",
                    "source_id": new_source_id,
                    "old_source_id": old_source_id,
                    "delete_attempts": attempts,
                })
                print("OK")
            else:
                # Keep the newly-added source and record warning; we'll retry cleanup later.
                files_synced.append({
                    "path": rel_path,
                    "hash": current_hash,
                    "action": "added",
                    "reason": "old_source_delete_failed",
                    "source_id": new_source_id,
                    "old_source_id": old_source_id,
                    "delete_attempts": attempts,
                })
                new_orphans.append(old_source_id)
                if repo_id:
                    add_orphan_source(
                        notebook_map,
                        repo_id,
                        old_source_id,
                        error="Delete failed after replacement retry",
                    )
                print("ADDED (old source cleanup failed)")
        else:
            files_synced.append({
                "path": rel_path,
                "hash": current_hash,
                "action": "added",
                "source_id": new_source_id,
                "old_source_id": None,
            })
            print("OK")

    # Summary
    added = sum(1 for f in files_synced if f["action"] == "added")
    replaced = sum(1 for f in files_synced if f["action"] == "replaced")
    skipped = sum(1 for f in files_synced if f["action"] == "skipped")
    failed = sum(1 for f in files_synced if f["action"] == "failed")

    print(f"\nSync complete: {added} added, {replaced} replaced, {skipped} skipped, {failed} failed")
    if new_orphans:
        print(f"Tracked {len(new_orphans)} orphaned source(s) for next-run cleanup")

    # Update notebook map
    if repo_id:
        if "notebooks" not in notebook_map:
            notebook_map["notebooks"] = {}

        if repo_id not in notebook_map["notebooks"]:
            notebook_map["notebooks"][repo_id] = {}

        entry = notebook_map["notebooks"][repo_id]
        entry["notebook_id"] = notebook.id
        entry["notebook_url"] = f"https://notebooklm.google.com/notebook/{notebook.id}"
        entry["last_sync"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        if "docs" not in entry:
            entry["docs"] = {}

        # Update doc entries
        for f in files_synced:
            if f["action"] in ("added", "replaced", "skipped") and f.get("source_id"):
                entry["docs"][f["path"]] = {
                    "hash": f.get("hash"),
                    "source_id": f["source_id"],
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }

        save_notebook_map(notebook_map)
        print("Updated notebook_map.yaml")

    # Handle audio overview with prompt
    should_generate_audio = False
    if create_audio and source_ids:
        if interactive:
            should_generate_audio = prompt_for_artifacts(notebook_name, changes_made)
        else:
            should_generate_audio = True  # Non-interactive mode: just do it

    if should_generate_audio:
        print("\nGenerating Audio Overview (this may take several minutes)...")
        audio_result = client.create_audio_overview(
            notebook.id,
            source_ids,
            format_code=1,  # Deep dive
            length_code=2,  # Default length
            focus_prompt=audio_focus,
        )

        if audio_result:
            print("Audio Overview generation started!")
        else:
            print("Failed to start Audio Overview generation.", file=sys.stderr)

    # Write receipt
    receipt_path = write_receipt(
        repo_id=repo_id,
        notebook_name=notebook_name,
        notebook_id=notebook.id,
        files_synced=files_synced,
        audio_requested=should_generate_audio,
        audio_focus=audio_focus,
    )
    print(f"Receipt: {receipt_path}")

    print(f"\nNotebook URL: https://notebooklm.google.com/notebook/{notebook.id}")


def run_batch_refresh(
    apply: bool,
    changed_only: bool,
    tier_filter: Optional[str],
    force_artifacts: bool,
    artifacts: Optional[str],
    skip_artifacts: bool,
    repos_csv: Optional[str],
    verbose: bool,
) -> int:
    """Run sequential cross-repo refresh using notebook_map repo mappings."""
    notebook_map = ensure_notebook_map_defaults(load_notebook_map())
    notebooks = notebook_map.get("notebooks", {})
    mapped_repos = sorted(notebooks.keys())
    log_lines: list[str] = []

    selected_repos = mapped_repos
    if repos_csv:
        requested = [r.strip() for r in repos_csv.split(",") if r.strip()]
        selected_repos = [r for r in requested if r in notebooks]
        missing = [r for r in requested if r not in notebooks]
        for repo in missing:
            _batch_log(log_lines, f"Repo {repo} is not mapped in notebook_map.yaml", echo=True)

    if not selected_repos:
        _batch_log(log_lines, "No mapped repositories found for batch refresh.", echo=True)
        append_refresh_log(log_lines)
        return 1

    client = try_get_client()
    if client is None:
        _batch_log(
            log_lines,
            "Auth unavailable: no cached tokens. Skipping batch refresh (run notebooklm-mcp-auth).",
            echo=True,
        )
        receipt_path = write_batch_receipt(
            {
                "status": "auth_unavailable",
                "apply": apply,
                "changed_only": changed_only,
                "tier_filter": tier_filter,
                "force_artifacts": force_artifacts,
                "repos": [],
            }
        )
        _batch_log(log_lines, f"Receipt: {receipt_path}", echo=True)
        append_refresh_log(log_lines)
        return 0

    try:
        client.list_notebooks()
    except Exception as e:
        _batch_log(
            log_lines,
            f"Auth check failed ({e}). Skipping batch refresh so future scheduled runs can continue.",
            echo=True,
        )
        receipt_path = write_batch_receipt(
            {
                "status": "auth_failed",
                "apply": apply,
                "changed_only": changed_only,
                "tier_filter": tier_filter,
                "force_artifacts": force_artifacts,
                "error": str(e),
                "repos": [],
            }
        )
        _batch_log(log_lines, f"Receipt: {receipt_path}", echo=True)
        append_refresh_log(log_lines)
        return 0

    workspace_root = Path(str(notebook_map.get("workspace_root", WORKSPACE_ROOT))).expanduser()
    results: list[dict[str, Any]] = []

    for repo_id in selected_repos:
        repo_path = (workspace_root / repo_id).resolve()
        _batch_log(log_lines, f"Processing {repo_id}", echo=True)

        if not repo_path.exists():
            message = f"Repository path not found: {repo_path}"
            _batch_log(log_lines, message, echo=True)
            results.append(
                {
                    "repo": repo_id,
                    "status": "failed",
                    "reason": "repo_path_missing",
                    "error": message,
                }
            )
            continue

        precomputed: Optional[tuple[Any, Any]] = None
        try:
            validation_report, hash_comparison = run_validation(
                repo_path=repo_path,
                dry_run=True,
                verbose=verbose,
            )
            precomputed = (validation_report, hash_comparison)

            if tier_filter and validation_report.discovery.tier.value != tier_filter:
                results.append(
                    {
                        "repo": repo_id,
                        "status": "skipped",
                        "reason": "tier_mismatch",
                        "tier": validation_report.discovery.tier.value,
                    }
                )
                _batch_log(
                    log_lines,
                    f"Skipped {repo_id}: tier {validation_report.discovery.tier.value} "
                    f"does not match filter {tier_filter}",
                    echo=True,
                )
                continue

            changed_docs = len(hash_comparison.changed_docs) + len(hash_comparison.new_docs)
            if changed_only and changed_docs == 0:
                results.append(
                    {
                        "repo": repo_id,
                        "status": "skipped",
                        "reason": "no_content_changes",
                    }
                )
                _batch_log(log_lines, f"Skipped {repo_id}: no content changes detected", echo=True)
                continue

            report, comparison, plan, sync_result = run_sync(
                repo_path=repo_path,
                apply=apply,
                verbose=verbose,
                precomputed=precomputed,
                client=client,
            )

            repo_artifacts = artifacts
            if repo_artifacts is None:
                repo_config = notebooks.get(repo_id, {})
                configured = repo_config.get("artifact_types")
                if isinstance(configured, list) and configured:
                    repo_artifacts = ",".join(str(a) for a in configured)

            artifact_plan = None
            artifact_result = None
            if not skip_artifacts and plan.notebook_id:
                artifact_plan, artifact_result = run_artifacts(
                    repo_path=repo_path,
                    notebook_id=plan.notebook_id,
                    hash_comparison=comparison,
                    apply=apply,
                    force=force_artifacts,
                    artifacts=repo_artifacts,
                    verbose=verbose,
                    client=client,
                )

            repo_failed = False
            if sync_result and not sync_result.success:
                repo_failed = True
            if artifact_result and not artifact_result.success:
                repo_failed = True
            if not report.is_valid:
                repo_failed = True

            repo_status = "failed" if repo_failed else "success"
            added_count = sync_result.sources_added if sync_result else len(plan.adds)
            updated_count = sync_result.sources_updated if sync_result else len(plan.updates)
            deleted_count = sync_result.sources_deleted if sync_result else len(plan.deletes)
            repo_summary = {
                "repo": repo_id,
                "status": repo_status,
                "tier": report.discovery.tier.value,
                "added": added_count,
                "updated": updated_count,
                "deleted": deleted_count,
                "orphans_cleaned": sync_result.orphans_cleaned if sync_result else 0,
                "orphans_tracked": len(sync_result.orphaned_source_ids) if sync_result else 0,
                "errors": (
                    (sync_result.errors if sync_result else [])
                    + (artifact_result.errors if artifact_result else [])
                ),
                "artifacts_triggered": artifact_plan.triggered if artifact_plan else False,
                "artifacts_created": artifact_result.artifacts_created if artifact_result else 0,
                "artifacts_failed": artifact_result.artifacts_failed if artifact_result else 0,
            }
            results.append(repo_summary)

            _batch_log(
                log_lines,
                f"{repo_id}: {repo_status} "
                f"(+{repo_summary['added']} ~{repo_summary['updated']} -{repo_summary['deleted']}, "
                f"orphans cleaned {repo_summary['orphans_cleaned']}, "
                f"artifacts {repo_summary['artifacts_created']})",
                echo=True,
            )

        except Exception as e:
            results.append(
                {
                    "repo": repo_id,
                    "status": "failed",
                    "reason": "exception",
                    "error": str(e),
                }
            )
            _batch_log(log_lines, f"{repo_id}: failed with exception: {e}", echo=True)
            continue

    summary = {
        "status": "completed",
        "apply": apply,
        "changed_only": changed_only,
        "tier_filter": tier_filter,
        "force_artifacts": force_artifacts,
        "repos_total": len(selected_repos),
        "repos_succeeded": sum(1 for r in results if r.get("status") == "success"),
        "repos_failed": sum(1 for r in results if r.get("status") == "failed"),
        "repos_skipped": sum(1 for r in results if r.get("status") == "skipped"),
        "repos": results,
    }
    receipt_path = write_batch_receipt(summary)
    _batch_log(log_lines, f"Batch summary: {summary['repos_succeeded']} succeeded, "
                         f"{summary['repos_failed']} failed, {summary['repos_skipped']} skipped", echo=True)
    _batch_log(log_lines, f"Receipt: {receipt_path}", echo=True)
    append_refresh_log(log_lines)

    return 1 if summary["repos_failed"] > 0 else 0


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="notebooklm-sync",
        description="Sync documentation files to NotebookLM (single repo or batch mode)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # List existing notebooks
    notebooklm-sync --list

    # Sync specific files to a notebook
    notebooklm-sync "C012_round-table" docs/*.md

    # Sync with audio overview (will prompt before generating)
    notebooklm-sync "C012_round-table" docs/*.md --audio

    # Auto-sync Tier 3 docs from a repo (notebook name = repo name)
    notebooklm-sync --repo C012_round-table --tier3

    # Full auto-sync with audio prompt
    notebooklm-sync --repo C012_round-table --tier3 --audio --focus "Explain the architecture"

    # Non-interactive mode (no prompts)
    notebooklm-sync --repo C012_round-table --tier3 --audio --yes

    # Batch refresh all mapped repos
    notebooklm-sync --all --apply

    # Batch refresh only changed kitted repos
    notebooklm-sync --all --apply --changed-only --tier kitted
        """,
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List existing notebooks and exit",
    )
    parser.add_argument(
        "--repo",
        metavar="REPO_ID",
        help="Repository ID (e.g., C012_round-table). Notebook name will match repo name exactly.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Batch refresh all mapped repos from notebook_map.yaml",
    )
    parser.add_argument(
        "--repos",
        metavar="REPO_LIST",
        help="Comma-separated subset of mapped repos for --all mode",
    )
    parser.add_argument(
        "--changed-only",
        action="store_true",
        help="With --all: skip repos with no content hash changes",
    )
    parser.add_argument(
        "--tier",
        choices=["simple", "complex", "kitted"],
        help="With --all: only process repos matching this tier",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="With --all: apply changes (otherwise dry-run planning only)",
    )
    parser.add_argument(
        "--force-artifacts",
        action="store_true",
        help="With --all: force artifact regeneration even below threshold",
    )
    parser.add_argument(
        "--artifacts",
        default=None,
        help="Artifact subset for --all (comma-separated). Default uses standard artifact set.",
    )
    parser.add_argument(
        "--skip-artifacts",
        action="store_true",
        help="With --all: skip artifact regeneration phase",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "--tier3",
        action="store_true",
        help="Auto-discover Tier 3 docs (README, CLAUDE, docs/*.md, 10_docs/**/*.md)",
    )
    parser.add_argument(
        "notebook_name",
        nargs="?",
        help="Name of the notebook (creates if doesn't exist). Ignored if --repo is used.",
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="Files to add as sources (supports glob patterns)",
    )
    parser.add_argument(
        "--audio",
        action="store_true",
        help="Generate Audio Overview after syncing (will prompt for confirmation)",
    )
    parser.add_argument(
        "--focus",
        default="",
        help="Focus prompt for Audio Overview (e.g., 'Explain the architecture')",
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Non-interactive mode: skip prompts and proceed with audio generation",
    )

    args = parser.parse_args()

    if args.list:
        list_notebooks()
        return 0

    if args.all:
        if args.repo:
            print("Error: --repo cannot be combined with --all. Use --repos for batch subsets.", file=sys.stderr)
            return 1
        return run_batch_refresh(
            apply=args.apply,
            changed_only=args.changed_only,
            tier_filter=args.tier,
            force_artifacts=args.force_artifacts,
            artifacts=args.artifacts,
            skip_artifacts=args.skip_artifacts,
            repos_csv=args.repos,
            verbose=args.verbose,
        )

    # Handle --repo mode
    repo_id = args.repo
    files = list(args.files) if args.files else []
    notebook_name = args.notebook_name

    if repo_id:
        repo_path = WORKSPACE_ROOT / repo_id
        if not repo_path.exists():
            print(f"Error: Repository not found at {repo_path}", file=sys.stderr)
            return 1

        # Notebook name MUST match repo name exactly
        notebook_name = repo_id

        # Auto-discover Tier 3 docs if requested
        if args.tier3:
            discovered = discover_tier3_docs(repo_path)
            print(f"Discovered {len(discovered)} Tier 3 docs in {repo_id}")
            files = discovered

    if not notebook_name:
        parser.print_help()
        return 1

    if not files:
        print("Error: No files specified. Use --tier3 with --repo or provide file paths.", file=sys.stderr)
        return 1

    # Expand glob patterns (shell may not expand them on all platforms)
    expanded_files = []
    for f in files:
        if "*" in str(f):
            expanded_files.extend(Path(".").glob(str(f)))
        else:
            expanded_files.append(f)

    if not expanded_files:
        print("Error: No files found matching patterns.", file=sys.stderr)
        return 1

    sync_files(
        notebook_name,
        expanded_files,
        repo_id=repo_id,
        create_audio=args.audio,
        audio_focus=args.focus,
        interactive=not args.yes,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
