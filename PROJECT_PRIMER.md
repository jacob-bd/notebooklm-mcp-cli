# PROJECT PRIMER — C021_notebooklm-mcp

## Provenance

- **Generated**: 2026-01-12 21:52
- **Repo SHA**: 337cf4b
- **Generator**: generate-project-primer v1.0.0
- **Source Docs**:
  - README.md
  - CHANGELOG.md
  - META.yaml
  - CLAUDE.md
  - RELATIONS.yaml

> **Derived document.** If conflicts exist, source docs override this primer.

---

## Quick Facts

| Field | Value |
|-------|-------|
| **Repo ID** | C021_notebooklm-mcp |
| **Status** | active |
| **Owner** | unknown |
| **Series** | C (Core) |
| **Tier** | complex |
| **Entry Point** | See Quickstart |
| **Port** | — |

---

## What This Repo IS

NotebookLM MCP Server - Programmatic access to NotebookLM via reverse-engineered APIs

---

## What This Repo IS NOT

- *TODO: Document what this repo does NOT do*
- *TODO: List explicit deferrals to other repos*
- *Example: Does NOT handle credentials (defer to C001_mission-control)*

---

## Responsibility Boundaries

### This Repo OWNS
- NotebookLM MCP Server (programmatic access to notebooklm.google.com)
- Reverse-engineered NotebookLM internal APIs (batchexecute protocol)
- Auth token caching and extraction (cookies, CSRF, session)
- 31 MCP tools for notebook/source/studio operations
- Doc-refresh Ralph loop for syncing canonical docs to NotebookLM
- PROJECT_PRIMER generator (primer_gen module)
- notebook_map.yaml tracking for doc sync state

### This Repo MUST NOT Own
- NotebookLM service itself (Google owns that)
- Workspace governance rules or protocols (belongs to C010_standards)
- Source document authoring (documents live in their source repos)
- Credential storage (uses C001_mission-control vault for API keys)
- Memory infrastructure or SADB pipeline (belongs to C002/C003)

---

## Integration Map

| External System | Direction | Interface | Status |
|-----------------|-----------|-----------|--------|
| C010_standards | depends on | Betty Protocol, README repo card standard, workspace conventions | active |
| C001_mission-control | depends on | Credential vault for any API keys needed | active |
| C017_brain-on-tap | depends on | Primary test target for doc-refresh; has active NotebookLM notebook | active |

---

## Quick Routing

| If you want to... | Read this section |
|-------------------|-------------------|
| Understand purpose | What This Repo IS |
| Run locally | Quickstart |
| Debug issues | Operations |

---

## README

# NotebookLM MCP Server

![NotebookLM MCP Header](docs/media/header.jpeg)

An MCP server for **NotebookLM** (notebooklm.google.com).

> **Note:** Tested with Pro/free tier accounts. May work with NotebookLM Enterprise accounts but has not been tested.

📺 **Watch the Demo** - See the MCP in action!

[![NotebookLM MCP Demo](https://img.youtube.com/vi/d-PZDQlO4m4/hqdefault.jpg)](https://www.youtube.com/watch?v=d-PZDQlO4m4)

## Features

| Tool | Description |
|------|-------------|
| `notebook_list` | List all notebooks |
| `notebook_create` | Create a new notebook |
| `notebook_get` | Get notebook details with sources |
| `notebook_describe` | Get AI-generated summary of notebook content |
| `source_describe` | Get AI-generated summary and keywords for a source |
| `notebook_rename` | Rename a notebook |
| `chat_configure` | Configure chat goal/style and response length |
| `notebook_delete` | Delete a notebook (requires confirmation) |
| `notebook_add_url` | Add URL/YouTube as source |
| `notebook_add_text` | Add pasted text as source |
| `notebook_add_drive` | Add Google Drive document as source |
| `notebook_query` | Ask questions and get AI answers |
| `source_list_drive` | List sources with freshness status |
| `source_sync_drive` | Sync stale Drive sources (requires confirmation) |
| `source_delete` | Delete a source from notebook (requires confirmation) |
| `research_start` | Start Web or Drive research to discover sources |
| `research_status` | Poll research progress with built-in wait |
| `research_import` | Import discovered sources into notebook |
| `audio_overview_create` | Generate audio podcasts (requires confirmation) |
| `video_overview_create` | Generate video overviews (requires confirmation) |
| `infographic_create` | Generate infographics (requires confirmation) |
| `slide_deck_create` | Generate slide decks (requires confirmation) |
| `studio_status` | Check studio artifact generation status |
| `studio_delete` | Delete studio artifacts (requires confirmation) |
| `save_auth_tokens` | Save cookies for authentication |

## Important Disclaimer

This MCP uses **reverse-engineered internal APIs** that:
- Are undocumented and may change without notice
- Require cookie extraction from your browser (I have a tool for that!)

Use at your own risk for personal/experimental purposes.

## Installation

Install from PyPI using your preferred Python package manager:

### Using uv (Recommended)
```bash
uv tool install notebooklm-mcp-server
```

### Using pip
```bash
pip install notebooklm-mcp-server
```

### Using pipx
```bash
pipx install notebooklm-mcp-server
```

<details>
<summary>Alternative: Install from Source</summary>

```bash
# Clone the repository
git clone https://github.com/jacob-bd/notebooklm-mcp.git
cd notebooklm-mcp

# Install with uv
uv tool install .
```
</details>

## Upgrading

```bash
# Using uv
uv tool upgrade notebooklm-mcp-server

# Using pip
pip install --upgrade notebooklm-mcp-server

# Using pipx
pipx upgrade notebooklm-mcp-server
```

After upgrading, restart your AI tool to reconnect to the updated MCP server:

- **Claude Code:** Restart the application, or use `/mcp` to reconnect
- **Cursor:** Restart the application
- **Gemini CLI:** Restart the CLI session

## Uninstalling

To completely remove the MCP:

```bash
# Using uv
uv tool uninstall notebooklm-mcp-server

# Using pip
pip uninstall notebooklm-mcp-server

# Using pipx
pipx uninstall notebooklm-mcp-server

# Remove cached auth tokens (optional)
rm -rf ~/.notebooklm-mcp
```

Also remove from your AI tools:

| Tool | Command |
|------|---------|
| Claude Code | `claude mcp remove notebooklm-mcp` |
| Gemini CLI | `gemini mcp remove notebooklm-mcp` |
| Cursor/VS Code | Remove entry from `~/.cursor/mcp.json` or `~/.vscode/mcp.json` |

## Authentication

Before using the MCP, you need to authenticate with NotebookLM. Run:

```bash
# Recommended: Auto mode (launches Chrome, you log in)
notebooklm-mcp-auth

# Alternative: File mode (manual cookie extraction)
notebooklm-mcp-auth --file
```

**Auto mode** launches a dedicated Chrome profile, you log in to Google, and cookies are extracted automatically. Your login persists for future auth refreshes.

**File mode** shows instructions for manually extracting cookies from Chrome DevTools and saving them to a file.

After successful auth, add the MCP to your AI tool and restart.

For detailed instructions, troubleshooting, and how the authentication system works, see **[docs/AUTHENTICATION.md](docs/AUTHENTICATION.md)**.

## MCP Configuration

> **⚠️ Context Window Warning:** This MCP provides **31 tools** which consume a significant portion of your context window. It's recommended to **disable the MCP when not actively using NotebookLM** to preserve context for your other work. In Claude Code, use `@notebooklm-mcp` to toggle it on/off, or use `/mcp` command.

No environment variables needed - the MCP uses cached tokens from `~/.notebooklm-mcp/auth.json`.

### Claude Code (Recommended CLI Method)

Use the built-in CLI command to add the MCP server:

**Add for all projects (recommended):**
```bash
claude mcp add --scope user notebooklm-mcp notebooklm-mcp
```

**Or add for current project only:**
```bash
claude mcp add notebooklm-mcp notebooklm-mcp
```

That's it! Restart Claude Code to use the MCP tools.

**Verify installation:**
```bash
claude mcp list
```

<details>
<summary>Alternative: Manual JSON Configuration</summary>

If you prefer to edit the config file manually, add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "notebooklm-mcp": {
      "command": "notebooklm-mcp"
    }
  }
}
```

Restart Claude Code after editing.
</details>

### Cursor, VS Code, Claude Desktop & Other IDEs

For tools that use JSON configuration files:

| Tool | Config File Location |
|------|---------------------|
| Cursor | `~/.cursor/mcp.json` |
| VS Code | `~/.vscode/mcp.json` |
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) |

**Step 1:** Find your installed path:
```bash
which notebooklm-mcp
```

This typically returns `/Users/<YOUR_USERNAME>/.local/bin/notebooklm-mcp` on macOS.

**Step 2:** Add this configuration (replace the path with your result from Step 1):
```json
{
  "mcpServers": {
    "notebooklm-mcp": {
      "command": "/Users/<YOUR_USERNAME>/.local/bin/notebooklm-mcp"
    }
  }
}
```

Restart the application after adding the configuration.

### Other MCP-Compatible Tools

**CLI tools with built-in MCP commands** (AIDER, Codex, OpenCode, etc.):
```bash
<your-tool> mcp add notebooklm-mcp notebooklm-mcp
```

**Tools using JSON config files** — use the full path approach shown above.

### Gemini CLI (Recommended CLI Method)

Use the built-in CLI command to add the MCP server:

**Add for all projects (recommended):**
```bash
gemini mcp add --scope user notebooklm-mcp notebooklm-mcp
```

**Or add for current project only:**
```bash
gemini mcp add notebooklm-mcp notebooklm-mcp
```

That's it! Restart Gemini CLI to use the MCP tools.

**Verify installation:**
```bash
gemini mcp list
```

<details>
<summary>Alternative: Manual JSON Configuration</summary>

Add to `~/.gemini/settings.json` under `mcpServers` (run `which notebooklm-mcp` to find your path):
```json
"notebooklm-mcp": {
  "command": "/Users/<YOUR_USERNAME>/.local/bin/notebooklm-mcp"
}
```

Restart Gemini CLI after editing.
</details>

### Managing Context Window Usage

Since this MCP has 31 tools, it's good practice to disable it when not in use:

**Claude Code:**
```bash
# Toggle on/off by @-mentioning in chat
@notebooklm-mcp

# Or use the /mcp command to enable/disable
/mcp
```

**Cursor/Gemini CLI:**
- Comment out the server in your config file when not needed
- Or use your tool's MCP management features if available

## What You Can Do

Simply chat with your AI tool (Claude Code, Cursor, Gemini CLI) using natural language. Here are some examples:

### Research & Discovery

- "List all my NotebookLM notebooks"
- "Create a new notebook called 'AI Strategy Research'"
- "Start web research on 'enterprise AI ROI metrics' and show me what sources it finds"
- "Do a deep research on 'cloud marketplace trends' and import the top 10 sources"
- "Search my Google Drive for documents about 'product roadmap' and create a notebook"

### Adding Content

- "Add this URL to my notebook: https://example.com/article"
- "Add this YouTube video about Kubernetes to the notebook"
- "Add my meeting notes as a text source to this notebook"
- "Import this Google Doc into my research notebook"

### AI-Powered Analysis

- "What are the key findings in this notebook?"
- "Summarize the main arguments across all these sources"
- "What does this source say about security best practices?"
- "Get an AI summary of what this notebook is about"
- "Configure the chat to use a learning guide style with longer responses"

### Content Generation

- "Create an audio podcast overview of this notebook in deep dive format"
- "Generate a video explainer with classic visual style"
- "Make a briefing doc from these sources"
- "Create flashcards for studying, medium difficulty"
- "Generate an infographic in landscape orientation"
- "Build a mind map from my research sources"
- "Create a slide deck presentation from this notebook"

### Smart Management

- "Check which Google Drive sources are out of date and sync them"
- "Show me all the sources in this notebook with their freshness status"
- "Delete this source from the notebook"
- "Check the status of my audio overview generation"

**Pro tip:** After creating studio content (audio, video, reports, etc.), poll the status to get download URLs when generation completes.

## Authentication Lifecycle

| Component | Duration | Refresh |
|-----------|----------|---------|
| Cookies | ~2-4 weeks | Re-extract from Chrome when expired |
| CSRF Token | Per MCP session | Auto-extracted on MCP start |
| Session ID | Per MCP session | Auto-extracted on MCP start |

When cookies expire, you'll see an auth error. Just extract fresh cookies and call `save_auth_tokens()` again.

## Troubleshooting

### Chrome DevTools MCP Not Working (Cursor/Gemini CLI)

If Chrome DevTools MCP shows "no tools, prompts or resources" or fails to start, it's likely due to a known `npx` bug with the puppeteer-core module.

**Symptoms:**
- Cursor/Gemini CLI shows MCP as connected but with "No tools, prompts, or resources"
- Process spawn errors in logs: `spawn pnpx ENOENT` or module not found errors
- Can't extract cookies for NotebookLM authentication

**Fix:**

1. **Install pnpm** (if not already installed):
   ```bash
   npm install -g pnpm
   ```

2. **Update Chrome DevTools MCP configuration:**

   **For Cursor** (`~/.cursor/mcp.json`):
   ```json
   "chrome-devtools": {
     "command": "pnpm",
     "args": ["dlx", "chrome-devtools-mcp@latest", "--browser-url=http://127.0.0.1:9222"]
   }
   ```

   **For Gemini CLI** (`~/.gemini/settings.json`):
   ```json
   "chrome-devtools": {
     "command": "pnpm",
     "args": ["dlx", "chrome-devtools-mcp@latest"]
   }
   ```

3. **Restart your IDE/CLI** for changes to take effect.

**Why this happens:** Chrome DevTools MCP uses `puppeteer-core` which changed its module path in v23+, but `npx` caching behavior causes module resolution failures. Using `pnpm dlx` avoids this issue.

**Related Issues:**
- [ChromeDevTools/chrome-devtools-mcp#160](https://github.com/ChromeDevTools/chrome-devtools-mcp/issues/160)
- [ChromeDevTools/chrome-devtools-mcp#111](https://github.com/ChromeDevTools/chrome-devtools-mcp/issues/111)
- [ChromeDevTools/chrome-devtools-mcp#221](https://github.com/ChromeDevTools/chrome-devtools-mcp/issues/221)

## Limitations

- **Rate limits**: Free tier has ~50 queries/day
- **No official support**: API may change without notice
- **Cookie expiration**: Need to re-extract cookies every few weeks

## Contributing

See [CLAUDE.md](CLAUDE.md) for detailed API documentation and how to add new features.

## Vibe Coding Alert

Full transparency: this project was built by a non-developer using AI coding assistants. If you're an experienced Python developer, you might look at this codebase and wince. That's okay.

The goal here was to scratch an itch - programmatic access to NotebookLM - and learn along the way. The code works, but it's likely missing patterns, optimizations, or elegance that only years of experience can provide.

**This is where you come in.** If you see something that makes you cringe, please consider contributing rather than just closing the tab. This is open source specifically because human expertise is irreplaceable. Whether it's refactoring, better error handling, type hints, or architectural guidance - PRs and issues are welcome.

Think of it as a chance to mentor an AI-assisted developer through code review. We all benefit when experienced developers share their knowledge.

## License

MIT License


---

## META.yaml

```yaml
# Project metadata for C021_notebooklm-mcp
# Auto-generated by Claude - agents should keep this current

project:
  last_reviewed: 2026-01-10
  summary: "NotebookLM MCP Server - Programmatic access to NotebookLM via reverse-engineered APIs"
  status: active
  series: C
  version: "0.1.0"

folders:
  00_admin: "Administrative files, audit exceptions"
  00_run: "C010 compliance placeholder"
  10_docs: "Documentation (working agreements)"
  20_receipts: "Change receipts per Betty Protocol"
  docs: "Reference documentation (API, troubleshooting, test plans)"
  skills: "Claude Code skills (doc-refresh)"
  src/notebooklm_mcp: "Core Python package"
  src/notebooklm_mcp/doc_refresh: "Doc-refresh Ralph loop module"
  tests: "Test suite"

files:
  pyproject.toml: "Python project config (uv/hatch)"
  README.md: "User documentation and setup guide"
  CLAUDE.md: "Claude Code session guidance"

executables:
  notebooklm-mcp: "MCP server entry point"
  notebooklm-mcp-auth: "CLI for Chrome-based auth token extraction"

relates_to:
  - C017_brain-on-tap: "Test target for doc-refresh; has NotebookLM notebook"
  - MCP_DOCKER: "Gateway that hosts this MCP server"

maintainer_notes:
  - "v0.1: Core MCP server with 31 tools, auth caching, doc-refresh loop"
  - "Uses reverse-engineered NotebookLM internal APIs (batchexecute)"
  - "Auth requires cookies from Chrome DevTools; CSRF/session auto-extracted"
  - "Free tier: ~25 API calls before cookie rotation, ~50 queries/day limit"
  - "Doc-refresh syncs canonical docs to NotebookLM + refreshes Standard 7 artifacts"

```

---

## CLAUDE.md

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## SESSION RECOVERY (Read First After Compaction)

**If you just resumed from context compaction and NotebookLM tools are failing:**

1. **Quick health check**: `notebook_list()` - if returns 0 notebooks, auth is dead
2. **Auth refresh**: User must run `notebooklm-mcp-auth` in terminal, then restart Claude Code
3. **Verify recovery**: `notebook_list()` should return notebooks again

**Auth dies after ~25 API calls on free tier.** The client has auto-retry logic, but if cookies fully expire, manual refresh is needed.

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

### Token Expiration

- **Cookies**: Stable for weeks, but some rotate on each request
- **CSRF token**: Auto-refreshed on each client initialization
- **Session ID**: Auto-refreshed on each client initialization

When API calls fail with auth errors, re-extract fresh cookies from Chrome DevTools.

## Architecture

```
src/notebooklm_mcp/
├── __init__.py      # Package version
├── server.py        # FastMCP server with tool definitions
├── api_client.py    # Internal API client (reverse-engineered)
├── auth.py          # Token caching and validation
└── auth_cli.py      # CLI for Chrome-based auth (notebooklm-mcp-auth)
```

**Executables:**
- `notebooklm-mcp` - The MCP server
- `notebooklm-mcp-auth` - CLI for extracting tokens (requires closing Chrome)

## MCP Tools Provided

| Tool | Purpose |
|------|---------|
| `notebook_list` | List all notebooks |
| `notebook_create` | Create new notebook |
| `notebook_get` | Get notebook details |
| `notebook_describe` | Get AI-generated summary of notebook content with keywords |
| `source_describe` | Get AI-generated summary and keyword chips for a source |
| `notebook_rename` | Rename a notebook |
| `chat_configure` | Configure chat goal/style and response length |
| `notebook_delete` | Delete a notebook (REQUIRES confirmation) |
| `notebook_add_url` | Add URL/YouTube source |
| `notebook_add_text` | Add pasted text source |
| `notebook_add_drive` | Add Google Drive source |
| `notebook_query` | Ask questions (AI answers!) |
| `source_list_drive` | List sources with types, check Drive freshness |
| `source_sync_drive` | Sync stale Drive sources (REQUIRES confirmation) |
| `source_delete` | Delete a source from notebook (REQUIRES confirmation) |
| `research_start` | Start Web or Drive research to discover sources |
| `research_status` | Check research progress and get results |
| `research_import` | Import discovered sources into notebook |
| `audio_overview_create` | Generate audio podcasts (REQUIRES confirmation) |
| `video_overview_create` | Generate video overviews (REQUIRES confirmation) |
| `infographic_create` | Generate infographics (REQUIRES confirmation) |
| `slide_deck_create` | Generate slide decks (REQUIRES confirmation) |
| `report_create` | Generate reports - Briefing Doc, Study Guide, Blog Post, Custom (REQUIRES confirmation) |
| `flashcards_create` | Generate flashcards with difficulty options (REQUIRES confirmation) |
| `quiz_create` | Generate interactive quizzes (REQUIRES confirmation) |
| `data_table_create` | Generate data tables from sources (REQUIRES confirmation) |
| `mind_map_create` | Generate and save mind maps (REQUIRES confirmation) |
| `mind_map_list` | List all mind maps in a notebook |
| `studio_status` | Check studio artifact generation status |
| `studio_delete` | Delete studio artifacts (REQUIRES confirmation) |
| `save_auth_tokens` | Save tokens extracted via Chrome DevTools MCP |

**IMPORTANT - Operations Requiring Confirmation:**
- `notebook_delete` requires `confirm=True` - deletion is IRREVERSIBLE
- `source_delete` requires `confirm=True` - deletion is IRREVERSIBLE
- `source_sync_drive` requires `confirm=True` - always show stale sources first via `source_list_drive`
- All studio creation tools require `confirm=True` - show settings and get user approval first
- `studio_delete` requires `confirm=True` - list artifacts first via `studio_status`, deletion is IRREVERSIBLE

## Features NOT Yet Implemented

- [ ] **Notes** - Save chat responses as notes
- [ ] **Share notebook** - Collaboration features
- [ ] **Export** - Download content

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

**[docs/MCP_TEST_PLAN.md](./docs/MCP_TEST_PLAN.md)**

This includes:
- Step-by-step test cases for all 31 MCP tools
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
4. Update the api_client.py with the new method
5. Add corresponding tool in server.py
6. Update the "Features NOT Yet Implemented" checklist
7. Add test case to docs/MCP_TEST_PLAN.md

## License

MIT License


---

## Standards Snapshot (C010)

This repo follows workspace standards from C010_standards:

- **Betty Protocol**: Evidence in 20_receipts/, no self-certification
- **META.yaml**: Keep `last_reviewed` current
- **Cross-platform**: Commands work on macOS, Windows, Linux
- **Closeout**: Git status clean, stash triaged, receipts written

Full standards are canonical in C010_standards.
