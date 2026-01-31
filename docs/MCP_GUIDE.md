# MCP Guide

Complete reference for the NotebookLM MCP server - **29 tools** for AI assistants.

## Installation

```bash
# Install the package
uv tool install notebooklm-mcp-cli

# Add to Claude Code
claude mcp add --scope user notebooklm-mcp notebooklm-mcp

# Add to Gemini CLI
gemini mcp add --scope user notebooklm-mcp notebooklm-mcp
```

## Authentication

Before using MCP tools, authenticate:

```bash
nlm login
```

Or use the standalone auth tool:
```bash
notebooklm-mcp-auth
```

---

## Tool Reference

### Notebooks (6 tools)

| Tool | Description |
|------|-------------|
| `notebook_list` | List all notebooks |
| `notebook_create` | Create new notebook |
| `notebook_get` | Get notebook details with sources |
| `notebook_describe` | Get AI summary and suggested topics |
| `notebook_rename` | Rename a notebook |
| `notebook_delete` | Delete notebook (requires `confirm=True`) |

### Sources (6 tools)

| Tool | Description |
|------|-------------|
| `source_add` | **Unified** - Add URL, text, file, or Drive source |
| `source_list_drive` | List sources with Drive freshness status |
| `source_sync_drive` | Sync stale Drive sources |
| `source_delete` | Delete source (requires `confirm=True`) |
| `source_describe` | Get AI summary with keywords |
| `source_get_content` | Get raw text content |

**`source_add` parameters:**
```python
source_add(
    notebook_id="...",
    source_type="url",        # url | text | file | drive
    url="https://...",        # for source_type=url
    text="...",               # for source_type=text
    title="...",              # optional title
    file_path="/path/to.pdf", # for source_type=file
    document_id="...",        # for source_type=drive
    doc_type="doc",           # doc | slides | sheets | pdf
    wait=True,                # wait for processing to complete
    wait_timeout=120.0        # seconds to wait
)
```

### Querying (2 tools)

| Tool | Description |
|------|-------------|
| `notebook_query` | Ask AI about sources in notebook |
| `chat_configure` | Set chat goal and response length |

### Studio Content (3 tools)

| Tool | Description |
|------|-------------|
| `studio_create` | **Unified** - Create any artifact type |
| `studio_status` | Check generation progress |
| `studio_delete` | Delete artifact (requires `confirm=True`) |

**`studio_create` artifact types:**
- `audio` - Podcast (formats: deep_dive, brief, critique, debate)
- `video` - Video overview (formats: explainer, brief)
- `report` - Text report (Briefing Doc, Study Guide, Blog Post)
- `quiz` - Multiple choice quiz
- `flashcards` - Study flashcards
- `mind_map` - Visual mind map
- `slide_deck` - Presentation slides
- `infographic` - Visual infographic
- `data_table` - Structured data table

### Downloads (1 tool)

| Tool | Description |
|------|-------------|
| `download_artifact` | **Unified** - Download any artifact type |

**`download_artifact` types:**
`audio`, `video`, `report`, `mind_map`, `slide_deck`, `infographic`, `data_table`, `quiz`, `flashcards`

### Exports (1 tool)

| Tool | Description |
|------|-------------|
| `export_artifact` | Export to Google Docs/Sheets |

### Research (3 tools)

| Tool | Description |
|------|-------------|
| `research_start` | Start web/Drive research |
| `research_status` | Poll research progress |
| `research_import` | Import discovered sources |

### Notes (1 unified tool)

| Tool | Description |
|------|-------------|
| `note` | **Unified** - Manage notes (action: list, create, update, delete) |

**`note` actions:**
```python
note(notebook_id, action="list")             # List all notes
note(notebook_id, action="create", content="...", title="...")
note(notebook_id, action="update", note_id="...", content="...")
note(notebook_id, action="delete", note_id="...", confirm=True)
```

### Sharing (3 tools)

| Tool | Description |
|------|-------------|
| `notebook_share_status` | Get sharing settings |
| `notebook_share_public` | Enable/disable public link |
| `notebook_share_invite` | Invite collaborator by email |

### Auth (2 tools)

| Tool | Description |
|------|-------------|
| `refresh_auth` | Reload auth tokens |
| `save_auth_tokens` | Save cookies (fallback method) |

### Server (1 tool)

| Tool | Description |
|------|-------------|
| `server_info` | Get version and check for updates |

---

## Example Workflows

### Research → Podcast

```
1. research_start(query="AI trends 2026", mode="deep")
2. research_status(notebook_id, max_wait=300)  # wait for completion
3. research_import(notebook_id, task_id)
4. studio_create(notebook_id, artifact_type="audio", confirm=True)
5. studio_status(notebook_id)  # poll until complete
6. download_artifact(notebook_id, artifact_type="audio", output_path="podcast.mp3")
```

### Add Sources with Wait

```
source_add(notebook_id, source_type="url", url="https://...", wait=True)
# Returns when source is fully processed and ready for queries
```

### Generate Study Materials

```
studio_create(notebook_id, artifact_type="quiz", question_count=10, confirm=True)
studio_create(notebook_id, artifact_type="flashcards", difficulty="hard", confirm=True)
studio_create(notebook_id, artifact_type="report", report_format="Study Guide", confirm=True)
```

---

## Configuration

### MCP Server Options

| Flag | Description | Default |
|------|-------------|---------|
| `--transport` | Protocol (stdio, http, sse) | stdio |
| `--port` | Port for HTTP/SSE | 8000 |
| `--debug` | Enable verbose logging | false |

### Environment Variables

| Variable | Description |
|----------|-------------|
| `NOTEBOOKLM_MCP_TRANSPORT` | Transport type |
| `NOTEBOOKLM_MCP_PORT` | HTTP/SSE port |
| `NOTEBOOKLM_MCP_DEBUG` | Enable debug logging |
| `NOTEBOOKLM_QUERY_TIMEOUT` | Query timeout (seconds) |

---

## Context Window Tips

This MCP has **29 tools** which consume context. Best practices:

- **Disable when not using**: In Claude Code, use `@notebooklm-mcp` to toggle
- **Use unified tools**: `source_add`, `studio_create`, `download_artifact` handle multiple operations each
- **Poll wisely**: Use `studio_status` sparingly - artifacts take 1-5 minutes

---

## IDE Configuration

### Claude Code
```bash
claude mcp add --scope user notebooklm-mcp notebooklm-mcp
```

### Cursor / VS Code
Add to `~/.cursor/mcp.json` or `~/.vscode/mcp.json`:
```json
{
  "mcpServers": {
    "notebooklm-mcp": {
      "command": "/path/to/notebooklm-mcp"
    }
  }
}
```

### Gemini CLI
```bash
gemini mcp add --scope user notebooklm-mcp notebooklm-mcp
```
