---
name: nlm-skill
description: "Expert guide for the NotebookLM CLI (`nlm`) and MCP server — programmatic access to Google NotebookLM. Use for: creating/managing notebooks, adding sources (URLs, YouTube, text, Google Drive), generating content (podcasts, reports, quizzes, flashcards, mind maps, slides, infographics, videos, data tables), conducting research, chatting with sources, or automating NotebookLM workflows."
metadata:
  openclaw:
    category: "productivity"
    requires:
      bins: ["nlm"]
    skills: ["nlm-notebook", "nlm-source", "nlm-studio", "nlm-research"]
---

# NotebookLM CLI & MCP Expert

This skill provides comprehensive guidance for using NotebookLM via both the `nlm` CLI and MCP tools.

## Tool Detection (CRITICAL - Read First!)

**ALWAYS check which tools are available before proceeding:**

1. **Check for MCP tools**: Look for tools starting with `mcp__notebooklm-mcp__*` or `mcp_notebooklm_*`
2. **If BOTH MCP tools AND CLI are available**: **ASK the user** which they prefer to use before proceeding
3. **If only MCP tools are available**: Use them directly (refer to tool docstrings for parameters)
4. **If only CLI is available**: Use `nlm` CLI commands via Bash

**Decision Logic:**
```
has_mcp_tools = check_available_tools()  # Look for mcp__notebooklm-mcp__* or mcp_notebooklm_*
has_cli = check_bash_available()  # Can run nlm commands

if has_mcp_tools and has_cli:
    # ASK USER: "I can use either MCP tools or the nlm CLI. Which do you prefer?"
    user_preference = ask_user()
else if has_mcp_tools:
    # Use MCP tools directly
    mcp__notebooklm-mcp__notebook_list()
else:
    # Use CLI via Bash
    bash("nlm notebook list")
```

This skill documents BOTH approaches. Choose the appropriate one based on tool availability and **user preference**.

## Quick Reference

**Run `nlm --ai` to get comprehensive AI-optimized documentation** - this provides a complete view of all CLI capabilities.

```bash
nlm --help              # List all commands
nlm <command> --help    # Help for specific command
nlm --ai                # Full AI-optimized documentation (RECOMMENDED)
nlm --version           # Check installed version
```

## Critical Rules (Read First!)

1. **Always authenticate first**: Run `nlm login` before any operations
2. **Sessions expire in ~20 minutes**: Re-run `nlm login` if commands start failing
3. **⚠️ ALWAYS ASK USER BEFORE DELETE**: Before executing ANY delete command, ask the user for explicit confirmation. Deletions are **irreversible**. Show what will be deleted and warn about permanent data loss.
4. **`--confirm` is REQUIRED**: All generation and delete commands need `--confirm` or `-y` (CLI) or `confirm=True` (MCP)
5. **Research requires `--notebook-id`**: The flag is mandatory, not positional
6. **Capture IDs from output**: Create/start commands return IDs needed for subsequent operations
7. **Use aliases**: Simplify long UUIDs with `nlm alias set <name> <uuid>`
8. **Check aliases before creating**: Run `nlm alias list` before creating a new alias to avoid conflicts with existing names.
9. **DO NOT launch REPL**: Never use `nlm chat start` - it opens an interactive REPL that AI tools cannot control. Use `nlm notebook query` for one-shot Q&A instead.
10. **Choose output format wisely**: Default output (no flags) is compact and token-efficient—use it for status checks. Use `--quiet` to capture IDs for piping. Only use `--json` when you need to parse specific fields programmatically.
11. **Use `--help` when unsure**: Run `nlm <command> --help` to see available options and flags for any command.

## Workflow Decision Tree

Use this to determine the right sequence of commands:

```
User wants to...
│
├─► Work with NotebookLM for the first time
│   └─► nlm login → nlm notebook create "Title"
│
├─► Add content to a notebook
│   ├─► From a URL/webpage → nlm source add <nb-id> --url "https://..."
│   ├─► From YouTube → nlm source add <nb-id> --url "https://youtube.com/..."
│   ├─► From pasted text → nlm source add <nb-id> --text "content" --title "Title"
│   ├─► From Google Drive → nlm source add <nb-id> --drive <doc-id> --type doc
│   └─► Discover new sources → nlm research start "query" --notebook-id <nb-id>
│
├─► Generate content from sources
│   ├─► Podcast/Audio → nlm audio create <nb-id> --confirm
│   ├─► Written summary → nlm report create <nb-id> --confirm
│   ├─► Study materials → nlm quiz/flashcards create <nb-id> --confirm
│   ├─► Visual content → nlm mindmap/slides/infographic create <nb-id> --confirm
│   ├─► Video → nlm video create <nb-id> --confirm
│   └─► Extract data → nlm data-table create <nb-id> "description" --confirm
│
├─► Ask questions about sources
│   └─► nlm notebook query <nb-id> "question"
│       (Use --conversation-id for follow-ups)
│       ⚠️ Do NOT use `nlm chat start` - it's a REPL for humans only
│
├─► Check generation status
│   └─► nlm studio status <nb-id>
│
└─► Manage/cleanup
    ├─► List notebooks → nlm notebook list
    ├─► List sources → nlm source list <nb-id>
    ├─► Delete source → nlm source delete <source-id> --confirm
    └─► Delete notebook → nlm notebook delete <nb-id> --confirm
```

## Command Categories

### 1. Authentication

#### MCP Authentication

If using MCP tools and encountering authentication errors:

```bash
# Run the CLI authentication (works for both CLI and MCP)
nlm login

# Then reload tokens in MCP
mcp__notebooklm-mcp__refresh_auth()
```

Or manually save cookies via MCP (fallback):
```python
# Extract cookies from Chrome DevTools and save
mcp__notebooklm-mcp__save_auth_tokens(cookies="<cookie_header>")
```

#### CLI Authentication

```bash
nlm login                           # Launch browser, extract cookies (primary method)
nlm login --check                   # Validate current session
nlm login --profile work            # Use named profile for multiple accounts
nlm login --provider openclaw --cdp-url http://127.0.0.1:18800  # External CDP provider
nlm login switch <profile>          # Switch the default profile
nlm login profile list              # List all profiles with email addresses
nlm login profile delete <name>     # Delete a profile
nlm login profile rename <old> <new> # Rename a profile
```

**Multi-Profile Support**: Each profile gets its own isolated browser session (supports Chrome, Arc, Brave, Edge, Chromium, and more), so you can be logged into multiple Google accounts simultaneously.

**Session lifetime**: ~20 minutes. Re-authenticate when commands fail with auth errors.

**Switching MCP Accounts**: The MCP server always uses the active default profile. If you need to switch which Google account the MCP server is communicating with, you MUST use the CLI: run `nlm login switch <name>`. Your next MCP tool call will instantly use the new account.

**Note**: Both MCP and CLI share the same authentication backend, so authenticating with one works for both.

### 2. Notebook Management

See also: **[nlm-notebook](../nlm-notebook/SKILL.md)** for focused notebook operations.

#### MCP Tools

Use tools: `notebook_list`, `notebook_create`, `notebook_get`, `notebook_describe`, `notebook_query`, `notebook_rename`, `notebook_delete`. All accept `notebook_id` parameter. Delete requires `confirm=True`.

#### CLI Commands
```bash
nlm notebook list                      # List all notebooks
nlm notebook list --json               # JSON output for parsing
nlm notebook list --quiet              # IDs only (for scripting)
nlm notebook create "Title"            # Create notebook, returns ID
nlm notebook get <id>                  # Get notebook details
nlm notebook describe <id>             # AI-generated summary + suggested topics
nlm notebook query <id> "question"     # One-shot Q&A with sources
nlm notebook rename <id> "New Title"   # Rename notebook
nlm notebook delete <id> --confirm     # PERMANENT deletion
```

### 3. Source Management

See also: **[nlm-source](../nlm-source/SKILL.md)** for focused source operations.

#### MCP Tools

Use `source_add` with these `source_type` values:
- `url` - Web page or YouTube URL (`url` param)
- `text` - Pasted content (`text` + `title` params)
- `file` - Local file upload (`file_path` param)
- `drive` - Google Drive doc (`document_id` + `doc_type` params)

Other tools: `source_list_drive`, `source_describe`, `source_get_content`, `source_rename`, `source_sync_drive` (requires `confirm=True`), `source_delete` (requires `confirm=True`).

#### CLI Commands
```bash
# Adding sources
nlm source add <nb-id> --url "https://..."           # Web page
nlm source add <nb-id> --url "https://youtube.com/..." # YouTube video
nlm source add <nb-id> --text "content" --title "X"  # Pasted text
nlm source add <nb-id> --drive <doc-id>              # Drive doc (auto-detect type)
nlm source add <nb-id> --drive <doc-id> --type slides # Explicit type

# Listing and viewing
nlm source list <nb-id>                # Table of sources
nlm source list <nb-id> --drive        # Show Drive sources with freshness
nlm source list <nb-id> --drive -S     # Skip freshness checks (faster)
nlm source get <source-id>             # Source metadata
nlm source describe <source-id>        # AI summary + keywords
nlm source content <source-id>         # Raw text content
nlm source content <source-id> -o file.txt  # Export to file

# Drive sync (for stale sources)
nlm source stale <nb-id>               # List outdated Drive sources
nlm source sync <nb-id> --confirm      # Sync all stale sources
nlm source sync <nb-id> --source-ids <ids> --confirm  # Sync specific

# Rename
nlm source rename <source-id> "New Title" --notebook <nb-id>

# Deletion
nlm source delete <source-id> --confirm
```

**Drive types**: `doc`, `slides`, `sheets`, `pdf`

### 4. Research (Source Discovery)

See also: **[nlm-research](../nlm-research/SKILL.md)** for focused research operations.

Research finds NEW sources from the web or Google Drive.

#### MCP Tools

Use `research_start` with:
- `source`: `web` or `drive`
- `mode`: `fast` (~30s) or `deep` (~5min, web only)

Workflow: `research_start` → poll `research_status` → `research_import`

#### CLI Commands
```bash
# Start research (--notebook-id is REQUIRED)
nlm research start "query" --notebook-id <id>              # Fast web (~30s)
nlm research start "query" --notebook-id <id> --mode deep  # Deep web (~5min)
nlm research start "query" --notebook-id <id> --source drive  # Drive search

# Check progress
nlm research status <nb-id>                   # Poll until done (5min max)
nlm research status <nb-id> --max-wait 0      # Single check, no waiting
nlm research status <nb-id> --task-id <tid>   # Check specific task
nlm research status <nb-id> --full            # Full details

# Import discovered sources
nlm research import <nb-id> <task-id>            # Import all
nlm research import <nb-id> <task-id> --indices 0,2,5  # Import specific
```

**Modes**: `fast` (~30s, ~10 sources) | `deep` (~5min, ~40+ sources, web only)

### 5. Content Generation (Studio)

See also: **[nlm-studio](../nlm-studio/SKILL.md)** for focused studio operations.

#### MCP Tools (Unified Creation)

Use `studio_create` with `artifact_type` and type-specific options. All require `confirm=True`.

| artifact_type | Key Options |
|--------------|-------------|
| `audio` | `audio_format`: deep_dive/brief/critique/debate, `audio_length`: short/default/long |
| `video` | `video_format`: explainer/brief, `visual_style`: auto_select/classic/whiteboard/kawaii/anime/watercolor/retro_print/heritage/paper_craft |
| `report` | `report_format`: Briefing Doc/Study Guide/Blog Post/Create Your Own, `custom_prompt` |
| `quiz` | `question_count`, `difficulty`: easy/medium/hard |
| `flashcards` | `difficulty`: easy/medium/hard |
| `mind_map` | `title` |
| `slide_deck` | `slide_format`: detailed_deck/presenter_slides, `slide_length`: short/default |
| `infographic` | `orientation`: landscape/portrait/square, `detail_level`: concise/standard/detailed, `infographic_style`: auto_select/sketch_note/professional/bento_grid/editorial/instructional/bricks/clay/anime/kawaii/scientific |
| `data_table` | `description` (REQUIRED) |

**Common options**: `source_ids`, `language` (BCP-47 code), `focus_prompt`

#### CLI Commands
```bash
# Audio (Podcast)
nlm audio create <id> --confirm
nlm audio create <id> --format deep_dive --length default --confirm

# Report
nlm report create <id> --confirm
nlm report create <id> --format "Study Guide" --confirm

# Quiz / Flashcards
nlm quiz create <id> --count 10 --difficulty 3 --confirm
nlm flashcards create <id> --difficulty medium --confirm

# Visual
nlm mindmap create <id> --confirm
nlm slides create <id> --format presenter --confirm
nlm infographic create <id> --orientation portrait --style professional --confirm
nlm video create <id> --format brief --style whiteboard --confirm

# Data Table (description required)
nlm data-table create <id> "Extract all dates and events" --confirm
```

### 6. Studio Artifact Management

```bash
nlm studio status <nb-id>                          # List all artifacts
nlm studio status <nb-id> --full                   # Full details
nlm download audio <nb-id> --output podcast.mp3
nlm download video <nb-id> --output video.mp4
nlm download report <nb-id> --output report.md
nlm download slide-deck <nb-id> --output slides.pdf
nlm export sheets <nb-id> <artifact-id>            # → Google Sheets
nlm export docs <nb-id> <artifact-id>              # → Google Docs
nlm studio delete <nb-id> <artifact-id> --confirm
nlm slides revise <artifact-id> --slide '1 Make title larger' --confirm
```

### 7. Notes, Sharing & Aliases

```bash
# Notes
nlm note create <nb-id> "Content" --title "Title"
nlm note list <nb-id>
nlm note update <nb-id> <note-id> --content "New content"
nlm note delete <nb-id> <note-id> --confirm

# Sharing
nlm share status <nb-id>
nlm share public <nb-id>           # Enable public link
nlm share public <nb-id> --off     # Disable
nlm share invite <nb-id> user@example.com --role editor

# Aliases (UUID shortcuts)
nlm alias set myproject <uuid>
nlm alias list
nlm alias delete myproject
```

## Output Formats

| Flag | Description |
|------|-------------|
| (none) | Rich table (human-readable) |
| `--json` | JSON output (for parsing) |
| `--quiet` | IDs only (for piping) |
| `--full` | All columns/details |

## Error Recovery

| Error | Cause | Solution |
|-------|-------|----------|
| "Cookies have expired" | Session timeout | `nlm login` |
| "Notebook not found" | Invalid ID | `nlm notebook list` |
| "Rate limit exceeded" | Too many calls | Wait 30s, retry |
| "Research already in progress" | Pending research | Use `--force` or import first |

## Advanced Reference

For detailed information, see:
- **[references/command_reference.md](references/command_reference.md)**: Complete command signatures
- **[references/troubleshooting.md](references/troubleshooting.md)**: Detailed error handling
- **[references/workflows.md](references/workflows.md)**: End-to-end task sequences
