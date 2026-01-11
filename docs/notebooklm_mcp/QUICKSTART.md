# NotebookLM MCP Quickstart

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
