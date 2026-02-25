# PRD-NR01: Nightly Notebook Refresh

**Status:** Draft
**Author:** Jeremy / Atlas
**Created:** 2026-02-25
**Repo:** C021_notebooklm-mcp

---

## Problem

NotebookLM notebooks for core repos go stale within days of active
development. Refreshing them today requires manual CLI runs, and even then
the sync leaves orphaned duplicate sources when the delete-after-add fails
(~30% of replace attempts based on observed logs). Jeremy must then manually
identify and remove old versions in the NotebookLM UI — a tedious process
since sources have no visible timestamps.

Generated artifacts (audio overviews, briefing docs, etc.) also become stale
but aren't regenerated unless explicitly requested.

## Goal

A fully automated nightly service that keeps all mapped NotebookLM notebooks
current with their repo docs and regenerates artifacts when content changes
meaningfully — with zero manual intervention under normal operation.

## Requirements

### R1: Reliable Source Replace (P0)

The replace operation must be atomic from the user's perspective:

- After a replace, exactly ONE version of each doc exists in the notebook
- If add-then-delete fails, retry the delete (up to 3 attempts with backoff)
- If delete still fails, record the orphaned source_id for cleanup on next run
- Maintain an **orphan ledger** in `notebook_map.yaml` so orphans are tracked
  across runs and cleaned up on the next successful auth window

### R2: Orphaned Source Cleanup (P0)

Each run should begin with an orphan sweep:

1. Load orphan ledger from `notebook_map.yaml`
2. Attempt to delete each orphaned source_id
3. On success, remove from ledger
4. On failure, increment retry counter; after 5 failures, log warning and skip

This ensures that transient auth failures don't permanently orphan sources.

### R3: Cross-Repo Batch Runner (P1)

A single command that iterates all repos in `notebook_map.yaml` (or a
configurable subset):

```bash
# Refresh all mapped repos
notebooklm-sync --all --apply

# Refresh only repos with changes (hash comparison)
notebooklm-sync --all --apply --changed-only

# Refresh specific tier
notebooklm-sync --all --apply --tier kitted
```

The batch runner should:
- Process repos sequentially (to stay within free-tier rate limits)
- Skip repos with no content changes (hash-based)
- Produce a summary report at the end
- Continue past individual repo failures (don't abort the batch)

### R4: Conditional Artifact Regeneration (P1)

After syncing docs, evaluate whether artifacts need regeneration:

- **Trigger**: Content delta > 15% of total notebook content, OR major
  version bump in META.yaml, OR `--force-artifacts` flag
- **Standard artifacts**: Audio Overview (deep-dive), Briefing Doc, Study Guide
- **Optional artifacts**: Infographic, Flashcards, Quiz (configurable per repo)
- **Artifact cleanup**: Delete the previous version of each artifact before
  generating the new one (prevent accumulation)

Note: The doc_refresh subsystem already implements this logic. Wire it into
the batch runner.

### R5: Scheduled Execution (P2)

Run the batch refresh on a schedule without manual intervention:

- **macOS**: `launchd` plist that runs nightly (e.g., 2:00 AM)
- **Trigger**: Timer-based, not file-watch-based (simpler, more predictable)
- **Auth handling**: Use cached cookies; if auth fails, skip the run and log
  a notification (don't block future runs)
- **Logging**: Append to `~/.config/notebooklm-mcp/refresh.log`
- **Receipts**: Write a sync receipt per run to
  `~/.config/notebooklm-mcp/sync_receipts/`

### R6: Observability (P2)

After each batch run, produce:

- Per-repo summary: added / replaced / skipped / failed / orphans cleaned
- Artifact regeneration status: which repos triggered, which artifacts generated
- Overall health: repos with persistent orphans, auth failures, stale notebooks
- Optional: Push summary to a notification channel (Todoist task, file, etc.)

## Non-Requirements

- **Real-time sync** — Nightly cadence is sufficient. No file watchers.
- **Bidirectional sync** — NotebookLM is read-only from repo perspective.
  We never pull content back from notebooks into repos.
- **Multi-user** — Single-user (Jeremy's account) only.
- **Google Workspace support** — Free/personal tier only for now.

## Architecture

### Existing Infrastructure to Reuse

| Component | Location | Status |
|-----------|----------|--------|
| API client (reverse-engineered) | `api_client.py` | Production |
| Hash-based change detection | `doc_refresh/hashing.py` | Production |
| Tier discovery (1/2/3) | `doc_refresh/discover.py` | Production |
| Sync planning (add/update/delete) | `doc_refresh/notebook_sync.py` | Production |
| Artifact regeneration + polling | `doc_refresh/artifact_refresh.py` | Production |
| Notebook map persistence | `doc_refresh/manifest.py` | Production |
| Runner orchestrator | `doc_refresh/runner.py` | Production |

### New Components

| Component | Description |
|-----------|-------------|
| Orphan ledger | New section in `notebook_map.yaml` per-repo |
| Orphan sweep | Pre-sync phase in runner.py |
| Delete retry with backoff | Enhancement to `notebook_sync.py` |
| Batch runner | New CLI command or flag on `notebooklm-sync` |
| launchd plist | New file: `30_config/com.notebooklm-mcp.refresh.plist` |
| Refresh log | `~/.config/notebooklm-mcp/refresh.log` |

### Data Flow

```
[launchd timer, 2 AM nightly]
        │
        ▼
[notebooklm-sync --all --apply --changed-only]
        │
        ├── For each mapped repo:
        │     ├── Orphan sweep (clean up previous failures)
        │     ├── Tier 3 discovery
        │     ├── Hash comparison (skip if unchanged)
        │     ├── Sync plan (add / replace / delete)
        │     ├── Execute sync (with delete retry + orphan ledger)
        │     ├── Evaluate artifact triggers
        │     └── Regenerate artifacts if triggered
        │
        ▼
[Summary report → refresh.log + sync_receipt]
```

## Implementation Plan

### Phase A: Reliable Replace (P0) — ~2 sessions

1. Add orphan ledger schema to `notebook_map.yaml`
2. Implement delete retry with exponential backoff in `notebook_sync.py`
3. Implement orphan sweep phase in `runner.py`
4. Add orphan tracking to `sync_cli.py` (so both paths benefit)
5. Tests: simulate delete failures, verify orphan tracking and cleanup

### Phase B: Batch Runner (P1) — ~1 session

1. Add `--all` flag to `notebooklm-sync`
2. Add `--changed-only` filter (hash comparison without sync)
3. Sequential repo iteration with error isolation
4. Summary report output
5. Wire artifact regeneration into batch flow

### Phase C: Scheduled Execution (P2) — ~1 session

1. Create launchd plist with nightly timer
2. Add log rotation for `refresh.log`
3. Auth failure detection and graceful skip
4. Installation script (`make install-schedule` / `make uninstall-schedule`)

## Success Criteria

- [ ] `notebooklm-sync --all --apply` refreshes all mapped repos end-to-end
- [ ] Zero orphaned duplicate sources after 3 consecutive nightly runs
- [ ] Artifacts regenerated automatically when content delta exceeds threshold
- [ ] Nightly schedule runs unattended for 7 days without manual intervention
- [ ] Auth failures logged but don't block subsequent runs or repos

## Open Questions

1. **Free tier rate limits**: How many API calls can we make per nightly run
   before hitting limits? May need to space repos apart or run over multiple
   nights.
2. **Cookie longevity**: Can we extend cookie lifetime beyond ~1 week? If not,
   the scheduled job needs a "re-auth needed" notification mechanism.
3. **Artifact selection per repo**: Should all repos get the full Standard 7,
   or should some repos only get audio + briefing doc?
