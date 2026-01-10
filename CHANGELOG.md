# Changelog

All notable changes to NotebookLM MCP Server are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Version numbers in pyproject.toml (no git tags).

## [Unreleased]

(No unreleased changes)

## [0.1.0] - 2026-01-10

### Added
- **Doc-Refresh Ralph Loop** (v0.3.0):
  - Canonical document discovery (Tier 1/2/3)
  - Hash-based change detection
  - NotebookLM source synchronization with deterministic titles
  - Standard 7 artifact refresh (mind map, briefing doc, study guide, audio, infographic, flashcards, quiz)
  - `--force`, `--artifacts`, `--skip-artifacts` CLI flags
  - Delta-based trigger logic (>15% change or major version bump)

- **MCP Tools** (31 total):
  - Notebook management: `notebook_list`, `notebook_create`, `notebook_get`, `notebook_describe`, `notebook_rename`, `notebook_delete`
  - Source management: `notebook_add_url`, `notebook_add_text`, `notebook_add_drive`, `source_describe`, `source_list_drive`, `source_sync_drive`, `source_delete`
  - Chat: `notebook_query`, `chat_configure`
  - Research: `research_start`, `research_status`, `research_import`
  - Studio: `audio_overview_create`, `video_overview_create`, `infographic_create`, `slide_deck_create`, `report_create`, `flashcards_create`, `quiz_create`, `data_table_create`, `mind_map_create`, `mind_map_list`, `studio_status`, `studio_delete`
  - Auth: `save_auth_tokens`

- **Authentication**:
  - Cookie-based auth with auto-extraction of CSRF token and session ID
  - Token caching in `~/.notebooklm-mcp/`
  - Auto-retry logic for auth token rotation
  - CLI tool `notebooklm-mcp-auth` for Chrome-based extraction

- **Documentation**:
  - Comprehensive CLAUDE.md with session recovery guidance
  - API reference (`docs/API_REFERENCE.md`)
  - Troubleshooting guide (`docs/TROUBLESHOOTING.md`)
  - MCP test plan (`docs/MCP_TEST_PLAN.md`)

### Technical Notes
- Reverse-engineered NotebookLM internal APIs (batchexecute RPC)
- Tested with personal/free tier accounts
- Python >=3.11 required
- FastMCP 2.14.2 for MCP protocol
