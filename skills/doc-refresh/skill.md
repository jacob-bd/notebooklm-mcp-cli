---
description: "Refresh documentation and sync to NotebookLM"
argument-hint: "[--target PATH] [MODE] [OPTIONS]"
---

# Doc Refresh Command

This command initiates a Ralph loop to:
1. Validate and update canonical documentation in a repo
2. Sync updated docs to the repo's NotebookLM notebook
3. Conditionally regenerate NotebookLM artifacts

## Safety Posture

**Default mode is `--dry-run`** - no changes are made without explicit `--apply`.

| Mode | Effect |
|------|--------|
| `--dry-run` | **DEFAULT.** Validate and report only. No writes, no syncs, no commits. |
| `--apply` | Execute changes: update docs, sync to NotebookLM, regenerate artifacts. |

## Modes

| Mode Flag | Description |
|-----------|-------------|
| `--validate-only` | Run validation phase only (check metadata, code refs, claims) |
| `--docs-only` | Validate + update docs, skip NotebookLM sync and artifacts |
| `--sync-only` | Validate + sync to NotebookLM, skip artifact regeneration |
| `--full` | Full cycle: validate, update, sync, regenerate artifacts (requires `--apply`) |

## Options

| Option | Description |
|--------|-------------|
| `--target PATH` | Specify repo path (default: current working directory) |
| `--force` | Force artifact regeneration regardless of change threshold |
| `--artifacts "a,b"` | Only refresh specific artifacts (e.g., "audio,mind_map") |
| `--skip-unchanged` | Skip docs that haven't changed (default behavior) |

## Usage Examples

```bash
# Dry-run validation on current repo (safe, default)
/doc-refresh

# Dry-run on a specific repo
/doc-refresh --target ~/SyncedProjects/C017_brain-on-tap

# Apply changes: update docs only
/doc-refresh --apply --docs-only

# Apply changes: full sync including artifact refresh
/doc-refresh --apply --full

# Force artifact regeneration (skips change threshold check)
/doc-refresh --apply --full --force

# Only refresh specific artifacts
/doc-refresh --apply --sync-only --artifacts "mind_map,briefing_doc"
```

## Instructions

Read the Ralph loop prompt from `src/notebooklm_mcp/doc_refresh/PROMPT.md` in the C021_notebooklm-mcp repository and execute it.

**Target repo:** Use `--target` value if provided, otherwise use current working directory.

**Important:** This is a Ralph loop. Each iteration builds on the previous. Output `<promise>DOC REFRESH COMPLETE</promise>` only when ALL applicable phases are complete:

| Mode | Required for Promise |
|------|---------------------|
| `--dry-run` | Validation report generated |
| `--validate-only` | Validation report generated |
| `--docs-only` | Docs validated, updated, committed |
| `--sync-only` | Docs synced to NotebookLM |
| `--full` | Docs updated, synced, artifacts refreshed, receipt written |

Begin by reading the PROMPT.md file and following its instructions for the specified mode.
