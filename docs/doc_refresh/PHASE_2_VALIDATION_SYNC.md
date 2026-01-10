# Phase 2: Validation & Sync

**Version:** 0.1.0
**Last Updated:** 2026-01-10
**Status:** ⏳ Pending

## Objective

Implement document validation logic, hash-based change detection, and NotebookLM source synchronization.

## Deliverables

| Deliverable | Status | Description |
|-------------|--------|-------------|
| Validation logic | ⏳ | Check metadata headers, code refs, claims |
| Hash tracking | ⏳ | Compute and store content hashes |
| NotebookLM sync | ⏳ | Delete stale sources, re-add changed docs |
| Test run on C017 | ⏳ | Full validation + sync cycle |

## Implementation Plan

### 2.1 Validation Logic

For each discovered doc:
1. Parse for metadata header (YAML frontmatter or Version/Last Updated)
2. Extract `file:line` references and verify files exist
3. Flag discrepancies for human review

**Output:** Validation report with issues list and change delta.

### 2.2 Hash Tracking

1. Compute SHA256 hash of each doc's content
2. Truncate to 12 characters for readability
3. Compare against stored hashes in `notebook_map.yaml`
4. Calculate content delta percentage

### 2.3 NotebookLM Sync

1. Look up or create notebook via `notebook_list`/`notebook_create`
2. For each changed doc:
   - Find existing source by title
   - Delete stale: `source_delete(source_id, confirm=True)`
   - Add updated: `notebook_add_text(notebook_id, text, title)`
3. Update `notebook_map.yaml` with new hashes

## Acceptance Criteria

- [ ] `/doc-refresh --dry-run` shows validation issues
- [ ] `/doc-refresh --apply --docs-only` updates metadata headers
- [ ] `/doc-refresh --apply --sync-only` syncs to NotebookLM
- [ ] `notebook_map.yaml` reflects current doc hashes after sync
- [ ] Changed docs correctly identified via hash comparison

## Dependencies

- Phase 1 complete ✅
- NotebookLM MCP tools available
- Auth tokens valid

## Notes

- Use `--dry-run` extensively during development
- Test on C017 first (gold standard)
- Handle auth rotation gracefully
