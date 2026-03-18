---
name: nlm-source
description: "NotebookLM source management — add, list, describe, read content, rename, delete, and sync Drive sources. Use when adding URLs, YouTube videos, text, files, or Google Drive documents to a notebook."
metadata:
  openclaw:
    category: "productivity"
    requires:
      bins: ["nlm"]
    cliHelp: "nlm source --help"
---

# nlm source

Add and manage sources in a NotebookLM notebook.

## See Also

- **[nlm-skill](../nlm-skill/SKILL.md)** — Full reference
- **[nlm-notebook](../nlm-notebook/SKILL.md)** — Notebook management
- **[recipe-drive-to-podcast](../recipe-drive-to-podcast/SKILL.md)** — Drive → podcast workflow

## Source Types

| Type | Flag | Description |
|------|------|-------------|
| URL / YouTube | `--url` | Web page or YouTube video |
| Pasted text | `--text` + `--title` | Raw text content |
| Local file | `--file` | PDF, TXT, DOCX, etc. |
| Google Drive | `--drive` | Doc, Slides, Sheets, PDF |

Drive `--type` values: `doc`, `slides`, `sheets`, `pdf` (auto-detected if omitted)

## CLI Commands

```bash
# Add sources
nlm source add <nb-id> --url "https://example.com"
nlm source add <nb-id> --url "https://youtube.com/watch?v=..."
nlm source add <nb-id> --text "content here" --title "My Notes"
nlm source add <nb-id> --file /path/to/document.pdf
nlm source add <nb-id> --drive 1KQH3eW0hMBp7WK...              # Auto-detect type
nlm source add <nb-id> --drive 1KQH3eW0hMBp7WK... --type slides

# List sources
nlm source list <nb-id>                     # Table view
nlm source list <nb-id> --drive             # Include Drive freshness
nlm source list <nb-id> --drive -S          # Skip freshness check (faster)
nlm source list <nb-id> --json              # JSON output

# Inspect a source
nlm source get <source-id>                  # Metadata
nlm source describe <source-id>             # AI summary + keywords
nlm source content <source-id>              # Raw text (no AI)
nlm source content <source-id> -o out.txt   # Export to file

# Manage stale Drive sources
nlm source stale <nb-id>                    # List outdated Drive sources
nlm source sync <nb-id> --confirm           # Sync all stale
nlm source sync <nb-id> --source-ids <id1,id2> --confirm  # Sync specific

# Rename
nlm source rename <source-id> "New Title" --notebook <nb-id>
nlm rename source <source-id> "New Title" --notebook <nb-id>  # verb-first

# Delete (IRREVERSIBLE — confirm with user first)
nlm source delete <source-id> --confirm
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `source_add` | Add source (url/text/file/drive) |
| `source_list_drive` | List Drive sources + freshness |
| `source_describe` | AI summary + keywords |
| `source_get_content` | Raw text (no AI) |
| `source_rename` | Rename a source |
| `source_sync_drive` | Sync stale Drive sources (requires `confirm=True`) |
| `source_delete` | Delete source (requires `confirm=True`) |

### MCP source_add examples

```python
# URL
source_add(notebook_id="...", source_type="url", url="https://example.com")

# Text
source_add(notebook_id="...", source_type="text", text="content", title="Title")

# Drive
source_add(notebook_id="...", source_type="drive", document_id="1KQH3...", doc_type="doc")
```

## Workflow: Add Multiple Sources

```bash
NB_ID="your-notebook-id"

# Batch add from URLs
for url in "https://site1.com" "https://site2.com" "https://site3.com"; do
    nlm source add $NB_ID --url "$url"
    sleep 2  # avoid rate limits
done

nlm source list $NB_ID
```

## Drive Sync Workflow

```bash
# 1. Check which Drive sources are stale
nlm source stale <nb-id>

# 2. Review what will be synced, then confirm
nlm source sync <nb-id> --confirm
```

Always show the user stale sources via `nlm source stale` before syncing.
