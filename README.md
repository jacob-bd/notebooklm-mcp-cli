# NotebookLM CLI & MCP Server

![NotebookLM MCP Header](docs/media/header.jpg)

> 🎉 **January 2026 — Major Update!** This project has been completely refactored to unify **NotebookLM-MCP** and **NotebookLM-CLI** into a single, powerful package. One install gives you both the CLI (`nlm`) and MCP server (`notebooklm-mcp`). See the [CLI Guide](docs/CLI_GUIDE.md) and [MCP Guide](docs/MCP_GUIDE.md) for full documentation.

**Programmatic access to Google NotebookLM** — via command-line interface (CLI) or Model Context Protocol (MCP) server.

> **Note:** Tested with Pro/free tier accounts. May work with NotebookLM Enterprise accounts but has not been tested.

📺 **Watch the Demos**

### MCP Demos

| **General Overview** | **Claude Desktop** | **Perplexity Desktop** | **MCP Super Assistant** |
|:---:|:---:|:---:|:---:|
| [![General](https://img.youtube.com/vi/d-PZDQlO4m4/mqdefault.jpg)](https://www.youtube.com/watch?v=d-PZDQlO4m4) | [![Claude](https://img.youtube.com/vi/PU8JhgLPxes/mqdefault.jpg)](https://www.youtube.com/watch?v=PU8JhgLPxes) | [![Perplexity](https://img.youtube.com/vi/BCKlDNg-qxs/mqdefault.jpg)](https://www.youtube.com/watch?v=BCKlDNg-qxs) | [![MCP SuperAssistant](https://img.youtube.com/vi/7aHDbkr-l_E/mqdefault.jpg)](https://www.youtube.com/watch?v=7aHDbkr-l_E) |

### CLI Demos

| **CLI Overview** | **CLI, MCP & Skills Deep Dive** |
|:---:|:---:|
| [![CLI Overview](https://img.youtube.com/vi/XyXVuALWZkE/mqdefault.jpg)](https://www.youtube.com/watch?v=XyXVuALWZkE) | [![CLI, MCP & Skills](https://img.youtube.com/vi/ZQBQigFK-E8/mqdefault.jpg)](https://www.youtube.com/watch?v=ZQBQigFK-E8) |


## Two Ways to Use

### 🖥️ Command-Line Interface (CLI)

Use `nlm` directly in your terminal for scripting, automation, or interactive use:

```bash
nlm notebook list                              # List all notebooks
nlm notebook create "Research Project"         # Create a notebook
nlm source add <notebook> --url "https://..."  # Add sources
nlm audio create <notebook> --confirm          # Generate podcast
nlm download audio <notebook> <artifact-id>    # Download audio file
nlm share public <notebook>                    # Enable public link
```

Run `nlm --ai` for comprehensive AI-assistant documentation.

### 🤖 MCP Server (for AI Agents)

Connect AI assistants (Claude, Gemini, Cursor, etc.) to NotebookLM:

```bash
# Add to Claude Code or Gemini CLI
claude mcp add --scope user notebooklm-mcp notebooklm-mcp
gemini mcp add --scope user notebooklm-mcp notebooklm-mcp
```

Then use natural language: *"Create a notebook about quantum computing and generate a podcast"*

## Features

| Capability | CLI Command | MCP Tool |
|------------|-------------|----------|
| List notebooks | `nlm notebook list` | `notebook_list` |
| Create notebook | `nlm notebook create` | `notebook_create` |
| Add Sources (URL, Text, Drive, File) | `nlm source add` | `source_add` |
| Query notebook (AI chat) | `nlm notebook query` | `notebook_query` |
| Create Studio Content (Audio, Video, etc.) | `nlm studio create` | `studio_create` |
| Download artifacts | `nlm download <type>` | `download_artifact` |
| Web/Drive research | `nlm research start` | `research_start` |
| Share notebook | `nlm share public/invite` | `notebook_share_*` |
| Sync Drive sources | `nlm source sync` | `source_sync_drive` |

📚 **More Documentation:**
- **[CLI Guide](docs/CLI_GUIDE.md)** — Complete command reference
- **[MCP Guide](docs/MCP_GUIDE.md)** — All 29 MCP tools with examples
- **[Authentication](docs/AUTHENTICATION.md)** — Setup and troubleshooting
- **[API Reference](docs/API_REFERENCE.md)** — Internal API docs for contributors

## Important Disclaimer

This MCP and CLI use **internal APIs** that:
- Are undocumented and may change without notice
- Require cookie extraction from your browser (I have a tool for that!)

Use at your own risk for personal/experimental purposes.

## Installation

Install from PyPI. This single package includes **both the CLI and MCP server**:

### Using uv (Recommended)
```bash
uv tool install notebooklm-mcp-cli
```

### Using uvx (Run Without Install)
```bash
uvx --from notebooklm-mcp-cli nlm --help
uvx --from notebooklm-mcp-cli notebooklm-mcp
```

### Using pip
```bash
pip install notebooklm-mcp-cli
```

### Using pipx
```bash
pipx install notebooklm-mcp-cli
```

**After installation, you get:**
- `nlm` — Command-line interface
- `notebooklm-mcp` — MCP server for AI assistants
- `notebooklm-mcp-auth` — Standalone authentication tool

<details>
<summary>Alternative: Install from Source</summary>

```bash
# Clone the repository
git clone https://github.com/jacob-bd/notebooklm-mcp-cli.git
cd notebooklm-mcp

# Install with uv
uv tool install .
```
</details>

## Upgrading

```bash
# Using uv
uv tool upgrade notebooklm-mcp-cli

# Using pip
pip install --upgrade notebooklm-mcp-cli

# Using pipx
pipx upgrade notebooklm-mcp-cli
```

After upgrading, restart your AI tool to reconnect to the updated MCP server:

- **Claude Code:** Restart the application, or use `/mcp` to reconnect
- **Cursor:** Restart the application
- **Gemini CLI:** Restart the CLI session

## Upgrading from Legacy Versions

If you previously installed the **separate** CLI and MCP packages, you need to migrate to the unified package.

### Step 1: Check What You Have Installed

```bash
uv tool list | grep notebooklm
```

**Legacy packages to remove:**
| Package | What it was |
|---------|-------------|
| `notebooklm-cli` | Old CLI-only package |
| `notebooklm-mcp-server` | Old MCP-only package |

### Step 2: Uninstall Legacy Packages

```bash
# Remove old CLI package (if installed)
uv tool uninstall notebooklm-cli

# Remove old MCP package (if installed)
uv tool uninstall notebooklm-mcp-server
```

### Step 3: Reinstall the Unified Package

After removing legacy packages, reinstall to fix symlinks:

```bash
uv tool install --force notebooklm-mcp-cli
```

> **Why `--force`?** When multiple packages provide the same executable, `uv` can leave broken symlinks after uninstalling. The `--force` flag ensures clean symlinks.

### Step 4: Verify Installation

```bash
uv tool list | grep notebooklm
```

You should see only:
```
notebooklm-mcp-cli v0.2.0
- nlm
- notebooklm-mcp
- notebooklm-mcp-auth
```

### Step 5: Re-authenticate

Your existing cookies should still work, but if you encounter auth issues:

```bash
nlm login
```

> **Note:** MCP server configuration (in Claude Code, Cursor, etc.) does not need to change — the executable name `notebooklm-mcp` is the same.

## Uninstalling

To completely remove the MCP:

```bash
# Using uv
uv tool uninstall notebooklm-mcp-cli

# Using pip
pip uninstall notebooklm-mcp-cli

# Using pipx
pipx uninstall notebooklm-mcp-cli

# Remove cached auth tokens and data (optional)
rm -rf ~/.notebooklm-mcp-cli
```

Also remove from your AI tools:

| Tool | Command |
|------|---------|
| Claude Code | `claude mcp remove notebooklm-mcp` |
| Gemini CLI | `gemini mcp remove notebooklm-mcp` |
| Cursor/VS Code | Remove entry from `~/.cursor/mcp.json` or `~/.vscode/mcp.json` |

## Authentication

Before using the CLI or MCP, you need to authenticate with NotebookLM:

### CLI Authentication (Recommended)

```bash
# Auto mode: launches Chrome, you log in, cookies extracted automatically
nlm login

# Check if already authenticated
nlm login --check

# Use a named profile (for multiple Google accounts)
nlm login --profile work
nlm login --profile personal

# Manual mode: import cookies from a file
nlm login --manual --file cookies.txt
```

**Profile management:**
```bash
nlm login --check                    # Show current auth status
nlm login switch <profile>           # Switch the default profile
nlm login profile list               # List all profiles with email addresses
nlm login profile delete <profile>   # Delete a profile
nlm login profile rename <old> <new> # Rename a profile
```

Each profile gets its own isolated Chrome session, so you can be logged into multiple Google accounts simultaneously.

### Standalone Auth Tool

If you only need the MCP server (not the CLI):

```bash
notebooklm-mcp-auth          # Auto mode (launches Chrome)
notebooklm-mcp-auth --file   # Manual file mode
```

**How it works:** Auto mode launches a dedicated Chrome profile, you log in to Google, and cookies are extracted automatically. Your login persists for future auth refreshes.

For detailed instructions and troubleshooting, see **[docs/AUTHENTICATION.md](docs/AUTHENTICATION.md)**.

## MCP Configuration

> **⚠️ Context Window Warning:** This MCP provides **29 tools**. Disable it when not using NotebookLM to preserve context. In Claude Code: `@notebooklm-mcp` to toggle.

### Quick Setup

**Claude Code / Gemini CLI:**
```bash
claude mcp add --scope user notebooklm-mcp notebooklm-mcp
gemini mcp add --scope user notebooklm-mcp notebooklm-mcp
```

**Cursor / VS Code / Claude Desktop** — Add to your config file:
```json
{
  "mcpServers": {
    "notebooklm-mcp": {
      "command": "notebooklm-mcp"
    }
  }
}
```

| Tool | Config Location |
|------|-----------------|
| Cursor | `~/.cursor/mcp.json` |
| VS Code | `~/.vscode/mcp.json` |
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` |

**Run without installing (uvx):**
```json
{
  "mcpServers": {
    "notebooklm-mcp": {
      "command": "uvx",
      "args": ["--from", "notebooklm-mcp-cli", "notebooklm-mcp"]
    }
  }
}
```

📚 **Full configuration details:** [MCP Guide](docs/MCP_GUIDE.md) — Server options, environment variables, HTTP transport, multi-user setup, and context window management.

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

### Sharing & Collaboration

- "Show me the sharing settings for this notebook"
- "Make this notebook public so anyone with the link can view it"
- "Disable public access to this notebook"
- "Invite user@example.com as an editor to this notebook"
- "Add a viewer to my research notebook"

**Pro tip:** After creating studio content (audio, video, reports, etc.), poll the status to get download URLs when generation completes.

## Authentication Lifecycle

| Component | Duration | Refresh |
|-----------|----------|---------|
| Cookies | ~2-4 weeks | Auto-refresh via headless Chrome (if profile saved) |
| CSRF Token | ~minutes | Auto-refreshed on every request failure |
| Session ID | Per MCP session | Auto-extracted on MCP start |

**v0.1.9+**: The server now automatically handles token expiration:
1. Refreshes CSRF tokens immediately when expired
2. Reloads cookies from disk if updated externally
3. Runs headless Chrome auth if profile has saved login

You can also call `refresh_auth()` to explicitly reload tokens.

If automatic refresh fails (Google login fully expired), run `notebooklm-mcp-auth` again.

## Troubleshooting

### `uv tool upgrade` Not Installing Latest Version

**Symptoms:**
- Running `uv tool upgrade notebooklm-mcp-cli` installs an older version (e.g., 0.1.5 instead of 0.1.9)
- `uv cache clean` doesn't fix the issue

**Why this happens:** `uv tool upgrade` respects version constraints from your original installation. If you initially installed an older version or with a constraint, `upgrade` stays within those bounds by design.

**Fix — Force reinstall:**
```bash
uv tool install --force notebooklm-mcp-cli
```

This bypasses any cached constraints and installs the absolute latest version from PyPI.

**Verify:**
```bash
uv tool list | grep notebooklm
# Should show: notebooklm-mcp-cli v0.1.9 (or latest)
```

---

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

## Credits

Special thanks to:
- **Le Anh Tuan** ([@latuannetnam](https://github.com/latuannetnam)) for contributing the HTTP transport, debug logging system, and performance optimizations.
- **David Szabo-Pele** ([@davidszp](https://github.com/davidszp)) for the `source_get_content` tool and Linux auth fixes.
- **saitrogen** ([@saitrogen](https://github.com/saitrogen)) for the research polling query fallback fix.
- **VooDisss** ([@VooDisss](https://github.com/VooDisss)) for multi-browser authentication improvements.
- **codepiano** ([@codepiano](https://github.com/codepiano)) for the configurable DevTools timeout for the auth CLI.


## License

MIT License
