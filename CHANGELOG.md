# Changelog

All notable changes to NotebookLM MCP Server are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Version numbers in pyproject.toml (no git tags).

## [Unreleased]

### Added
- CI workflow (`.github/workflows/ci.yml`) to run tests, coverage report, and package build on push/PR.
- `doc-refresh` console script entrypoint for the doc-refresh runner.
- Regression tests for sync safety, artifact completion polling, major-version detection, and cookie parsing.

### Changed
- Doc-refresh runtime notebook map now defaults to `~/.config/notebooklm-mcp/notebook_map.yaml`.
- Added a packaged `notebook_map.template.yaml` bootstrap file instead of bundling mutable runtime state.
- Security and code-tour docs updated to reflect persisted local doc-refresh state.

### Fixed
- Replacement sync flow now adds new content before deleting old source (prevents source loss on failed add).
- Artifact completion polling now verifies completion using the exact artifact IDs created in the run.
- Major version bump detection now compares stored `meta_version` with current `META.yaml` version.
- `save_auth_tokens` now parses cookie headers with or without spaces after semicolons.

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
