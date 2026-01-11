# NotebookLM MCP Server Overview

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
