# PROJECT PRIMER — C021_notebooklm-mcp

## Provenance

- **Generated**: 2026-01-24 18:49
- **Repo SHA**: 5ed058c
- **Generator**: generate-project-primer v1.0.0
- **Source Docs**:
  - README.md
  - CHANGELOG.md
  - META.yaml
  - CLAUDE.md
  - docs/notebooklm_mcp/OVERVIEW.md
  - docs/notebooklm_mcp/QUICKSTART.md
  - docs/notebooklm_mcp/ARCHITECTURE.md
  - docs/notebooklm_mcp/CODE_TOUR.md
  - docs/notebooklm_mcp/OPERATIONS.md
  - docs/notebooklm_mcp/SECURITY_AND_PRIVACY.md
  - docs/notebooklm_mcp/OPEN_QUESTIONS.md
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
| **Tier** | kitted |
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
| Find code | Code Tour |
| Understand architecture | Architecture |
| Security rules | Security & Privacy |
| Current roadmap | Open Questions |

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

# Remove sync config and receipts (optional)
rm -rf ~/.config/notebooklm-mcp
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

## Using notebooklm-sync CLI

The `notebooklm-sync` command provides deterministic document syncing with receipts and idempotence tracking.

### Features

- **Idempotence**: Uses SHA256 hashes to skip unchanged files
- **Tier 3 auto-discovery**: Finds README.md, CLAUDE.md, docs/*.md automatically
- **Sync receipts**: JSON audit trail in `~/.config/notebooklm-mcp/sync_receipts/`
- **Audio generation**: Optional podcast creation after sync

### Usage Examples

```bash
# List existing notebooks
notebooklm-sync --list

# Sync Tier 3 docs from a repo (auto-discovers docs)
notebooklm-sync --repo C012_round-table --tier3

# Sync with audio overview generation
notebooklm-sync --repo C012_round-table --tier3 --audio

# Non-interactive mode (skip confirmation prompts)
notebooklm-sync --repo C012_round-table --tier3 --audio --yes

# Sync specific files to a named notebook
notebooklm-sync "My Research" docs/*.md

# With custom audio focus
notebooklm-sync --repo C012_round-table --tier3 --audio --focus "Explain the architecture"
```

### Configuration Files

| Path | Purpose |
|------|---------|
| `~/.config/notebooklm-mcp/notebook_map.yaml` | Repo-to-notebook mappings |
| `~/.config/notebooklm-mcp/sync_receipts/` | JSON audit trail for each sync |

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
├── auth_cli.py      # CLI for Chrome-based auth (notebooklm-mcp-auth)
└── sync_cli.py      # CLI for deterministic doc sync (notebooklm-sync)
```

**Executables:**
- `notebooklm-mcp` - The MCP server
- `notebooklm-mcp-auth` - CLI for extracting tokens (requires closing Chrome)
- `notebooklm-sync` - CLI for deterministic doc syncing with receipts

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
```

**Key features:**
- **Idempotence**: SHA256 hashes skip unchanged files
- **Cross-notebook safety**: Uses mapped notebook_id to prevent accidental source deletion
- **Receipts**: JSON audit trail with timestamps, actions, and source IDs

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
| Sync deletes wrong sources | notebook_map has stale notebook_id | Delete entry from `notebook_map.yaml` |
| Sync receipts not found | Config dir issue | Check `~/.config/notebooklm-mcp/sync_receipts/` |
| Tier 3 discovery missing files | Non-standard structure | Use explicit file paths instead |

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

## Overview

**Last Updated**: 2026-01-10
**Version**: 0.1.0

## What Is NotebookLM MCP?

NotebookLM MCP Server provides **programmatic access to Google NotebookLM** via the Model Context Protocol (MCP). It enables AI assistants like Claude Code, Cursor, and Gemini CLI to create notebooks, add sources, ask questions, and generate studio artifacts (audio, video, infographics, etc.).

## Ecosystem Position

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         WEBCORE ECOSYSTEM                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  AI Assistants                                                          │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐           │
│  │ Claude    │  │ Cursor    │  │ Gemini    │  │ Others    │           │
│  │ Code      │  │           │  │ CLI       │  │           │           │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘           │
│        │              │              │              │                   │
│        └──────────────┴──────────────┴──────────────┘                   │
│                              │                                          │
│                              ▼                                          │
│                    ┌─────────────────────┐                              │
│                    │ NotebookLM MCP      │                              │
│                    │ Server (C021)       │                              │
│                    │ • 31 MCP Tools      │                              │
│                    │ • Cookie-based Auth │                              │
│                    └──────────┬──────────┘                              │
│                              │                                          │
│                              ▼                                          │
│                    ┌─────────────────────┐                              │
│                    │ NotebookLM          │                              │
│                    │ (Google)            │                              │
│                    │ Internal APIs       │                              │
│                    └─────────────────────┘                              │
│                                                                         │
│  Downstream Consumers                                                   │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  • C017 Brain-on-Tap: NotebookLM as memory/research layer        │ │
│  │  • C003 SADB: Documentation hub notebooks                        │ │
│  │  • Doc-refresh loop: Syncs repo docs to NotebookLM               │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

## Core Components

| Component | Purpose | Location |
|-----------|---------|----------|
| **MCP Server** | FastMCP server with 31 tools | `src/notebooklm_mcp/server.py` |
| **API Client** | Reverse-engineered NotebookLM API | `src/notebooklm_mcp/api_client.py` |
| **Auth System** | Cookie extraction and caching | `src/notebooklm_mcp/auth.py` |
| **Auth CLI** | Chrome-based token extraction | `src/notebooklm_mcp/auth_cli.py` |
| **Doc-Refresh** | Ralph loop for doc sync | `src/notebooklm_mcp/doc_refresh/` |

## Key Capabilities

### 1. Notebook Management
- Create, list, rename, delete notebooks
- Get notebook details with source information
- AI-generated notebook summaries

### 2. Source Management
- Add URLs (web pages, YouTube videos)
- Add pasted text as sources
- Add Google Drive documents
- Sync stale Drive sources
- Delete sources

### 3. AI Queries
- Ask questions against notebook sources
- Maintain conversation context
- Configure chat style (learning guide, custom)

### 4. Studio Content Generation
- **Audio**: Deep dive, brief, critique, debate formats
- **Video**: Explainer and brief formats with visual styles
- **Reports**: Briefing Doc, Study Guide, Blog Post, custom
- **Visual**: Infographics, slide decks, mind maps
- **Learning**: Flashcards, quizzes, data tables

### 5. Research Discovery
- Web research with fast/deep modes
- Drive research for document discovery
- Import discovered sources into notebooks

## Operating Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| **MCP Server** | `notebooklm-mcp` command | Integration with AI assistants |
| **Auth CLI** | `notebooklm-mcp-auth` | Token extraction from Chrome |
| **Development** | `uv run pytest` | Testing and development |

## Integration Points

| System | Integration Type | Status |
|--------|-----------------|--------|
| Claude Code | MCP client | Active |
| Cursor | MCP client | Active |
| Gemini CLI | MCP client | Active |
| MCP_DOCKER | Gateway host | Active |
| C017 Brain-on-Tap | Research notebooks | Active |

## Important Disclaimer

This MCP uses **reverse-engineered internal APIs** that:
- Are undocumented and may change without notice
- Require cookie extraction from your browser
- Have rate limits (~50 queries/day on free tier)

Use at your own risk for personal/experimental purposes.

## Why NotebookLM MCP?

- **Programmatic access** to NotebookLM's AI features
- **Batch operations** for notebook management
- **Integration** with AI coding assistants
- **Automation** of research and content generation workflows

## Related Documentation

- [QUICKSTART.md](QUICKSTART.md) - Get running in 5 minutes
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design details
- [OPERATIONS.md](OPERATIONS.md) - Day-to-day operation


---

## Quickstart

**Last Updated**: 2026-01-10
**Version**: 0.1.0

Get NotebookLM MCP running in 5 minutes.

## Prerequisites

- Python 3.11+
- Google Chrome installed
- NotebookLM account (free or Plus)

## Quick Start

### 1. Install the MCP Server

```bash
# Using uv (Recommended)
uv tool install notebooklm-mcp-server

# Or using pip
pip install notebooklm-mcp-server

# Or using pipx
pipx install notebooklm-mcp-server
```

### 2. Authenticate

```bash
# Close Chrome completely first (Cmd+Q on Mac)
notebooklm-mcp-auth
```

A Chrome window opens. Log in to your Google account, then wait for "SUCCESS!".

### 3. Add to Your AI Tool

**Claude Code (Recommended):**
```bash
claude mcp add --scope user notebooklm-mcp notebooklm-mcp
```

**Gemini CLI:**
```bash
gemini mcp add --scope user notebooklm-mcp notebooklm-mcp
```

**Cursor/VS Code:** Add to config file (see [Configuration](#configuration)).

### 4. Restart Your AI Tool

Restart Claude Code, Cursor, or Gemini CLI to load the MCP.

### 5. Verify Installation

Ask your AI assistant:
```
List all my NotebookLM notebooks
```

You should see your existing notebooks (or an empty list if you have none).

## Configuration

### Claude Code

```bash
# Add for all projects
claude mcp add --scope user notebooklm-mcp notebooklm-mcp

# Verify
claude mcp list
```

### Cursor / VS Code

Find your path:
```bash
which notebooklm-mcp
```

Add to `~/.cursor/mcp.json` or `~/.vscode/mcp.json`:
```json
{
  "mcpServers": {
    "notebooklm-mcp": {
      "command": "/path/from/which/command/notebooklm-mcp"
    }
  }
}
```

### Gemini CLI

```bash
gemini mcp add --scope user notebooklm-mcp notebooklm-mcp
```

## First Operations

### List Notebooks
```
List all my NotebookLM notebooks
```

### Create a Notebook
```
Create a new notebook called "My Research Project"
```

### Add a Source
```
Add this URL to my notebook: https://example.com/article
```

### Ask a Question
```
What are the key findings in my research notebook?
```

### Generate Audio
```
Create an audio overview of my notebook in deep dive format
```

## Context Window Warning

This MCP provides **31 tools** which consume context window space. Recommendations:

- **Disable when not using NotebookLM** to preserve context
- **Claude Code**: Use `@notebooklm-mcp` to toggle on/off
- **Other tools**: Comment out server in config when not needed

## Troubleshooting

### Auth Fails
```bash
# Close Chrome completely (Cmd+Q on Mac)
notebooklm-mcp-auth
```

### "0 notebooks" Returned
Your auth tokens expired. Re-run `notebooklm-mcp-auth` and restart your AI tool.

### MCP Not Found
Verify installation:
```bash
which notebooklm-mcp
notebooklm-mcp --help
```

### Chrome Won't Close
Use file mode for manual cookie extraction:
```bash
notebooklm-mcp-auth --file
```

## Upgrading

```bash
# Using uv
uv tool upgrade notebooklm-mcp-server

# Using pip
pip install --upgrade notebooklm-mcp-server
```

After upgrading, restart your AI tool.

## Next Steps

- [OPERATIONS.md](OPERATIONS.md) - Day-to-day workflows
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [CODE_TOUR.md](CODE_TOUR.md) - Navigate the codebase
- [../TROUBLESHOOTING.md](../TROUBLESHOOTING.md) - Detailed troubleshooting


---

## Architecture

**Last Updated**: 2026-01-10
**Version**: 0.1.0

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      NotebookLM MCP Server                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                       MCP Layer                                   │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │  │
│  │  │ FastMCP     │  │ Tool        │  │ Resource    │              │  │
│  │  │ Server      │  │ Definitions │  │ Handlers    │              │  │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │  │
│  │         │                │                │                      │  │
│  │         └────────────────┴────────────────┘                      │  │
│  │                          │                                        │  │
│  │                   server.py (31 tools)                           │  │
│  └──────────────────────────┼────────────────────────────────────────┘  │
│                             │                                           │
│  ┌──────────────────────────┼────────────────────────────────────────┐  │
│  │                    API Layer                                      │  │
│  │                                                                   │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │  │
│  │  │ HTTP Client │  │ RPC Builder │  │ Response    │              │  │
│  │  │ (httpx)     │  │             │  │ Parser      │              │  │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │  │
│  │         │                │                │                      │  │
│  │         └────────────────┴────────────────┘                      │  │
│  │                          │                                        │  │
│  │                   api_client.py                                   │  │
│  └──────────────────────────┼────────────────────────────────────────┘  │
│                             │                                           │
│  ┌──────────────────────────┼────────────────────────────────────────┐  │
│  │                    Auth Layer                                     │  │
│  │                                                                   │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │  │
│  │  │ Token Cache │  │ Cookie      │  │ CSRF/Session│              │  │
│  │  │ (JSON file) │  │ Parser      │  │ Extractor   │              │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘              │  │
│  │                                                                   │  │
│  │                   auth.py + auth_cli.py                          │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │ NotebookLM Internal API │
                    │ (batchexecute endpoint) │
                    └─────────────────────────┘
```

## Core Principles

1. **Reverse-engineered API**: Uses undocumented internal batchexecute RPC endpoints
2. **Cookie-based auth**: Browser cookies for authentication (no official API)
3. **Auto-extraction**: CSRF tokens and session IDs auto-extracted on init
4. **Confirmation patterns**: Destructive operations require explicit `confirm=True`
5. **Token-efficient responses**: Compact output for MCP tool results

## Component Details

### MCP Server (`server.py`)

FastMCP server providing 31 tools across categories:

| Category | Tools |
|----------|-------|
| Notebook Management | `notebook_list`, `notebook_create`, `notebook_get`, `notebook_describe`, `notebook_rename`, `notebook_delete` |
| Source Management | `notebook_add_url`, `notebook_add_text`, `notebook_add_drive`, `source_describe`, `source_list_drive`, `source_sync_drive`, `source_delete` |
| AI Queries | `notebook_query`, `chat_configure` |
| Research | `research_start`, `research_status`, `research_import` |
| Studio Content | `audio_overview_create`, `video_overview_create`, `infographic_create`, `slide_deck_create`, `report_create`, `flashcards_create`, `quiz_create`, `data_table_create`, `mind_map_create`, `mind_map_list`, `studio_status`, `studio_delete` |
| Auth | `save_auth_tokens` |

### API Client (`api_client.py`)

Reverse-engineered HTTP client for NotebookLM internal APIs:

**Key Methods:**
```python
# Notebook operations
list_notebooks() -> List[dict]
create_notebook(title) -> dict
get_notebook(notebook_id) -> dict
delete_notebook(notebook_id) -> bool

# Source operations
add_url_source(notebook_id, url) -> dict
add_text_source(notebook_id, text, title) -> dict
add_drive_source(notebook_id, doc_id, title, doc_type) -> dict

# Query operations
query_notebook(notebook_id, query, source_ids, conversation_id) -> dict

# Studio operations
create_audio_overview(notebook_id, format, length, ...) -> dict
create_video_overview(notebook_id, format, style, ...) -> dict
get_studio_status(notebook_id) -> dict
```

**RPC Protocol:**
- Endpoint: `https://notebooklm.google.com/v1alpha1/batchexecute`
- Format: Nested array structures with RPC IDs
- Response: Multi-part batchexecute response parsing

### Auth System (`auth.py`, `auth_cli.py`)

**Token Storage:**
```
~/.notebooklm-mcp/
├── auth.json           # Cached cookies, CSRF, session ID
└── chrome-profile/     # Dedicated Chrome profile for auth
```

**Token Lifecycle:**
| Token | Duration | Refresh |
|-------|----------|---------|
| Cookies | ~2-4 weeks | Re-extract from Chrome |
| CSRF | Per session | Auto-extracted on init |
| Session ID | Per session | Auto-extracted on init |

**Auth CLI Modes:**
- **Auto mode** (default): Launches Chrome, user logs in, cookies extracted
- **File mode** (`--file`): Manual cookie extraction from DevTools

## Data Flow

### Tool Call Flow
```
AI Assistant → MCP Protocol → FastMCP Server
                                   │
                                   ▼
                            Tool Handler
                                   │
                                   ▼
                            API Client Method
                                   │
                                   ▼
                            Build RPC Request
                                   │
                                   ▼
                            HTTP POST (batchexecute)
                                   │
                                   ▼
                            Parse Response
                                   │
                                   ▼
                            Return to Tool Handler
                                   │
                                   ▼
                            Format MCP Response
```

### Auth Flow
```
notebooklm-mcp-auth
        │
        ▼
Launch Chrome (dedicated profile)
        │
        ▼
User logs in to Google
        │
        ▼
Navigate to NotebookLM
        │
        ▼
Extract cookies via CDP
        │
        ▼
Parse CSRF token from page
        │
        ▼
Save to ~/.notebooklm-mcp/auth.json
```

## Request/Response Format

### RPC Request Structure
```python
# Batchexecute request format
[
    [
        [
            "RPC_ID",           # e.g., "wJbB3c" for list notebooks
            json.dumps(params), # Nested parameter array
            None,
            "generic"
        ]
    ]
]
```

### Response Parsing
```python
# Batchexecute response format
)]}'  # Security prefix (stripped)

[[["wrb.fr","RPC_ID","[nested_json_array]",null,null,null,"generic"]]]
```

## Confirmation Pattern

Destructive operations require explicit confirmation:

```python
# Without confirmation - returns preview/warning
notebook_delete(notebook_id, confirm=False)
# Returns: {"status": "confirm_required", "message": "..."}

# With confirmation - executes operation
notebook_delete(notebook_id, confirm=True)
# Returns: {"status": "success", ...}
```

**Operations requiring confirmation:**
- `notebook_delete`
- `source_delete`
- `source_sync_drive`
- All studio creation tools
- `studio_delete`

## Integration Points

| Component | Purpose |
|-----------|---------|
| FastMCP | MCP server framework |
| httpx | Async HTTP client |
| Chrome CDP | Cookie extraction (auth CLI) |
| Selenium | Browser automation (auth CLI) |

## Related Documentation

- [CODE_TOUR.md](CODE_TOUR.md) - Navigate the codebase
- [OPERATIONS.md](OPERATIONS.md) - Day-to-day operation
- [../API_REFERENCE.md](../API_REFERENCE.md) - Detailed API documentation


---

## Code Tour

**Last Updated**: 2026-01-10
**Version**: 0.1.0

Navigate the C021 codebase efficiently.

## Quick Reference

| I want to... | Look at... |
|--------------|------------|
| Add a new MCP tool | `src/notebooklm_mcp/server.py` |
| Add a new API method | `src/notebooklm_mcp/api_client.py` |
| Fix auth issues | `src/notebooklm_mcp/auth.py` |
| Modify auth CLI | `src/notebooklm_mcp/auth_cli.py` |
| Understand API format | `docs/API_REFERENCE.md` |
| Test tools | `docs/MCP_TEST_PLAN.md` |
| Debug issues | `docs/TROUBLESHOOTING.md` |

## Directory Map

```
C021_notebooklm-mcp/
├── src/notebooklm_mcp/           # Core Python package
│   ├── __init__.py               # Package version (0.1.0)
│   ├── server.py                 # FastMCP server (31 tools)
│   ├── api_client.py             # NotebookLM API client (~110KB)
│   ├── auth.py                   # Token caching/validation
│   ├── auth_cli.py               # Chrome-based auth CLI
│   └── doc_refresh/              # Doc-refresh Ralph loop module
│       ├── __init__.py
│       ├── canonical_docs.yaml   # Tiered doc manifest
│       ├── notebook_map.yaml     # Repo → Notebook mapping
│       └── PROMPT.md             # Ralph loop prompt
│
├── docs/                         # Reference documentation
│   ├── API_REFERENCE.md          # Reverse-engineered API details
│   ├── AUTHENTICATION.md         # Auth guide
│   ├── TROUBLESHOOTING.md        # Common issues
│   ├── MCP_TEST_PLAN.md          # Tool test cases
│   ├── KNOWN_ISSUES.md           # Known bugs
│   ├── media/                    # Images (header.jpeg)
│   └── doc_refresh/              # Doc-refresh epic docs
│       ├── EPIC.md
│       ├── INTERFACES.md
│       └── PHASE_*.md
│
├── skills/                       # Claude Code skills
│   └── doc-refresh/
│       └── skill.md              # /doc-refresh command
│
├── tests/                        # Test suite
│   └── test_*.py                 # Pytest tests
│
├── 00_admin/                     # Administrative (audit exceptions)
├── 10_docs/                      # Working agreements
├── 20_receipts/                  # Betty Protocol receipts
│
├── pyproject.toml                # Python project config (uv/hatch)
├── README.md                     # User documentation
├── CLAUDE.md                     # Claude Code guidance
├── META.yaml                     # Project metadata
└── CHANGELOG.md                  # Version history
```

## Key Entry Points

### MCP Server (`src/notebooklm_mcp/server.py`)

```python
# FastMCP server initialization
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("notebooklm-mcp")

# Tool definition example
@mcp.tool()
async def notebook_list(
    max_results: int = 100,
    compact: bool = True
) -> dict:
    """List all notebooks."""
    client = get_client()
    notebooks = await client.list_notebooks()
    return format_response(notebooks, compact)
```

### API Client (`src/notebooklm_mcp/api_client.py`)

```python
# Batchexecute RPC call
async def _make_request(self, rpc_id: str, params: list) -> dict:
    """Make a batchexecute RPC request."""
    data = {
        "f.req": json.dumps([[[rpc_id, json.dumps(params), None, "generic"]]])
    }
    response = await self.client.post(BATCHEXECUTE_URL, data=data)
    return self._parse_response(response.text)

# Example method
async def list_notebooks(self) -> list:
    """List all notebooks."""
    return await self._make_request("wJbB3c", [])
```

### Auth System (`src/notebooklm_mcp/auth.py`)

```python
# Token cache location
AUTH_FILE = Path.home() / ".notebooklm-mcp" / "auth.json"

# Load cached tokens
def load_auth() -> dict:
    """Load cached auth tokens."""
    if AUTH_FILE.exists():
        return json.loads(AUTH_FILE.read_text())
    return {}

# Auto-extract CSRF from page
async def extract_csrf_token(page_content: str) -> str:
    """Extract CSRF token from NotebookLM page."""
    # Parse HTML for token
```

### Auth CLI (`src/notebooklm_mcp/auth_cli.py`)

```python
# Entry point
def main():
    """notebooklm-mcp-auth CLI entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", nargs="?", const=True)
    args = parser.parse_args()

    if args.file:
        file_mode(args.file)
    else:
        auto_mode()
```

## Configuration

### Package Version (`src/notebooklm_mcp/__init__.py`)

```python
__version__ = "0.1.0"
```

### Project Config (`pyproject.toml`)

```toml
[project]
name = "notebooklm-mcp-server"
version = "0.1.0"
requires-python = ">=3.11"

[project.scripts]
notebooklm-mcp = "notebooklm_mcp.server:main"
notebooklm-mcp-auth = "notebooklm_mcp.auth_cli:main"
```

## Common Patterns

### Adding a New MCP Tool

1. **Add API method** in `api_client.py`:
```python
async def new_feature(self, notebook_id: str, param: str) -> dict:
    return await self._make_request("RPC_ID", [notebook_id, param])
```

2. **Add tool** in `server.py`:
```python
@mcp.tool()
async def new_feature(notebook_id: str, param: str) -> dict:
    """Tool description."""
    client = get_client()
    return await client.new_feature(notebook_id, param)
```

3. **Document RPC ID** in `docs/API_REFERENCE.md`
4. **Add test case** in `docs/MCP_TEST_PLAN.md`

### Confirmation Pattern

```python
@mcp.tool()
async def dangerous_operation(
    notebook_id: str,
    confirm: bool = False
) -> dict:
    """Operation requiring confirmation."""
    if not confirm:
        return {
            "status": "confirm_required",
            "message": "Set confirm=True to proceed"
        }

    client = get_client()
    return await client.dangerous_operation(notebook_id)
```

### Response Formatting

```python
def format_notebook(notebook: dict, compact: bool) -> dict:
    """Format notebook for MCP response."""
    if compact:
        return {
            "id": notebook["id"],
            "title": notebook["title"],
            "source_count": len(notebook.get("sources", []))
        }
    return notebook  # Full details
```

## Development Commands

```bash
# Install for development
uv tool install .

# Reinstall after changes (always clean cache!)
uv cache clean && uv tool install --force .

# Run tests
uv run pytest

# Run single test
uv run pytest tests/test_file.py::test_function -v
```

## Test Files

| Test File | Coverage |
|-----------|----------|
| `tests/test_*.py` | Unit tests for modules |
| `docs/MCP_TEST_PLAN.md` | Manual integration tests |

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [OPERATIONS.md](OPERATIONS.md) - Day-to-day operation
- [../API_REFERENCE.md](../API_REFERENCE.md) - API details
- [../MCP_TEST_PLAN.md](../MCP_TEST_PLAN.md) - Test cases


---

## Operations

**Last Updated**: 2026-01-10
**Version**: 0.1.0

Day-to-day operation of the NotebookLM MCP Server.

## Operating Modes

### MCP Server Mode (Primary)

The MCP server runs as a subprocess of your AI assistant:

```bash
# Runs automatically when AI tool starts
notebooklm-mcp
```

You don't typically run this directly - your AI tool manages it.

### Auth CLI Mode

For extracting authentication tokens:

```bash
# Auto mode (recommended)
notebooklm-mcp-auth

# File mode (manual cookie extraction)
notebooklm-mcp-auth --file
```

### Development Mode

For testing and development:

```bash
# Activate environment
cd ~/SyncedProjects/C021_notebooklm-mcp

# Install from source
uv tool install .

# Run tests
uv run pytest

# Reinstall after changes
uv cache clean && uv tool install --force .
```

## Daily Workflows

### Session Startup

1. **Start AI tool** (Claude Code, Cursor, Gemini CLI)
2. **Verify MCP connection**: Ask "List my NotebookLM notebooks"
3. **If 0 notebooks returned**: Auth is dead, run recovery

### Auth Health Check

```
List all my NotebookLM notebooks
```

| Result | Status |
|--------|--------|
| Returns your notebooks | Auth working |
| Returns 0 notebooks | Auth dead - needs refresh |
| Error message | Check troubleshooting |

### Auth Recovery

When auth dies:

```bash
# 1. Close Chrome completely (Cmd+Q on Mac)

# 2. Run auth refresh
notebooklm-mcp-auth

# 3. Wait for "SUCCESS!" message

# 4. Restart your AI tool

# 5. Verify: "List my NotebookLM notebooks"
```

### Common Operations

**Create a notebook:**
```
Create a new notebook called "Project Research"
```

**Add sources:**
```
Add this URL to my notebook: https://example.com/article
Add this YouTube video to my notebook: https://youtube.com/watch?v=xxx
```

**Query notebook:**
```
What are the key findings in my research notebook?
```

**Generate content:**
```
Create an audio overview of my notebook in deep dive format
Generate a briefing doc from my sources
Create flashcards from this notebook, medium difficulty
```

**Check studio status:**
```
Check the status of my audio overview generation
```

## Context Window Management

This MCP provides **31 tools** - significant context consumption.

### Claude Code

```bash
# Toggle MCP on/off
@notebooklm-mcp

# Or use /mcp command
/mcp
```

### Cursor/Other Tools

- Comment out server in config when not needed
- Uncomment when ready to use NotebookLM

## Rate Limits

| Tier | Daily Queries | Cookie Rotation |
|------|---------------|-----------------|
| Free | ~50 | After ~20-30 calls |
| Plus | Higher | Less frequent |

### Mitigation Strategies

- Batch related operations together
- Check auth health before long operations
- Keep `notebooklm-mcp-auth` ready for quick refresh

## Troubleshooting Quick Reference

### Auth Issues

| Symptom | Fix |
|---------|-----|
| 0 notebooks returned | Run `notebooklm-mcp-auth`, restart AI tool |
| 401/403 errors | Run `notebooklm-mcp-auth`, restart AI tool |
| Auth CLI succeeds but API fails | Restart AI tool (tokens cached at startup) |

### Studio Issues

| Symptom | Fix |
|---------|-----|
| Video fails "No sources" | Retry the request |
| Mind maps not in studio_status | Use `mind_map_list()` instead |
| URLs null in studio_status | Still generating - poll again |

### Source Issues

| Symptom | Fix |
|---------|-----|
| source_sync_drive has no effect | Only works for Drive sources, not pasted text |
| Large text fails | Split into multiple sources (<50KB each) |

## MCP Tool Categories

### Information (Read-Only)

- `notebook_list` - List notebooks
- `notebook_get` - Get notebook details
- `notebook_describe` - AI-generated summary
- `source_describe` - Source summary
- `source_list_drive` - List sources with freshness
- `studio_status` - Check artifact status
- `mind_map_list` - List mind maps
- `research_status` - Check research progress

### Modification (Write)

- `notebook_create` - Create notebook
- `notebook_rename` - Rename notebook
- `notebook_add_url` - Add URL source
- `notebook_add_text` - Add text source
- `notebook_add_drive` - Add Drive source
- `notebook_query` - Ask questions
- `chat_configure` - Configure chat style
- `research_start` - Start research
- `research_import` - Import discovered sources

### Destructive (Require Confirmation)

- `notebook_delete` - Delete notebook
- `source_delete` - Delete source
- `source_sync_drive` - Sync Drive sources
- `audio_overview_create` - Generate audio
- `video_overview_create` - Generate video
- `infographic_create` - Generate infographic
- `slide_deck_create` - Generate slides
- `report_create` - Generate report
- `flashcards_create` - Generate flashcards
- `quiz_create` - Generate quiz
- `data_table_create` - Generate data table
- `mind_map_create` - Generate mind map
- `studio_delete` - Delete artifact

### Auth

- `save_auth_tokens` - Save tokens from Chrome DevTools MCP

## Log Locations

| Log | Location | Purpose |
|-----|----------|---------|
| Auth tokens | `~/.notebooklm-mcp/auth.json` | Cached credentials |
| Chrome profile | `~/.notebooklm-mcp/chrome-profile/` | Persistent login |
| MCP logs | AI tool's log output | Debug MCP issues |

## Upgrading

```bash
# Using uv
uv tool upgrade notebooklm-mcp-server

# Using pip
pip install --upgrade notebooklm-mcp-server

# Always restart AI tool after upgrade
```

## Related Documentation

- [QUICKSTART.md](QUICKSTART.md) - Initial setup
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [../TROUBLESHOOTING.md](../TROUBLESHOOTING.md) - Detailed troubleshooting
- [../AUTHENTICATION.md](../AUTHENTICATION.md) - Auth deep dive


---

## Security & Privacy

**Last Updated**: 2026-01-10
**Version**: 0.1.0

Security model and data protection for the NotebookLM MCP Server.

## Security Principles

1. **Local credential storage** - Auth tokens stored locally, not transmitted
2. **No credential logging** - Cookies never written to logs
3. **Dedicated Chrome profile** - Isolated from main browser profile
4. **Confirmation patterns** - Destructive operations require explicit confirmation

## Authentication Security

### Token Storage

| Token | Location | Permissions |
|-------|----------|-------------|
| Cookies | `~/.notebooklm-mcp/auth.json` | User-only (0600) |
| Chrome profile | `~/.notebooklm-mcp/chrome-profile/` | User-only (0700) |

### What Gets Stored

```json
// ~/.notebooklm-mcp/auth.json
{
  "cookies": "SID=...; HSID=...; ...",
  "csrf_token": "...",
  "session_id": "...",
  "extracted_at": "2026-01-10T12:00:00Z"
}
```

### What Stays Local

| Data | Stored Where | Synced Externally? |
|------|--------------|-------------------|
| Google cookies | `auth.json` | No |
| CSRF token | `auth.json` | No |
| Session ID | `auth.json` | No |
| Chrome profile | `chrome-profile/` | No |

## Network Security

### Connections Made

| Endpoint | Purpose | Auth Required |
|----------|---------|---------------|
| `notebooklm.google.com` | NotebookLM API | Yes (cookies) |
| `accounts.google.com` | OAuth (auth CLI only) | Interactive |

### No Proxy Support

Current implementation connects directly to Google services. Corporate proxies may require additional configuration.

## Data Privacy

### What Data is Sent to NotebookLM

| Data Type | When Sent |
|-----------|-----------|
| Notebook content | When adding sources |
| Queries | When using `notebook_query` |
| Studio requests | When generating content |

### What Data is Returned

| Data Type | Storage |
|-----------|---------|
| Notebook metadata | In-memory only |
| Source content | In-memory only |
| Generated content URLs | In-memory only |

**No MCP data is persisted locally** except auth tokens.

### Google's Data Handling

All notebook data is stored and processed by Google NotebookLM. Refer to:
- [NotebookLM Terms of Service](https://notebooklm.google.com/terms)
- [Google Privacy Policy](https://policies.google.com/privacy)

## Confirmation Pattern

Destructive operations require explicit `confirm=True`:

```python
# Without confirmation - safe preview
notebook_delete(notebook_id, confirm=False)
# Returns: {"status": "confirm_required", ...}

# With confirmation - executes delete
notebook_delete(notebook_id, confirm=True)
# Returns: {"status": "success", ...}
```

### Operations Requiring Confirmation

| Operation | Risk Level | Notes |
|-----------|------------|-------|
| `notebook_delete` | High | IRREVERSIBLE |
| `source_delete` | High | IRREVERSIBLE |
| `studio_delete` | High | IRREVERSIBLE |
| `source_sync_drive` | Medium | May update content |
| All studio creation | Medium | Uses API quota |

## Threat Model

### Mitigated Threats

| Threat | Mitigation |
|--------|------------|
| Credential theft | Local storage with user-only permissions |
| Accidental deletion | Confirmation pattern |
| Cookie leakage | Not logged, not synced |
| Profile contamination | Dedicated Chrome profile |

### Accepted Risks

| Risk | Acceptance Rationale |
|------|---------------------|
| Local file access | OS-level protection |
| Google sees data | Inherent to using NotebookLM |
| Cookie expiration | Auto-detection and user notification |
| API changes | Reverse-engineered API may break |

### Out of Scope

| Risk | Notes |
|------|-------|
| Google account security | User's responsibility |
| Network interception | HTTPS handled by Google |
| Memory inspection | Requires system access |

## Security Checklist

### Initial Setup

- [ ] Run `notebooklm-mcp-auth` to create dedicated profile
- [ ] Verify `~/.notebooklm-mcp/` has correct permissions (0700)
- [ ] Verify `auth.json` has correct permissions (0600)
- [ ] Ensure `auth.json` is not committed to version control

### Ongoing

- [ ] Don't share `auth.json` file
- [ ] Don't commit cookies to version control
- [ ] Re-authenticate when cookies expire
- [ ] Use separate Google account if needed for isolation

## Incident Response

### Suspected Credential Compromise

1. **Revoke Google session**: [Google Security Checkup](https://myaccount.google.com/security-checkup)
2. **Delete local tokens**: `rm -rf ~/.notebooklm-mcp/`
3. **Re-authenticate**: `notebooklm-mcp-auth`
4. **Monitor account**: Check for unauthorized notebook access

### Auth Token Leaked

1. **Invalidate session**: Sign out of all Google sessions
2. **Delete local tokens**: `rm ~/.notebooklm-mcp/auth.json`
3. **Change Google password** if concerned
4. **Re-authenticate**: `notebooklm-mcp-auth`

## Configuration

### File Permissions

```bash
# Verify permissions
ls -la ~/.notebooklm-mcp/

# Fix if needed
chmod 700 ~/.notebooklm-mcp/
chmod 600 ~/.notebooklm-mcp/auth.json
```

### Gitignore

The following should be in `.gitignore`:
```
auth.json
.notebooklm-mcp/
chrome-profile/
cookies.txt
```

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [OPERATIONS.md](OPERATIONS.md) - Day-to-day operation
- [../AUTHENTICATION.md](../AUTHENTICATION.md) - Auth details


---

## Open Questions

**Last Updated**: 2026-01-10
**Version**: 0.1.0

Unresolved decisions, known limitations, and future considerations.

## Architecture Questions

### Official API Support

**Current State**: Using reverse-engineered internal APIs

**Question**: Should we switch when/if Google releases an official NotebookLM API?

| Option | Pros | Cons |
|--------|------|------|
| Wait for official API | Stable, supported | Unknown timeline |
| Continue reverse-engineering | Works now | May break anytime |
| Hybrid approach | Best of both | More complexity |

**Current Approach**: Continue with reverse-engineered APIs, monitor for official API announcements.

### MCP Protocol Evolution

**Current State**: Using FastMCP framework

**Question**: How should we handle MCP protocol updates?

**Considerations**:
- FastMCP may update independently
- MCP spec may evolve
- Tool schemas may need updates

**Resolution**: Track FastMCP releases, update as needed.

### Multi-Account Support

**Current State**: Single Google account at a time

**Question**: Should we support multiple NotebookLM accounts?

**Options**:
- Multiple auth.json files with switching
- Account parameter per tool call
- Keep single account focus

**Resolution**: Single account for simplicity. Users can re-auth to switch.

## Known Limitations

### API Limitations

| Limitation | Impact | Workaround |
|------------|--------|------------|
| Rate limits (~50/day free) | Restricts heavy usage | Batch operations, upgrade to Plus |
| Cookie rotation | Auth dies mid-session | Keep auth CLI ready |
| No official API | May break anytime | Monitor for changes |
| 31 tools = large context | Consumes context window | Toggle MCP on/off |

### Feature Limitations

| Limitation | Impact | Workaround |
|------------|--------|------------|
| No Notes support | Can't save chat responses | Manual copy |
| No Sharing | Can't share via MCP | Use web UI |
| No Export | Can't download content | Use web UI |
| No audio playback | URL only | Open URL in browser |

### Studio Limitations

| Limitation | Impact | Workaround |
|------------|--------|------------|
| Video sometimes fails | "No sources" error | Retry request |
| Mind maps separate | Not in studio_status | Use mind_map_list |
| Quiz shows as flashcards | Type field misleading | Track by ID |
| Generation time varies | Long waits | Poll status |

## Security Considerations

### Cookie Security

**Question**: Is local cookie storage secure enough?

**Current Approach**:
- User-only file permissions (0600)
- Dedicated Chrome profile isolation
- No logging of credentials

**Potential Improvements**:
- System keychain integration
- Encrypted storage
- Shorter cookie lifetimes

**Resolution**: Current approach sufficient for personal use.

### API Key Alternative

**Question**: Should we support API keys if Google adds them?

**Options**:
- Environment variable
- Config file
- MCP tool for setting key

**Resolution**: Implement when/if Google provides API keys.

## Feature Roadmap Questions

### Notes Feature

**Current State**: Not implemented

**Question**: Should we add Notes support?

**Considerations**:
- Would enable saving chat responses
- Requires discovering RPC ID
- May increase complexity

**Resolution**: Low priority until user demand.

### Sharing Feature

**Current State**: Not implemented

**Question**: Should we add notebook sharing?

**Considerations**:
- Enterprise use case
- Requires collaboration RPC discovery
- Security implications

**Resolution**: Out of scope for personal use focus.

### Export Feature

**Current State**: Not implemented

**Question**: Should we add content export?

**Options**:
- Direct download via API (if available)
- Screen scraping
- Manual web UI

**Resolution**: Investigate API options when time permits.

## Integration Questions

### Doc-Refresh Loop

**Current State**: Implemented in `src/notebooklm_mcp/doc_refresh/`

**Question**: Should artifact refresh be automatic?

**Options**:
- Automatic on doc change (>15% delta)
- Manual trigger only
- User-configurable threshold

**Current Approach**: Threshold-based with manual override flags.

### Cross-Platform Support

**Current State**: macOS focused

**Question**: How well does it work on Linux/Windows?

**Tested**:
- macOS: Full support
- Linux: Should work (untested)
- Windows: Unknown

**Resolution**: Accept issues, improve as reports come in.

## Performance Questions

### Context Window Optimization

**Current State**: 31 tools consume significant context

**Question**: Can we reduce tool count or consolidate?

**Options**:
- Consolidate similar tools
- Dynamic tool loading
- Tool categories with sub-menus

**Resolution**: Keep current structure, rely on toggle feature.

### Response Size

**Current State**: Compact mode for token efficiency

**Question**: Is compact mode sufficient?

**Measurements**:
- Full response: ~2-5KB per notebook
- Compact response: ~200-500 bytes per notebook

**Resolution**: Compact mode default, full details on request.

## Resolved Questions

| Question | Resolution | Date |
|----------|------------|------|
| Auth token format | JSON file with cookies | 2025-12 |
| CSRF extraction | Auto-extracted from page | 2025-12 |
| Confirmation pattern | `confirm=True` required | 2025-12 |
| Tool count | 31 tools sufficient | 2026-01 |
| Compact mode | Default for efficiency | 2026-01 |

## Contributing Questions

If you encounter an unresolved question:

1. Check existing issues on GitHub
2. Add question to this document with context
3. Propose options if you have ideas
4. Reference related code or API behavior

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System design context
- [SECURITY_AND_PRIVACY.md](SECURITY_AND_PRIVACY.md) - Security decisions
- [../KNOWN_ISSUES.md](../KNOWN_ISSUES.md) - Known bugs
- [../API_REFERENCE.md](../API_REFERENCE.md) - API details


---

## Standards Snapshot (C010)

This repo follows workspace standards from C010_standards:

- **Betty Protocol**: Evidence in 20_receipts/, no self-certification
- **META.yaml**: Keep `last_reviewed` current
- **Cross-platform**: Commands work on macOS, Windows, Linux
- **Closeout**: Git status clean, stash triaged, receipts written

Full standards are canonical in C010_standards.
