---
name: nlm-notebook
description: "NotebookLM notebook management — create, list, get, rename, delete, query, and describe notebooks. Use this when the user wants to manage their NotebookLM notebooks programmatically."
metadata:
  openclaw:
    category: "productivity"
    requires:
      bins: ["nlm"]
    cliHelp: "nlm notebook --help"
---

# nlm notebook

Manage Google NotebookLM notebooks.

## See Also

- **[nlm-skill](../nlm-skill/SKILL.md)** — Full reference including auth, sources, and studio
- **[nlm-source](../nlm-source/SKILL.md)** — Add and manage sources in a notebook
- **[nlm-studio](../nlm-studio/SKILL.md)** — Generate content from notebook sources

## Authentication

```bash
nlm login              # Required before first use
nlm login --check      # Validate session is active
```

Sessions expire in ~20 minutes. Re-run `nlm login` if commands fail.

## CLI Commands

```bash
# List
nlm notebook list                    # All notebooks (table)
nlm notebook list --json             # JSON for parsing
nlm notebook list --quiet            # IDs only (for piping)

# Create / Get
nlm notebook create "Title"          # Returns notebook ID
nlm notebook get <id>                # Full details

# AI Operations
nlm notebook describe <id>           # AI summary + keywords
nlm notebook query <id> "question"   # One-shot Q&A with sources
nlm notebook query <id> "question" --conversation-id <cid>  # Follow-up

# Rename / Delete
nlm notebook rename <id> "New Title"
nlm notebook delete <id> --confirm   # IRREVERSIBLE — confirm with user first

# Chat configuration
nlm chat configure <id> --goal default
nlm chat configure <id> --goal learning_guide
nlm chat configure <id> --goal custom --prompt "Act as a tutor..."
nlm chat configure <id> --response-length longer
```

> ⚠️ **DO NOT use `nlm chat start`** — it opens an interactive REPL that AI tools cannot control. Use `nlm notebook query` for one-shot Q&A.

## MCP Tools

| Tool | Description |
|------|-------------|
| `notebook_list` | List all notebooks |
| `notebook_create` | Create a notebook |
| `notebook_get` | Get notebook details |
| `notebook_describe` | AI summary + keywords |
| `notebook_query` | Ask a question (AI answer) |
| `notebook_rename` | Rename a notebook |
| `notebook_delete` | Delete (requires `confirm=True`) |
| `chat_configure` | Configure chat goal/style |

## Aliases

Simplify long UUIDs with aliases:

```bash
nlm alias set research <notebook-id>
nlm notebook query research "What are the key findings?"
```

## Examples

```bash
# Create and immediately query
ID=$(nlm notebook create "Market Research" --quiet)
nlm source add $ID --url "https://example.com/report"
nlm notebook query $ID "What are the main trends?"

# Rename then describe
nlm notebook rename $ID "Q4 Market Research"
nlm notebook describe $ID
```
