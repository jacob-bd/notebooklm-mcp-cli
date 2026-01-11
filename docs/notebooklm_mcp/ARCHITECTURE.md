# NotebookLM MCP Architecture

**Last Updated**: 2026-01-10
**Version**: 0.1.0

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      NotebookLM MCP Server                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                       MCP Layer                                   │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │  │
│  │  │ FastMCP     │  │ Tool        │  │ Resource    │              │  │
│  │  │ Server      │  │ Definitions │  │ Handlers    │              │  │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │  │
│  │         │                │                │                      │  │
│  │         └────────────────┴────────────────┘                      │  │
│  │                          │                                        │  │
│  │                   server.py (31 tools)                           │  │
│  └──────────────────────────┼────────────────────────────────────────┘  │
│                             │                                           │
│  ┌──────────────────────────┼────────────────────────────────────────┐  │
│  │                    API Layer                                      │  │
│  │                                                                   │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │  │
│  │  │ HTTP Client │  │ RPC Builder │  │ Response    │              │  │
│  │  │ (httpx)     │  │             │  │ Parser      │              │  │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │  │
│  │         │                │                │                      │  │
│  │         └────────────────┴────────────────┘                      │  │
│  │                          │                                        │  │
│  │                   api_client.py                                   │  │
│  └──────────────────────────┼────────────────────────────────────────┘  │
│                             │                                           │
│  ┌──────────────────────────┼────────────────────────────────────────┐  │
│  │                    Auth Layer                                     │  │
│  │                                                                   │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │  │
│  │  │ Token Cache │  │ Cookie      │  │ CSRF/Session│              │  │
│  │  │ (JSON file) │  │ Parser      │  │ Extractor   │              │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘              │  │
│  │                                                                   │  │
│  │                   auth.py + auth_cli.py                          │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │ NotebookLM Internal API │
                    │ (batchexecute endpoint) │
                    └─────────────────────────┘
```

## Core Principles

1. **Reverse-engineered API**: Uses undocumented internal batchexecute RPC endpoints
2. **Cookie-based auth**: Browser cookies for authentication (no official API)
3. **Auto-extraction**: CSRF tokens and session IDs auto-extracted on init
4. **Confirmation patterns**: Destructive operations require explicit `confirm=True`
5. **Token-efficient responses**: Compact output for MCP tool results

## Component Details

### MCP Server (`server.py`)

FastMCP server providing 31 tools across categories:

| Category | Tools |
|----------|-------|
| Notebook Management | `notebook_list`, `notebook_create`, `notebook_get`, `notebook_describe`, `notebook_rename`, `notebook_delete` |
| Source Management | `notebook_add_url`, `notebook_add_text`, `notebook_add_drive`, `source_describe`, `source_list_drive`, `source_sync_drive`, `source_delete` |
| AI Queries | `notebook_query`, `chat_configure` |
| Research | `research_start`, `research_status`, `research_import` |
| Studio Content | `audio_overview_create`, `video_overview_create`, `infographic_create`, `slide_deck_create`, `report_create`, `flashcards_create`, `quiz_create`, `data_table_create`, `mind_map_create`, `mind_map_list`, `studio_status`, `studio_delete` |
| Auth | `save_auth_tokens` |

### API Client (`api_client.py`)

Reverse-engineered HTTP client for NotebookLM internal APIs:

**Key Methods:**
```python
# Notebook operations
list_notebooks() -> List[dict]
create_notebook(title) -> dict
get_notebook(notebook_id) -> dict
delete_notebook(notebook_id) -> bool

# Source operations
add_url_source(notebook_id, url) -> dict
add_text_source(notebook_id, text, title) -> dict
add_drive_source(notebook_id, doc_id, title, doc_type) -> dict

# Query operations
query_notebook(notebook_id, query, source_ids, conversation_id) -> dict

# Studio operations
create_audio_overview(notebook_id, format, length, ...) -> dict
create_video_overview(notebook_id, format, style, ...) -> dict
get_studio_status(notebook_id) -> dict
```

**RPC Protocol:**
- Endpoint: `https://notebooklm.google.com/v1alpha1/batchexecute`
- Format: Nested array structures with RPC IDs
- Response: Multi-part batchexecute response parsing

### Auth System (`auth.py`, `auth_cli.py`)

**Token Storage:**
```
~/.notebooklm-mcp/
├── auth.json           # Cached cookies, CSRF, session ID
└── chrome-profile/     # Dedicated Chrome profile for auth
```

**Token Lifecycle:**
| Token | Duration | Refresh |
|-------|----------|---------|
| Cookies | ~2-4 weeks | Re-extract from Chrome |
| CSRF | Per session | Auto-extracted on init |
| Session ID | Per session | Auto-extracted on init |

**Auth CLI Modes:**
- **Auto mode** (default): Launches Chrome, user logs in, cookies extracted
- **File mode** (`--file`): Manual cookie extraction from DevTools

## Data Flow

### Tool Call Flow
```
AI Assistant → MCP Protocol → FastMCP Server
                                   │
                                   ▼
                            Tool Handler
                                   │
                                   ▼
                            API Client Method
                                   │
                                   ▼
                            Build RPC Request
                                   │
                                   ▼
                            HTTP POST (batchexecute)
                                   │
                                   ▼
                            Parse Response
                                   │
                                   ▼
                            Return to Tool Handler
                                   │
                                   ▼
                            Format MCP Response
```

### Auth Flow
```
notebooklm-mcp-auth
        │
        ▼
Launch Chrome (dedicated profile)
        │
        ▼
User logs in to Google
        │
        ▼
Navigate to NotebookLM
        │
        ▼
Extract cookies via CDP
        │
        ▼
Parse CSRF token from page
        │
        ▼
Save to ~/.notebooklm-mcp/auth.json
```

## Request/Response Format

### RPC Request Structure
```python
# Batchexecute request format
[
    [
        [
            "RPC_ID",           # e.g., "wJbB3c" for list notebooks
            json.dumps(params), # Nested parameter array
            None,
            "generic"
        ]
    ]
]
```

### Response Parsing
```python
# Batchexecute response format
)]}'  # Security prefix (stripped)

[[["wrb.fr","RPC_ID","[nested_json_array]",null,null,null,"generic"]]]
```

## Confirmation Pattern

Destructive operations require explicit confirmation:

```python
# Without confirmation - returns preview/warning
notebook_delete(notebook_id, confirm=False)
# Returns: {"status": "confirm_required", "message": "..."}

# With confirmation - executes operation
notebook_delete(notebook_id, confirm=True)
# Returns: {"status": "success", ...}
```

**Operations requiring confirmation:**
- `notebook_delete`
- `source_delete`
- `source_sync_drive`
- All studio creation tools
- `studio_delete`

## Integration Points

| Component | Purpose |
|-----------|---------|
| FastMCP | MCP server framework |
| httpx | Async HTTP client |
| Chrome CDP | Cookie extraction (auth CLI) |
| Selenium | Browser automation (auth CLI) |

## Related Documentation

- [CODE_TOUR.md](CODE_TOUR.md) - Navigate the codebase
- [OPERATIONS.md](OPERATIONS.md) - Day-to-day operation
- [../API_REFERENCE.md](../API_REFERENCE.md) - Detailed API documentation
