# CLI Guide

Complete command reference for the `nlm` command-line interface.

## Installation

```bash
# Using uv (recommended)
uv tool install notebooklm-mcp-cli

# Using pip
pip install notebooklm-mcp-cli
```

## Authentication

```bash
nlm login                         # Opens Chrome, extracts cookies automatically
nlm login --profile work          # Named profile for multiple accounts
nlm login --check                 # Check if authenticated
nlm login switch <profile>        # Switch default profile
nlm login profile list            # List all profiles with email addresses
nlm login profile delete <name>   # Delete a profile
nlm login profile rename <old> <new>  # Rename a profile
```

Each profile gets its own isolated Chrome session, so you can stay logged into multiple Google accounts simultaneously.

## Command Structure

The CLI supports **two styles** - use whichever feels natural:

```bash
# Noun-first (resource-oriented)
nlm notebook create "Title"
nlm source add <notebook> --url <url>

# Verb-first (action-oriented)  
nlm create notebook "Title"
nlm add url <notebook> <url>
```

---

## Command Reference

### Notebooks

```bash
nlm notebook list                      # List all notebooks
nlm notebook list --json               # JSON output
nlm notebook create "Title"            # Create notebook
nlm notebook get <id>                  # Get details
nlm notebook describe <id>             # AI summary
nlm notebook rename <id> "New Title"   # Rename
nlm notebook delete <id> --confirm     # Delete (IRREVERSIBLE)
nlm notebook query <id> "question"     # Chat with sources
```

### Sources

```bash
nlm source list <notebook>                         # List sources
nlm source add <notebook> --url "https://..."      # Add URL
nlm source add <notebook> --url "https://..." --wait  # Add and wait until ready
nlm source add <notebook> --text "content" --title "Notes"  # Add text
nlm source add <notebook> --file document.pdf --wait  # Upload file
nlm source add <notebook> --youtube "https://..."  # Add YouTube
nlm source add <notebook> --drive <doc-id>         # Add Drive doc
nlm source get <source-id>                         # Get content
nlm source describe <source-id>                    # AI summary
nlm source stale <notebook>                        # Check stale Drive sources
nlm source sync <notebook> --confirm               # Sync stale sources
nlm source delete <source-id> --confirm            # Delete (IRREVERSIBLE)
```

### Studio Content Creation

```bash
# Audio (podcasts)
nlm audio create <notebook> --confirm
nlm audio create <notebook> --format deep_dive --length long --confirm
# Formats: deep_dive, brief, critique, debate
# Lengths: short, default, long

# Video
nlm video create <notebook> --confirm
nlm video create <notebook> --format explainer --style classic --confirm
# Formats: explainer, brief
# Styles: auto_select, classic, whiteboard, kawaii, anime, watercolor, retro_print, heritage, paper_craft

# Reports
nlm report create <notebook> --format "Briefing Doc" --confirm
# Formats: "Briefing Doc", "Study Guide", "Blog Post", "Create Your Own"

# Quiz & Flashcards
nlm quiz create <notebook> --count 10 --difficulty medium --confirm
nlm flashcards create <notebook> --difficulty hard --confirm

# Other
nlm mindmap create <notebook> --confirm
nlm slides create <notebook> --confirm
nlm infographic create <notebook> --orientation landscape --confirm
nlm data-table create <notebook> --description "Sales by region" --confirm
```

### Downloads

```bash
nlm download audio <notebook> <artifact-id> --output podcast.mp3
nlm download video <notebook> <artifact-id> --output video.mp4
nlm download report <notebook> <artifact-id> --output report.md
nlm download mind-map <notebook> <artifact-id> --output mindmap.json
nlm download slide-deck <notebook> <artifact-id> --output slides.pdf
nlm download infographic <notebook> <artifact-id> --output infographic.png
nlm download data-table <notebook> <artifact-id> --output data.csv

# Interactive formats (quiz/flashcards)
nlm download quiz <notebook> <artifact-id> --format html --output quiz.html
nlm download flashcards <notebook> <artifact-id> --format markdown --output cards.md
```

### Research

```bash
nlm research start "query" --notebook-id <id> --mode fast  # Quick search
nlm research start "query" --notebook-id <id> --mode deep  # Extended research
nlm research start "query" --notebook-id <id> --source drive  # Search Drive
nlm research status <notebook> --max-wait 300              # Poll until done
nlm research import <notebook> <task-id>                   # Import sources
```

### Studio Status

```bash
nlm studio status <notebook>           # Check artifact generation status
nlm studio delete <notebook> <artifact-id> --confirm  # Delete artifact
```

### Sharing

```bash
nlm share status <notebook>                    # View sharing settings
nlm share public <notebook>                    # Enable public link
nlm share private <notebook>                   # Disable public link
nlm share invite <notebook> email@example.com  # Invite viewer
nlm share invite <notebook> email --role editor  # Invite editor
```

### Chat Configuration

```bash
nlm chat configure <notebook> --goal default --length default
nlm chat configure <notebook> --goal learning_guide --length longer
nlm chat configure <notebook> --goal custom --prompt "You are an expert..."
```

### Configuration

```bash
nlm config show                         # Show all settings
nlm config get auth.default_profile     # Get a specific value
nlm config set auth.default_profile work  # Set default profile
nlm config set output.format json       # Change default output format
```

**Available Settings:**

| Key | Default | Description |
|-----|---------|-------------|
| `output.format` | `table` | Default output format (table, json) |
| `output.color` | `true` | Enable colored output |
| `output.short_ids` | `true` | Show shortened IDs |
| `auth.browser` | `auto` | Browser for login (auto, chrome, chromium) |
| `auth.default_profile` | `default` | Profile to use when `--profile` not specified |

### Aliases (Shortcuts)

```bash
nlm alias set myproject <notebook-id>   # Create alias
nlm alias list                          # List all aliases
nlm alias get myproject                 # Resolve to UUID
nlm alias delete myproject              # Remove alias

# Use aliases anywhere
nlm notebook get myproject
nlm source list myproject
```

### Skills (AI Assistant Integration)

```bash
nlm skill list                           # Show installation status
nlm skill install claude-code            # Install for Claude Code
nlm skill install cursor                 # Install for Cursor AI
nlm skill install gemini-cli             # Install for Gemini CLI
nlm skill install <tool> --level project # Install at project level
nlm skill uninstall <tool>               # Remove skill
nlm skill show                           # View skill content

# Verb-first alternatives
nlm install skill claude-code
nlm list skills
```

**Supported Tools:** `claude-code`, `cursor`, `codex`, `opencode`, `gemini-cli`, `antigravity`, `other`

### Setup (MCP Server Configuration)

Configure the NotebookLM MCP server for AI tools in one command:

```bash
nlm setup add claude-code       # Configure via `claude mcp add`
nlm setup add claude-desktop    # Write claude_desktop_config.json
nlm setup add gemini            # Write ~/.gemini/settings.json
nlm setup add cursor            # Write ~/.cursor/mcp.json
nlm setup add windsurf          # Write mcp_config.json

nlm setup remove claude-desktop # Remove MCP configuration
nlm setup remove gemini         # Remove from Gemini CLI

nlm setup list                  # Show all clients and config status
```

**Supported Clients:** `claude-code`, `claude-desktop`, `gemini`, `cursor`, `windsurf`

> **Note:** `nlm setup` configures the MCP server transport. Use `nlm skill install` to install skill/reference docs for AI tools that don't use MCP.

### Doctor (Diagnostics)

Run diagnostics to troubleshoot installation, authentication, and configuration issues:

```bash
nlm doctor              # Run all checks
nlm doctor --verbose    # Include additional details (Python version, paths, etc.)
```

**Checks performed:**

| Category | What it checks |
|----------|---------------|
| Installation | Package version, `nlm` and `notebooklm-mcp` binary paths |
| Authentication | Profile status, cookies present, CSRF token, account email |
| Chrome | Browser installed, saved Chrome profiles for headless auth |
| AI Tools | MCP configuration status for each supported client |

Each issue includes a suggested fix (e.g., "Run `nlm login` to authenticate").

---

## Output Formats

| Flag | Description |
|------|-------------|
| (none) | Rich table format |
| `--json` | JSON output |
| `--quiet` | IDs only |
| `--title` | "ID: Title" format |
| `--full` | All columns |

---

## Complete Workflow Example

```bash
# 1. Authenticate and configure
nlm login
nlm setup add claude-code       # One-time MCP setup

# 2. Create notebook and set alias
nlm notebook create "AI Research"
nlm alias set ai <notebook-id>

# 3. Add sources (with --wait to ensure ready)
nlm source add ai --url "https://example.com/article" --wait
nlm source add ai --file research.pdf --wait

# 4. Generate podcast
nlm audio create ai --format deep_dive --confirm

# 5. Wait for generation
nlm studio status ai

# 6. Download when ready
nlm download audio ai <artifact-id> --output podcast.mp3
```

---

## Tips

- Session lasts ~20 minutes; run `nlm login` if operations fail
- Use `--confirm` for all create/delete commands in scripts
- Use `--wait` when adding sources to ensure they're ready before querying
- Use aliases for frequently-used notebooks
- Audio/video takes 1-5 minutes; poll with `nlm studio status`
- Use `nlm login switch <name>` to change the default profile
- Run `nlm login profile list` to see all profiles with their associated email addresses
- Run `nlm doctor` to diagnose installation, auth, or config issues
- Use `nlm setup add <client>` to quickly configure MCP for your AI tool