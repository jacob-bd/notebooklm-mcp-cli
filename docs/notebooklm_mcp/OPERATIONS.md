# NotebookLM MCP Operations

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
