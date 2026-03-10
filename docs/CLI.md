# CLI Reference

This page tracks the command-line interfaces and scheduled automation for this repo.

## Executables

- `notebooklm-mcp` — start the MCP server
- `notebooklm-mcp-auth` — extract/retry NotebookLM auth via Chrome profile flow
- `notebooklm-sync` — deterministic document sync + receipts engine

## Core Commands

### MCP server

```bash
notebooklm-mcp
```

### Auth workflows

```bash
# Recommended: auto mode
notebooklm-mcp-auth

# Fallback: manual cookie file outside the repo
notebooklm-mcp-auth --file ~/Downloads/notebooklm-cookies.txt
```

## Read-Only Smoke Verification

Use this when you want operator confidence without mutating NotebookLM state.

### 1. Shell smoke

```bash
notebooklm-sync --list
```

- Success: notebook list prints normally
- Failure: if you see `ValueError: Cookies have expired`, run `notebooklm-mcp-auth`,
  restart your AI tool, and retry this same command

### 2. MCP smoke

After the shell smoke passes and your MCP client is restarted:

```python
notebook_list(max_results=5)
notebook_get(notebook_id="<known_notebook_id>")
```

- `notebook_list` confirms auth + listing
- `notebook_get` confirms read access against a known notebook without creating or mutating anything

## Nightly Receipt Review

To review the most recent nightly batch window:

```bash
ls -1t ~/.config/notebooklm-mcp/sync_receipts | head -n 7
tail -n 200 ~/.config/notebooklm-mcp/refresh.log
```

Look for:
- one batch receipt per expected day
- `repos_failed` spikes or repeated failures in the same repo
- any non-zero `orphans_cleaned` or `orphans_tracked`
- whether the target repo was `success`, `skipped`, or `failed`

### Document sync (manual)

```bash
# List notebooks
notebooklm-sync --list

# Sync Tier 3 docs (README, CLAUDE, docs)
notebooklm-sync --repo <REPO_ID> --tier3

# Sync with audio overview
notebooklm-sync --repo <REPO_ID> --tier3 --audio

# Non-interactive sync
notebooklm-sync --repo <REPO_ID> --tier3 --audio --yes

# Sync explicit files to a named notebook
notebooklm-sync "<NOTEBOOK_NAME>" docs/*.md
```

### Batch / Repo-map modes

```bash
# Plan-only for all mapped repos
notebooklm-sync --all

# Apply all mapped repos
notebooklm-sync --all --apply

# Apply only changed repos
notebooklm-sync --all --apply --changed-only

# Apply only changed kitted repos
notebooklm-sync --all --apply --changed-only --tier kitted

# Force artifact regeneration
notebooklm-sync --all --apply --force-artifacts
```

## Scheduled automation (macOS)

```bash
# Install recurring nightly schedule (local 2:00 AM)
make install-schedule

# Remove recurring schedule
make uninstall-schedule
```

The installed launchd job runs:

```bash
notebooklm-sync --all --apply --changed-only
```

## Operations files

- `~/.config/notebooklm-mcp/notebook_map.yaml`
- `~/.config/notebooklm-mcp/sync_receipts/`
- `~/.config/notebooklm-mcp/refresh.log`

## Validation

```bash
make health
make verify
```
