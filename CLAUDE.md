# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## SESSION RECOVERY (Read First After Compaction)

**Auth dead?** Run `notebooklm-mcp-auth`, restart Claude Code, verify with `notebook_list()`. See [Troubleshooting](./docs/TROUBLESHOOTING.md) for full recovery steps.

---

## Project Overview

**NotebookLM MCP Server** - Provides programmatic access to NotebookLM (notebooklm.google.com) using reverse-engineered internal APIs.

Tested with personal/free tier accounts. May work with Google Workspace accounts but has not been tested.

## Development Commands

```bash
# Install dependencies
uv tool install .

# Reinstall after code changes (ALWAYS clean cache first)
uv cache clean && uv tool install --force .

# Run the MCP server
notebooklm-mcp

# Run tests
uv run pytest

# Run a single test
uv run pytest tests/test_file.py::test_function -v
```

**Python requirement:** >=3.11

## Authentication

Preferred: `notebooklm-mcp-auth` (auto mode). Fallback: `notebooklm-mcp-auth --file`. In-session: `save_auth_tokens(cookies=<header>)`.

For full details, see **[docs/AUTHENTICATION.md](./docs/AUTHENTICATION.md)**.

## Architecture

```
src/notebooklm_mcp/
├── __init__.py      # Package version
├── server.py        # FastMCP server with tool definitions
├── api_client.py    # Internal API client (reverse-engineered)
├── auth.py          # Token caching and validation
├── auth_cli.py      # CLI for Chrome-based auth (notebooklm-mcp-auth)
├── sync_cli.py      # CLI for deterministic doc sync (notebooklm-sync)
├── doc_refresh/     # Scheduled doc sync engine (discovery, hashing, manifests, validation)
└── primer_gen/      # Project primer generator (DEPRECATED — moved to C010_standards)
```

**Executables:**
- `notebooklm-mcp` - The MCP server
- `notebooklm-mcp-auth` - CLI for extracting tokens (requires closing Chrome)
- `notebooklm-sync` - CLI for deterministic doc syncing with receipts
- `doc-refresh` - Scheduled doc refresh engine (used by launchd nightly job)

### notebooklm-sync CLI

Deterministic document syncing tool with idempotence and audit trails.

**Config paths:**
- `~/.config/notebooklm-mcp/notebook_map.yaml` - Repo-to-notebook mappings with source IDs
- `~/.config/notebooklm-mcp/sync_receipts/` - JSON audit trail for each sync run

**Usage modes:**

```bash
# List notebooks
notebooklm-sync --list

# Tier 3 auto-discovery (README, CLAUDE, docs/*.md, 10_docs/**/*.md)
notebooklm-sync --repo C012_round-table --tier3

# With audio overview generation
notebooklm-sync --repo C012_round-table --tier3 --audio

# Non-interactive (skip prompts)
notebooklm-sync --repo C012_round-table --tier3 --audio --yes

# Custom focus for audio
notebooklm-sync --repo C012_round-table --tier3 --audio --focus "Explain the architecture"

# Nightly batch mode (used by launchd)
notebooklm-sync --all --apply --changed-only
```

**Key features:**
- **Idempotence**: SHA256 hashes skip unchanged files
- **Cross-notebook safety**: Uses mapped notebook_id to prevent accidental source deletion
- **Receipts**: JSON audit trail with timestamps, actions, and source IDs

## Operations and Scheduling for Docs

Use the scheduled refresh pipeline when maintaining doc hygiene across repos:

- `make install-schedule` installs a macOS launchd job at 02:00 local time.
- `make uninstall-schedule` removes that launchd job.
- Scheduled job command:

```bash
notebooklm-sync --all --apply --changed-only
```

- Runbook logs are written to:

```bash
~/.config/notebooklm-mcp/refresh.log
```

- If batch runs fail, fix auth first and rerun the same command.

For CLI references and scheduled-operations details, see **[docs/CLI.md](./docs/CLI.md)**.

## MCP Tools Provided

31 tools registered in `server.py`. Tools marked `confirm=True` require explicit user confirmation before execution. Always show current state before destructive/expensive operations. See tool docstrings in `server.py` for the full reference.

## Troubleshooting

**For comprehensive troubleshooting**, see **[docs/TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md)**.

### Quick Reference: Auth Recovery

When `notebook_list()` returns 0 notebooks (auth dead):

1. Close all NotebookLM tabs in Chrome
2. Run: `notebooklm-mcp-auth`
3. **Restart Claude Code** (required to reload tokens)
4. Verify: `notebook_list()` should return your notebooks

**Auth rotation pattern:** Heavy API usage (~25+ calls) can trigger cookie rotation on free tier.

### Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| 401/403 errors | Cookies expired | Re-run `notebooklm-mcp-auth` |
| notebook_list returns 0 | Auth dead | Full auth recovery (see above) |
| Auth CLI succeeds but API fails | MCP server has stale tokens | Restart Claude Code |
| video_overview fails "No sources" | API quirk | Retry the request |
| Mind maps missing from studio_status | Stored separately | Use `mind_map_list()` |
| Rate limit errors | Free tier: ~50 queries/day | Wait or upgrade to Plus |
| Sync deletes wrong sources | notebook_map has stale notebook_id | Delete entry from `notebook_map.yaml` |
| Sync receipts not found | Config dir issue | Check `~/.config/notebooklm-mcp/sync_receipts/` |
| Tier 3 discovery missing files | Non-standard structure | Use explicit file paths instead |

## Documentation

- **[docs/API_REFERENCE.md](./docs/API_REFERENCE.md)** — RPC IDs, parameter structures, response formats (read when debugging API issues or adding features)
- **[docs/MCP_TEST_PLAN.md](./docs/MCP_TEST_PLAN.md)** — Step-by-step test cases for all 31 MCP tools (read when validating after code changes)

## Contributing

When adding new tools: capture the network request via Chrome DevTools, document the RPC ID in `docs/API_REFERENCE.md`, implement in `api_client.py` + `server.py`, and add a test case to `docs/MCP_TEST_PLAN.md`.

**Gotcha:** `generate-project-primer` entry in `pyproject.toml` is deprecated (moved to C010_standards). Do not use — clean up when convenient.

## License

MIT License
