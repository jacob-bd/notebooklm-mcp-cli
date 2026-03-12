# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**NotebookLM MCP Server & CLI** - Provides programmatic access to NotebookLM (notebooklm.google.com) via both a Model Context Protocol server and a comprehensive command-line interface.

Tested with personal/free tier accounts. May work with Google Workspace accounts but has not been tested.

## Development Commands

```bash
# Install dependencies
uv tool install .

# Reinstall after code changes (ALWAYS clean cache first)
uv cache clean && uv tool install --force .

# Run the MCP server (stdio)
notebooklm-mcp

# Run with Debug logging
notebooklm-mcp --debug

# Run as HTTP server
notebooklm-mcp --transport http --port 8000

# Run tests
uv run pytest

# Run a single test
uv run pytest tests/test_file.py::test_function -v
```

**Python requirement:** >=3.11

## Authentication (SIMPLIFIED!)

**You only need to provide COOKIES!** The CSRF token and session ID are now **automatically extracted** when needed.

### Method 1: Chrome DevTools MCP (Recommended)

**Option A - Fast (Recommended):**
Extract CSRF token and session ID directly from network request - **no page fetch needed!**

```python
# 1. Navigate to NotebookLM page
navigate_page(url="https://notebooklm.google.com/")

# 2. Get a batchexecute request (any NotebookLM API call)
get_network_request(reqid=<any_batchexecute_request>)

# 3. Save with all three fields from the network request:
save_auth_tokens(
    cookies=<cookie_header>,
    request_body=<request_body>,  # Contains CSRF token
    request_url=<request_url>      # Contains session ID
)
```

**Option B - Minimal (slower first call):**
Save only cookies, tokens extracted from page on first API call

```python
save_auth_tokens(cookies=<cookie_header>)
```

### Method 2: Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `NOTEBOOKLM_COOKIES` | Yes | Full cookie header from Chrome DevTools |
| `NOTEBOOKLM_CSRF_TOKEN` | No | (DEPRECATED - auto-extracted) |
| `NOTEBOOKLM_SESSION_ID` | No | (DEPRECATED - auto-extracted) |
| `NOTEBOOKLM_BL` | No | Override for build label / bl URL param (auto-extracted from page) |
| `NOTEBOOKLM_HL` | No | Interface language and default artifact language (default: `en`) |
| `NOTEBOOKLM_REQUEST_INTERVAL` | No | Minimum seconds between API calls for proactive rate limiting (default: `0.25`) |
| `NOTEBOOKLM_QUERY_TIMEOUT` | No | Query timeout in seconds (default: `120.0`) |
| `ANTHROPIC_API_KEY` | No | Claude API key for agent query bypass (no NLM rate limits) |
| `NOTEBOOKLM_AGENT_MODEL` | No | Claude model for agent queries (default: `claude-haiku-4-5-20251001`) |
| `NOTEBOOKLM_AGENT_MAX_SOURCES` | No | Max sources to include in agent context (default: `20`) |
| `NOTEBOOKLM_AGENT_MAX_CHARS` | No | Max chars per source in agent context (default: `50000`) |
| `CLOUDFLARE_API_TOKEN` | No | CF API token for Vectorize + Workers AI (semantic search pipeline) |
| `CLOUDFLARE_ACCOUNT_ID` | No | Cloudflare account ID for Vectorize |
| `VECTORIZE_INDEX_NAME` | No | Vectorize index name (default: `notebooklm-sources`) |
| `CF_AI_MODEL` | No | Cloudflare AI embedding model (default: `@cf/baai/bge-base-en-v1.5`) |

### Token Expiration

- **Cookies**: Stable for weeks, but some rotate on each request
- **CSRF token**: Auto-refreshed on each client initialization
- **Session ID**: Auto-refreshed on each client initialization
- **Build label (bl)**: Auto-extracted during login and CSRF refresh; stays current with Google's build

When API calls fail with auth errors, re-extract fresh cookies from Chrome DevTools.

## Architecture

```
src/notebooklm_tools/
├── __init__.py          # Package version
├── services/            # Shared service layer (v0.3.0+)
│   ├── errors.py        # ServiceError, ValidationError, NotFoundError, etc.
│   ├── chat.py          # Chat/query logic
│   ├── downloads.py     # Artifact downloading
│   ├── exports.py       # Google Docs/Sheets export
│   ├── notebooks.py     # Notebook CRUD + describe
│   ├── notes.py         # Note CRUD
│   ├── research.py      # Research start/poll/import
│   ├── sharing.py       # Public link, invite, status
│   ├── sources.py       # Source add/list/sync/delete
│   └── studio.py        # Artifact creation, status, rename, delete
├── cli/                 # CLI commands and formatting (thin wrapper)
├── mcp/                 # MCP server + tools (thin wrapper)
│   ├── server.py        # FastMCP server facade
│   └── tools/           # Modular tool definitions per domain
├── core/                # Low-level API client (no business logic)
│   ├── client.py        # Internal batchexecute API calls
│   ├── constants.py     # Code-name mappings (CodeMapper class)
│   └── auth.py          # AuthManager for profile-based token caching
└── utils/
    ├── config.py        # Configuration and storage paths
    └── cdp.py           # Chrome DevTools Protocol for cookie extraction
```

**Layering Rules (v0.3.0+):**
- `cli/` and `mcp/` are thin wrappers: they handle UX concerns (prompts, spinners, JSON responses) and delegate to `services/`
- `services/` contains all business logic, validation, and error handling. Returns typed dicts.
- `cli/` and `mcp/` must NOT import from `core/` directly — always go through `services/`
- `services/` raises `ServiceError`/`ValidationError` — never raw exceptions

**Storage Structure (`~/.notebooklm-mcp-cli/`):**
```
├── config.toml                    # CLI settings (default_profile, output format)
├── aliases.json                   # Notebook aliases
├── profiles/<name>/auth.json      # Per-profile credentials and email
├── chrome-profile/                # Chrome session (single-profile/legacy)
└── chrome-profiles/<name>/        # Chrome sessions (multi-profile)
```

**Executables:**
- `nlm` - Command-line interface
- `notebooklm-mcp` - The MCP server

## MCP Tools Provided

| Tool | Purpose |
|------|---------|
| `notebook_list` | List all notebooks |
| `notebook_create` | Create new notebook |
| `notebook_get` | Get notebook details |
| `notebook_describe` | Get AI-generated summary of notebook content with keywords |
| `source_describe` | Get AI-generated summary and keyword chips for a source |
| `source_get_content` | Get raw text content from a source (no AI processing) |
| `notebook_rename` | Rename a notebook |
| `chat_configure` | Configure chat goal/style and response length |
| `notebook_delete` | Delete a notebook (REQUIRES confirmation) |
| `source_add` | Add source (url, text, drive, file) |
| `notebook_query` | Ask questions (AI answers!) |
| `source_list_drive` | List sources with types, check Drive freshness |
| `source_sync_drive` | Sync stale Drive sources (REQUIRES confirmation) |
| `source_rename` | Rename a source in a notebook |
| `source_delete` | Delete a source from notebook (REQUIRES confirmation) |
| `research_start` | Start Web or Drive research to discover sources |
| `research_status` | Check research progress and get results |
| `research_import` | Import discovered sources into notebook |
| `studio_create` | Generate unified content (audio, video, infographic, slides, etc.) |
| `download_artifact` | Download any artifact (audio, video, pdf, markdown, json) |
| `export_artifact` | Export Data Tables to Google Sheets or Reports to Google Docs |
| `studio_status` | Check studio artifact generation status |
| `studio_delete` | Delete studio artifacts (REQUIRES confirmation) |
| `studio_revise` | Revise slides in an existing slide deck (creates new artifact, REQUIRES confirmation) |
| `notebook_share_status` | Get sharing settings and collaborators |
| `notebook_share_public` | Enable/disable public link access |
| `notebook_share_invite` | Invite collaborator by email |
| `save_auth_tokens` | Save tokens extracted via Chrome DevTools MCP |
| `refresh_auth` | Reload auth tokens or run headless auth |
| `note_create` | Create a note in a notebook |
| `note_list` | List all notes in a notebook |
| `note_update` | Update a note's content or title |
| `note_delete` | Delete a note (REQUIRES confirmation) |

**IMPORTANT - Operations Requiring Confirmation:**
- `notebook_delete` requires `confirm=True` - deletion is IRREVERSIBLE
- `source_delete` requires `confirm=True` - deletion is IRREVERSIBLE
- `source_sync_drive` requires `confirm=True` - always show stale sources first via `source_list_drive`
- All studio creation tools require `confirm=True` - show settings and get user approval first
- `studio_delete` requires `confirm=True` - list artifacts first via `studio_status`, deletion is IRREVERSIBLE
- `studio_revise` requires `confirm=True` - creates a new artifact with revisions applied
- `note_delete` requires `confirm=True` - deletion is IRREVERSIBLE

## GDoc-as-Agent-Instruction Pattern

Each notebook can have a **designated Google Doc** that serves as both its data source and its agent configuration file. This is the canonical way to keep notebooks clean and agents self-updating.

### Why This Matters

- Instead of adding many sources, maintain **one GDoc per notebook**
- Update the GDoc with new data → sync it → NotebookLM picks up the changes
- The GDoc also contains **agent instructions** (persona, scope, response style)
- After answering a query, the agent writes findings back as a **notebook note** — ready to be copied back into the GDoc's DATA section, completing the loop

### GDoc Structure (Required Format)

```markdown
## AGENT INSTRUCTIONS
You are the [Notebook Title] agent. You specialize in [domain].
When answering questions, [behavior, tone, scope instructions].
Only answer based on the documents in this notebook.

## DATA
[Facts, records, findings — updated by humans or pasted from agent notes]
```

The `## AGENT INSTRUCTIONS` section is read automatically. Everything between that heading and the next `##` is used as the agent's system context when routing queries to this notebook.

### Setup Workflow

```
1. agent_gdoc_link(notebook_id, gdoc_id, source_id=<nlm_source_id>)
   └─ Links the GDoc; source_id is the NotebookLM Drive source ID for that GDoc

2. agent_gdoc_refresh_instructions(notebook_id)
   └─ Reads the GDoc source content, extracts ## AGENT INSTRUCTIONS, caches it

3. agent_registry_build(force=True)
   └─ Rebuilds registry — instructions now embedded in AgentEntry

4. notebook_agent_query(query)
   └─ Routes to correct notebook, prepends instructions, returns answer
   └─ Automatically writes findings back as a notebook note
```

### Audit Coverage

```
agent_gdoc_check()
└─ Lists all notebooks: which have designated GDocs, which don't
└─ Shows whether instructions are loaded for each linked notebook
```

### Self-Update Loop

```
Query → Agent reads instructions from GDoc → Answers → Saves findings as note
                                                              ↓
                          Human reviews note → Pastes into GDoc DATA section
                                                              ↓
                              source_sync_drive() → Notebook source updated
                                                              ↓
                                         Future queries see the new data
```

When the agent has Google Docs write access (future), this loop will be fully automatic.

## Features NOT Yet Implemented

None - all NotebookLM features that can be accessed programmatically are implemented.

## Troubleshooting

### "401 Unauthorized" or "403 Forbidden"
- Cookies or CSRF token expired
- Re-extract from Chrome DevTools

### "Invalid CSRF token"
- The `at=` value expired
- Must match the current session

### Empty notebook list
- Session might be for a different Google account
- Verify you're logged into the correct account

### Rate limit errors
- Free tier: ~50 queries/day
- Wait until the next day or upgrade to Plus

## Documentation

### API Reference

**For detailed API documentation** (RPC IDs, parameter structures, response formats), see:

**[docs/API_REFERENCE.md](./docs/API_REFERENCE.md)**

This includes:
- All discovered RPC endpoints and their parameters
- Source type structures (URL, text, Drive)
- Studio content creation (audio, video, reports, etc.)
- Research workflow details
- Mind map generation process
- Source metadata structures

Only read API_REFERENCE.md when:
- Debugging API issues
- Adding new features
- Understanding internal API behavior

### MCP Test Plan

**For comprehensive MCP tool testing**, see:

**[docs/MCP_CLI_TEST_PLAN.md](./docs/MCP_CLI_TEST_PLAN.md)**

This includes:
- Step-by-step test cases for all 29 MCP tools and CLI commands
- Authentication and basic operations tests
- Source management and Drive sync tests
- Studio content generation tests (audio, video, infographics, etc.)
- Quick copy-paste test prompts for validation

Use this test plan when:
- Validating MCP server functionality after code changes
- Testing new tool implementations
- Debugging MCP tool issues

## Contributing

When adding new features:

1. Use Chrome DevTools MCP to capture the network request
2. Document the RPC ID in docs/API_REFERENCE.md
3. Add the param structure with comments
4. Add the low-level API method in `core/client.py`
5. Add business logic in the appropriate `services/*.py` module
6. Add a thin wrapper in `mcp/tools/*.py` (for MCP) and `cli/commands/*.py` (for CLI)
7. Write unit tests for the service function in `tests/services/`
8. Update the "Features NOT Yet Implemented" checklist
9. Add test case to docs/MCP_TEST_PLAN.md

## License

MIT License
