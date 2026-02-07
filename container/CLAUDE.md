# Container - NotebookLM MCP Server in Go

## Overview

This directory contains a standalone Go implementation of the NotebookLM MCP server, designed to run as a container. It is functionally equivalent to the Python MCP server in the parent repo but is completely independent — it shares no code and has no runtime dependency on the Python implementation.

**Reference the Python source** in `src/notebooklm_tools/` and `docs/API_REFERENCE.md` for behavior parity, but never import or modify those files.

## Development Commands

```bash
# Build
go build -o notebooklm-mcp ./cmd/server

# Run (stdio transport - default)
./notebooklm-mcp

# Run (HTTP transport)
./notebooklm-mcp --transport http --port 8000

# Run tests
go test ./...

# Run with race detector
go test -race ./...

# Docker build
docker build -t notebooklm-mcp .

# Docker run (HTTP mode)
docker run -p 8000:8000 -e NOTEBOOKLM_COOKIES="..." notebooklm-mcp
```

## Architecture (implemented)

```
container/
├── CLAUDE.md              # This file
├── Dockerfile             # Multi-stage build (scratch base, ~6.4MB)
├── .dockerignore
├── go.mod                 # Zero external dependencies
├── cmd/
│   └── server/
│       └── main.go        # Entry point, CLI flags, transport selection
├── internal/
│   ├── auth/
│   │   └── auth.go        # Cookie/CSRF/session management (in-memory)
│   ├── api/               # NotebookLM HTTP API client
│   │   ├── client.go      # Base batchexecute HTTP client
│   │   ├── rpc.go         # RPC ID constants
│   │   ├── parse.go       # Anti-XSSI + double-encoded JSON parser
│   │   ├── notebooks.go   # Notebook CRUD
│   │   ├── sources.go     # Source add/delete/sync/content/guide
│   │   ├── query.go       # Streaming query endpoint
│   │   ├── research.go    # Research start/poll/import
│   │   ├── studio.go      # Studio create/status/delete/rename
│   │   ├── sharing.go     # Share status/public/invite
│   │   ├── notes.go       # Note CRUD
│   │   ├── describe.go    # Notebook describe (AI summary)
│   │   └── exports.go     # Export to Google Docs/Sheets
│   ├── mcp/               # MCP protocol layer
│   │   ├── server.go      # JSON-RPC 2.0 server
│   │   ├── tools.go       # All 29 tool definitions + handlers (~936 lines)
│   │   ├── transport.go   # stdio + HTTP transports
│   │   └── types.go       # MCP protocol types
│   └── constants/
│       └── codes.go       # Bidirectional name↔code mappings
└── (4,027 lines of Go, ~6.4MB stripped binary, zero deps)
```

## Key Design Decisions

1. **No CGo** — Pure Go for maximum portability and minimal container image size.
2. **`internal/`** — All packages under `internal/` to prevent external imports.
3. **Minimal dependencies** — Prefer stdlib. Use only well-maintained, necessary libraries.
4. **Context propagation** — All API calls accept `context.Context` for cancellation/timeout.
5. **Structured logging** — Use `log/slog` (stdlib, Go 1.21+).
6. **Configuration via env vars** — No config files inside the container; everything via environment variables.

## NotebookLM API Summary

**Base URL:** `https://notebooklm.google.com`
**RPC endpoint:** `POST /_/LabsTailwindUi/data/batchexecute`
**Query endpoint:** `POST /_/LabsTailwindUi/data/google.internal.labs.tailwind.orchestration.v1.LabsTailwindOrchestrationService/GenerateFreeFormStreamed`

### Authentication

- **Cookies** (required): Full cookie header from Chrome DevTools
- **CSRF token** (auto-extracted): `SNlM0e` value from HTML page
- **Session ID** (auto-extracted): `FdrFJe` value from HTML page

### Request Format

```
Content-Type: application/x-www-form-urlencoded;charset=UTF-8
Body: f.req=<url_encoded_json>&at=<csrf_token>&
URL params: rpcids, source-path, bl, f.sid, hl, _reqid, rt=c
```

Where `f.req` contains: `[[["RPC_ID", "<params_json>", null, "generic"]]]`

### Response Format

```
)]}'           ← anti-XSSI prefix, MUST strip
<byte_count>
<json_array>
```

### RPC IDs (complete reference in docs/API_REFERENCE.md)

| RPC ID | Operation |
|--------|-----------|
| `wXbhsf` | List notebooks |
| `rLM1Ne` | Get notebook |
| `CCqFvf` | Create notebook |
| `s0tc2d` | Rename notebook / Configure chat |
| `WWINqb` | Delete notebook |
| `izAoDd` | Add source (URL/text/Drive) |
| `hizoJc` | Get source details |
| `yR9Yof` | Check source freshness |
| `FLmJqe` | Sync Drive source |
| `tGMBJ` | Delete source |
| `Ljjv0c` | Start fast research |
| `QA9ei` | Start deep research |
| `e3bVqc` | Poll research results |
| `LBwxtb` | Import research sources |
| `R7cb6c` | Create studio content (audio/video/report/etc) |
| `gArtLc` | Poll studio status |
| `V5N4be` | Delete studio content |
| `rc3d8d` | Rename studio artifact |
| `yyryJe` | Generate mind map |
| `CYK0Xb` | Save mind map / Create note |
| `cFji9` | List mind maps / notes |
| `cYAfTb` | Update note |
| `AH0mwd` | Delete mind map / note |
| `VfAZjd` | Get notebook summary |
| `tr032e` | Get source guide |
| `QDyure` | Set sharing settings |
| `JFMDGd` | Get share status |
| `Krh3pd` | Export to Google Docs/Sheets |
| `v9rmvd` | Get interactive HTML (quiz/flashcards) |

## MCP Tools to Implement (29 total)

### Auth (2)
- `save_auth_tokens` — Save cookies
- `refresh_auth` — Reload/refresh auth tokens

### Notebooks (6)
- `notebook_list` — List all notebooks
- `notebook_get` — Get details with sources
- `notebook_describe` — AI summary with keywords
- `notebook_create` — Create new notebook
- `notebook_rename` — Rename notebook
- `notebook_delete` — Delete (requires confirm)

### Sources (6)
- `source_add` — Add URL/text/Drive/file source
- `source_describe` — AI summary of source
- `source_get_content` — Raw text content
- `source_list_drive` — List with Drive freshness
- `source_sync_drive` — Sync stale sources (requires confirm)
- `source_delete` — Delete source (requires confirm)

### Chat (2)
- `notebook_query` — Ask AI about sources (streaming)
- `chat_configure` — Set chat goal/style/length

### Research (3)
- `research_start` — Start web/Drive research
- `research_status` — Poll progress
- `research_import` — Import discovered sources

### Studio (3)
- `studio_create` — Create audio/video/report/flashcards/quiz/infographic/slides/data_table/mind_map
- `studio_status` — Check generation status / rename artifact
- `studio_delete` — Delete artifact (requires confirm)

### Downloads & Exports (2)
- `download_artifact` — Download any artifact
- `export_artifact` — Export to Google Docs/Sheets

### Sharing (3)
- `notebook_share_status` — Get sharing settings
- `notebook_share_public` — Enable/disable public link
- `notebook_share_invite` — Invite collaborator

### Notes (1 unified tool)
- `note` — Create/list/update/delete notes (action param)

### Server (1)
- `server_info` — Version and update check

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `NOTEBOOKLM_COOKIES` | Yes | Full cookie header |
| `NOTEBOOKLM_CSRF_TOKEN` | No | Auto-extracted from page |
| `NOTEBOOKLM_SESSION_ID` | No | Auto-extracted from page |
| `NOTEBOOKLM_BL` | No | Build label (has default) |
| `NOTEBOOKLM_MCP_TRANSPORT` | No | `stdio` (default), `http`, `sse` |
| `NOTEBOOKLM_MCP_HOST` | No | HTTP host (default `127.0.0.1`) |
| `NOTEBOOKLM_MCP_PORT` | No | HTTP port (default `8000`) |
| `NOTEBOOKLM_MCP_PATH` | No | HTTP endpoint path (default `/mcp`) |
| `NOTEBOOKLM_MCP_STATELESS` | No | Enable stateless HTTP mode |
| `NOTEBOOKLM_MCP_DEBUG` | No | Enable debug logging |
| `NOTEBOOKLM_QUERY_TIMEOUT` | No | Query timeout seconds (default `120`) |

## Code Mappings

These bidirectional name-to-code mappings are used throughout the API:

- **Chat goals:** default=1, custom=2, learning_guide=3
- **Response lengths:** default=1, longer=4, shorter=5
- **Research sources:** web=1, drive=2
- **Research modes:** fast=1, deep=5
- **Source types:** google_docs=1, google_slides_sheets=2, pdf=3, pasted_text=4, web_page=5, generated_text=8, youtube=9, uploaded_file=11, image=13, word_doc=14
- **Studio types:** audio=1, report=2, video=3, flashcards=4, infographic=7, slide_deck=8, data_table=9
- **Audio formats:** deep_dive=1, brief=2, critique=3, debate=4
- **Audio lengths:** short=1, default=2, long=3
- **Video formats:** explainer=1, brief=2
- **Video styles:** auto_select=1, custom=2, classic=3, whiteboard=4, kawaii=5, anime=6, watercolor=7, retro_print=8, heritage=9, paper_craft=10
- **Infographic orientations:** landscape=1, portrait=2, square=3
- **Infographic details:** concise=1, standard=2, detailed=3
- **Slide deck formats:** detailed_deck=1, presenter_slides=2
- **Slide deck lengths:** short=1, default=3
- **Share roles:** owner=1, editor=2, viewer=3
- **Share access:** restricted=0, public=1
- **Export types:** docs=1, sheets=2
