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
notebooklm-mcp-auth
notebooklm-mcp-auth --file
```

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
