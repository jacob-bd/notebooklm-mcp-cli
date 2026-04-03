# GEMINI.md

## Project Overview

**NotebookLM MCP Server**

This project implements a Model Context Protocol (MCP) server that provides programmatic access to [NotebookLM](https://notebooklm.google.com). It allows AI agents and developers to interact with NotebookLM notebooks, sources, and query capabilities.

Tested with personal/free tier accounts. May work with Google Workspace accounts but has not been tested. This project relies on reverse-engineered internal APIs (`batchexecute` RPCs).

## Environment & Setup

The project uses `uv` for dependency management and tool installation.

### Prerequisites
- Python 3.11+
- `uv` (Universal Python Package Manager)
- Google Chrome (for automated authentication)

### Installation

**From PyPI (Recommended):**
```bash
uv tool install notebooklm-mcp-server
# or: pip install notebooklm-mcp-server
```

**From Source (Development):**
```bash
git clone https://github.com/jeremybrad/notebooklm-mcp.git
cd notebooklm-mcp
uv tool install .
```

**Reinstalling after code changes:**
```bash
uv cache clean && uv tool install --force .
```

## Authentication

**You only need to extract cookies** - the CSRF token and session ID are auto-extracted when the MCP starts.

**Option 1: CLI Auth (Recommended)**
```bash
notebooklm-mcp-auth
```
Launches a dedicated Chrome profile, you log in to Google, and cookies are extracted automatically.

**Option 2: Chrome DevTools MCP**
If your AI assistant has Chrome DevTools MCP access:
1. Navigate to `notebooklm.google.com`
2. Get cookies from any network request
3. Call `save_auth_tokens(cookies=<cookie_header>)`

**Option 3: Environment Variables (Manual)**
```bash
export NOTEBOOKLM_COOKIES="SID=xxx; HSID=xxx; SSID=xxx; ..."
```

Cookies last for weeks. When they expire, re-run `notebooklm-mcp-auth`.

**Auth rotation:** Heavy API usage (~25+ calls) can trigger cookie rotation on free tier.

## Development Workflow

### Running
```bash
# MCP server
notebooklm-mcp

# Auth CLI
notebooklm-mcp-auth

# Doc sync CLI
notebooklm-sync --list
notebooklm-sync --repo C012_round-table --tier3
notebooklm-sync --all --apply --changed-only
```

### Testing
```bash
# Run all tests
uv run pytest

# Run a specific test file
uv run pytest tests/test_file.py::test_function -v

# With coverage
uv run pytest --cov=notebooklm_mcp --cov-report=term-missing
```

## Project Structure

- `src/notebooklm_mcp/`
    - `server.py`: FastMCP server with 31 tool definitions
    - `api_client.py`: Reverse-engineered internal API client
    - `auth.py`: Token caching, validation, and loading
    - `auth_cli.py`: CLI for Chrome-based auth token extraction (`notebooklm-mcp-auth`)
    - `sync_cli.py`: CLI for deterministic doc syncing (`notebooklm-sync`)
- `docs/API_REFERENCE.md`: Detailed RPC IDs, parameter structures, response formats
- `docs/CLI.md`: CLI usage reference and smoke ladder
- `docs/AUTHENTICATION.md`: Full auth lifecycle documentation
- `docs/TROUBLESHOOTING.md`: Common issues and recovery steps
- `pyproject.toml`: Project configuration and dependencies

## MCP Tools (31 total)

| Category | Tools |
|----------|-------|
| Notebook management | `notebook_list`, `notebook_create`, `notebook_get`, `notebook_describe`, `notebook_rename`, `notebook_delete` |
| Source management | `notebook_add_url`, `notebook_add_text`, `notebook_add_drive`, `source_describe`, `source_list_drive`, `source_sync_drive`, `source_delete` |
| Chat | `notebook_query`, `chat_configure` |
| Research | `research_start`, `research_status`, `research_import` |
| Studio | `audio_overview_create`, `video_overview_create`, `infographic_create`, `slide_deck_create`, `report_create`, `flashcards_create`, `quiz_create`, `data_table_create`, `mind_map_create`, `mind_map_list`, `studio_status`, `studio_delete` |
| Auth | `save_auth_tokens` |

**Confirmation required** for destructive/expensive operations: `notebook_delete`, `source_delete`, `source_sync_drive`, all studio creation tools, `studio_delete`.

## Key Conventions

- **Reverse Engineering:** This project relies on undocumented APIs. Changes to Google's internal API will break functionality.
- **RPC Protocol:** The API uses Google's `batchexecute` protocol. Responses often contain "anti-XSSI" prefixes (`)]}'`) that must be stripped.
- **Tools:** New features should be exposed as MCP tools in `server.py` and documented in `docs/API_REFERENCE.md`.
- **Auth:** Prefer `notebooklm-mcp-auth` CLI for token extraction. Chrome DevTools MCP is the fallback for in-session workflows.
