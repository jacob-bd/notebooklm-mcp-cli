# NotebookLM CLI - Complete Command Reference

This document contains the complete command signatures and all available options for every `nlm` command.

## Table of Contents

1. [Global Options](#global-options)
2. [Authentication](#authentication)
3. [Notebook Commands](#notebook-commands)
4. [Source Commands](#source-commands)
5. [Research Commands](#research-commands)
6. [Generation Commands](#generation-commands)
7. [Studio Commands](#studio-commands)
8. [Download Commands](#download-commands)
9. [Export Commands](#export-commands)
10. [Sharing Commands](#sharing-commands)
11. [Note Commands](#note-commands)
12. [Chat Commands](#chat-commands)
13. [Alias Commands](#alias-commands)
14. [Config Commands](#config-commands)

---

## Global Options

```bash
nlm --version, -v      # Show version and exit
nlm --ai               # Output AI-friendly documentation
nlm --install-completion  # Install shell completion
nlm --show-completion  # Show completion script
nlm --help             # Show help and exit
```

---

## Authentication

### nlm login

Authenticate with NotebookLM using Chrome DevTools Protocol.

```bash
nlm login [OPTIONS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--profile` | `-p` | Profile name for multiple accounts |
| `--check` | | Validate current credentials without re-authenticating |
| `--legacy` | `-l` | Use browser-cookie3 fallback (not recommended) |
| `--browser` | `-b` | Browser for legacy mode (chrome, firefox, edge) |
| `--manual` | `-m` | Import cookies from file |
| `--file` | `-f` | Cookie file path for manual mode |

**Note**: Each profile gets its own isolated Chrome session, so you can be logged into multiple Google accounts simultaneously.

### nlm login profile list

List all authentication profiles with their associated email addresses.

```bash
nlm login profile list
```

### nlm login profile delete

Delete an authentication profile and its credentials.

```bash
nlm login profile delete <profile>
```

### nlm login profile rename

Rename an authentication profile.

```bash
nlm login profile rename <old-name> <new-name>
```

### nlm login switch

Switch the default profile for all commands.

```bash
nlm login switch <profile>
```

| Argument | Description |
|----------|-------------|
| `<profile>` | Profile name to switch to |

**Example:**
```bash
nlm login switch work
# Output: ✓ Switched default profile to work
#         Account: jsmith@company.com
```

---

## Notebook Commands

### nlm notebook list

List all notebooks.

```bash
nlm notebook list [OPTIONS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--json` | | Output as JSON |
| `--quiet` | `-q` | Output IDs only |
| `--title` | | Output as "ID: Title" |
| `--full` | | Show all columns |
| `--profile` | `-p` | Use specific profile |

### nlm notebook create

Create a new notebook.

```bash
nlm notebook create <title> [OPTIONS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--profile` | `-p` | Use specific profile |

### nlm notebook get

Get notebook details.

```bash
nlm notebook get <notebook-id> [OPTIONS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--profile` | `-p` | Use specific profile |

### nlm notebook describe

Get AI-generated notebook summary with suggested topics.

```bash
nlm notebook describe <notebook-id> [OPTIONS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--profile` | `-p` | Use specific profile |

### nlm notebook query

Ask a question about notebook sources.

```bash
nlm notebook query <notebook-id> <question> [OPTIONS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--source-ids` | | Limit to specific sources (comma-separated) |
| `--conversation-id` | | Continue existing conversation |
| `--profile` | `-p` | Use specific profile |

### nlm notebook rename

Rename a notebook.

```bash
nlm notebook rename <notebook-id> <new-title> [OPTIONS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--profile` | `-p` | Use specific profile |

### nlm notebook delete

Delete a notebook permanently.

```bash
nlm notebook delete <notebook-id> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--confirm` | **Required** to confirm deletion |
| `--profile` | Use specific profile |

---

## Source Commands

### nlm source list

List sources in a notebook.

```bash
nlm source list <notebook-id> [OPTIONS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--json` | | Output as JSON |
| `--quiet` | `-q` | Output IDs only |
| `--title` | | Output as "ID: Title" |
| `--url` | | Output as "ID: URL" |
| `--full` | | Show all columns (wider URL display) |
| `--drive` | | Show Drive sources with freshness status |
| `--skip-freshness` | `-S` | Skip freshness checks (faster with --drive) |
| `--profile` | `-p` | Use specific profile |

### nlm source add

Add a source to a notebook.

```bash
nlm source add <notebook-id> [OPTIONS]
```

**URL Source:**
| Option | Description |
|--------|-------------|
| `--url` | URL to add (web page or YouTube) |

**Text Source:**
| Option | Description |
|--------|-------------|
| `--text` | Text content to add |
| `--title` | Title for text source |

**Drive Source:**
| Option | Description |
|--------|-------------|
| `--drive` | Google Drive document ID |
| `--type` | Drive doc type: `doc`, `slides`, `sheets`, `pdf` |
| `--title` | Display title |

| Option | Short | Description |
|--------|-------|-------------|
| `--profile` | `-p` | Use specific profile |

### nlm source get

Get source metadata.

```bash
nlm source get <source-id> [OPTIONS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--profile` | `-p` | Use specific profile |

### nlm source describe

Get AI-generated source summary with keywords.

```bash
nlm source describe <source-id> [OPTIONS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--profile` | `-p` | Use specific profile |

### nlm source content

Get raw text content of a source.

```bash
nlm source content <source-id> [OPTIONS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--output` | `-o` | Export to file path |
| `--profile` | `-p` | Use specific profile |

### nlm source stale

List stale (outdated) Drive sources.

```bash
nlm source stale <notebook-id> [OPTIONS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--profile` | `-p` | Use specific profile |

### nlm source sync

Sync Drive sources with latest content.

```bash
nlm source sync <notebook-id> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--confirm` | **Required** to execute sync |
| `--source-ids` | Specific source IDs to sync (comma-separated) |
| `--profile` | Use specific profile |

### nlm source delete

Delete a source permanently.

```bash
nlm source delete <source-id> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--confirm` | **Required** to confirm deletion |
| `--profile` | Use specific profile |

---

## Research Commands

### nlm research start

Start a research task to discover new sources.

```bash
nlm research start <query> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--notebook-id` | **Required** - Target notebook ID |
| `--mode` | `fast` (default, ~30s) or `deep` (~5min, web only) |
| `--source` | `web` (default) or `drive` |
| `--force` | Override pending research |
| `--profile` | Use specific profile |

### nlm research status

Check research task progress.

```bash
nlm research status <notebook-id> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--task-id` | Check specific task (auto-detected if omitted) |
| `--max-wait` | Max seconds to wait (default: 300, 0=single check) |
| `--full` | Show full details |
| `--profile` | Use specific profile |

### nlm research import

Import discovered sources into notebook.

```bash
nlm research import <notebook-id> <task-id> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--indices` | Comma-separated indices of sources to import (default: all) |
| `--profile` | Use specific profile |

---

## Generation Commands

All generation commands share these common options:

| Option | Short | Description |
|--------|-------|-------------|
| `--confirm` | `-y` | **Required** to execute generation |
| `--source-ids` | | Limit to specific sources (comma-separated) |
| `--language` | | BCP-47 language code (en, es, fr, de, ja) |
| `--profile` | `-p` | Use specific profile |

### nlm audio create

Generate audio overview (podcast).

```bash
nlm audio create <notebook-id> [OPTIONS]
```

| Option | Values | Default |
|--------|--------|---------|
| `--format` | `deep_dive`, `brief`, `critique`, `debate` | `deep_dive` |
| `--length` | `short`, `default`, `long` | `default` |
| `--focus` | Focus text/topic | |

### nlm report create

Generate written report.

```bash
nlm report create <notebook-id> [OPTIONS]
```

| Option | Values | Default |
|--------|--------|---------|
| `--format` | `"Briefing Doc"`, `"Study Guide"`, `"Blog Post"`, `"Create Your Own"` | `"Briefing Doc"` |
| `--prompt` | Custom prompt (required for "Create Your Own") | |

### nlm quiz create

Generate quiz questions.

```bash
nlm quiz create <notebook-id> [OPTIONS]
```

| Option | Values | Default |
|--------|--------|---------|
| `--count` | Number of questions | 2 |
| `--difficulty` | 1-5 (1=easy, 5=hard) | 2 |

### nlm flashcards create

Generate flashcards.

```bash
nlm flashcards create <notebook-id> [OPTIONS]
```

| Option | Values | Default |
|--------|--------|---------|
| `--difficulty` | `easy`, `medium`, `hard` | `medium` |

### nlm mindmap create

Generate mind map.

```bash
nlm mindmap create <notebook-id> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--title` | Display title for the mind map |

### nlm mindmap list

List existing mind maps.

```bash
nlm mindmap list <notebook-id> [OPTIONS]
```

### nlm slides create

Generate slide deck.

```bash
nlm slides create <notebook-id> [OPTIONS]
```

| Option | Values | Default |
|--------|--------|---------|
| `--format` | `detailed`, `presenter` | `detailed` |
| `--length` | `short`, `default` | `default` |
| `--focus` | Focus text/topic | |

### nlm infographic create

Generate infographic.

```bash
nlm infographic create <notebook-id> [OPTIONS]
```

| Option | Values | Default |
|--------|--------|---------|
| `--orientation` | `landscape`, `portrait`, `square` | `landscape` |
| `--detail` | `concise`, `standard`, `detailed` | `standard` |
| `--focus` | Focus text/topic | |

### nlm video create

Generate video overview.

```bash
nlm video create <notebook-id> [OPTIONS]
```

| Option | Values | Default |
|--------|--------|---------|
| `--format` | `explainer`, `brief` | `explainer` |
| `--style` | `auto_select`, `classic`, `whiteboard`, `kawaii`, `anime`, `watercolor`, `retro_print`, `heritage`, `paper_craft` | `auto_select` |
| `--focus` | Focus text/topic | |

### nlm data-table create

Extract structured data as a table.

```bash
nlm data-table create <notebook-id> <description> [OPTIONS]
```

**Note**: `<description>` is a **required positional argument** describing what data to extract.

---

## Studio Commands

### nlm studio status

List all generated artifacts in a notebook.

```bash
nlm studio status <notebook-id> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--json` | Output as JSON |
| `--full` | Show all details |
| `--profile` | Use specific profile |

### nlm studio delete

Delete a generated artifact.

```bash
nlm studio delete <notebook-id> <artifact-id> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--confirm` | **Required** to confirm deletion |
| `--profile` | Use specific profile |
---

## Download Commands

### nlm download

Download generated artifacts to local files.

```bash
nlm download <type> <notebook-id> <output-path> [OPTIONS]
```

**Available types:** `audio`, `video`, `report`, `mind-map`, `slides`, `infographic`, `quiz`, `flashcards`, `data-table`

| Option | Description |
|--------|-------------|
| `--artifact-id` | Specific artifact ID (uses latest if omitted) |
| `--format` | Output format for quiz/flashcards: `json`, `markdown`, `html` |
| `--profile` | Use specific profile |

**Examples:**
```bash
nlm download audio <nb-id> podcast.mp3
nlm download video <nb-id> video.mp4
nlm download report <nb-id> report.md
nlm download quiz <nb-id> quiz.html --format html
nlm download flashcards <nb-id> cards.json --format json
```

---

## Export Commands

### nlm export

Export artifacts to Google Docs or Sheets.

```bash
nlm export <type> <notebook-id> <artifact-id> [OPTIONS]
```

**Available types:** `docs`, `sheets`

| Option | Description |
|--------|-------------|
| `--title` | Title for the exported document |
| `--profile` | Use specific profile |

**Examples:**
```bash
nlm export sheets <nb-id> <artifact-id> --title "Data Table Export"
nlm export docs <nb-id> <artifact-id> --title "My Report"
```

---

## Sharing Commands

### nlm share status

Get current sharing settings for a notebook.

```bash
nlm share status <notebook-id> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--profile` | Use specific profile |

### nlm share public

Enable or disable public link sharing.

```bash
nlm share public <notebook-id> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--off` | Disable public sharing (default: enable) |
| `--profile` | Use specific profile |

**Examples:**
```bash
nlm share public <nb-id>         # Enable public link
nlm share public <nb-id> --off   # Disable public link
```

### nlm share invite

Invite a collaborator by email.

```bash
nlm share invite <notebook-id> <email> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--role` | `viewer` (default) or `editor` |
| `--profile` | Use specific profile |

**Examples:**
```bash
nlm share invite <nb-id> user@example.com
nlm share invite <nb-id> user@example.com --role editor
```

---

## Note Commands

### nlm note create

Create a note in a notebook.

```bash
nlm note create <notebook-id> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--content` | Note content (required) |
| `--title` | Note title |
| `--profile` | Use specific profile |

### nlm note list

List all notes in a notebook.

```bash
nlm note list <notebook-id> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--json` | Output as JSON |
| `--profile` | Use specific profile |

### nlm note update

Update an existing note.

```bash
nlm note update <notebook-id> <note-id> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--content` | New content |
| `--title` | New title |
| `--profile` | Use specific profile |

### nlm note delete

Delete a note permanently.

```bash
nlm note delete <notebook-id> <note-id> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--confirm` | **Required** to confirm deletion |
| `--profile` | Use specific profile |

## Chat Commands

### nlm chat start

Start interactive chat REPL session.

```bash
nlm chat start <notebook-id> [OPTIONS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--profile` | `-p` | Use specific profile |

**REPL Commands:**
- `/sources` - List available sources
- `/clear` - Reset conversation context
- `/help` - Show available commands
- `/exit` - Exit the REPL

### nlm chat configure

Configure chat behavior for a notebook.

```bash
nlm chat configure <notebook-id> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--goal` | `default`, `learning_guide`, `custom` |
| `--prompt` | Custom system prompt (required when goal is `custom`) |
| `--response-length` | `default`, `longer`, `shorter` |
| `--profile` | Use specific profile |

---

## Alias Commands

### nlm alias set

Create or update an alias for a UUID.

```bash
nlm alias set <name> <uuid>
```

Type is auto-detected (notebook, source, artifact, task).

### nlm alias get

Resolve an alias to its UUID.

```bash
nlm alias get <name>
```

### nlm alias list

List all aliases.

```bash
nlm alias list
```

### nlm alias delete

Delete an alias.

```bash
nlm alias delete <name>
```

---

## Config Commands

### nlm config show

Display current configuration.

```bash
nlm config show [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--json` | Output as JSON instead of TOML |

### nlm config get

Get a specific configuration value.

```bash
nlm config get <key>
```

### nlm config set

Set a configuration value.

```bash
nlm config set <key> <value>
```

**Available Configuration Keys:**

| Key | Default | Description |
|-----|---------|-------------|
| `output.format` | `table` | Default output format (table, json) |
| `output.color` | `true` | Enable colored output |
| `output.short_ids` | `true` | Show shortened IDs |
| `auth.browser` | `auto` | Browser for login (auto, chrome, chromium) |
| `auth.default_profile` | `default` | Profile to use when `--profile` not specified |

**Example**: Set default profile to avoid typing `--profile` for every command:

```bash
# Preferred method (simpler)
nlm login switch work

# Alternative method (via config)
nlm config set auth.default_profile work
```
