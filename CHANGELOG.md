# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.19] - 2026-02-10

### Added
- **Automatic retry on server errors** — Transient errors (429, 500, 502, 503, 504) are now retried up to 3 times with exponential backoff. Special thanks to **@sebsnyk** for the suggestion in #42.
- **`--json` flag for more commands** — Added structured JSON output to `notebook describe`, `notebook query`, `source describe`, and `source content`. JSON output is also auto-detected when piping. Thanks to **@sebsnyk** for the request in #43.

### Changed
- **Error handling priority** — Server error retry now executes *before* authentication recovery.
- **AI docs & Skills updated** — specific documentation on retry behavior and expanded `--json` flags.

## [0.2.18] - 2026-02-09

### Added
- **Claude Desktop Extension (.mcpb)** — One-click install for Claude Desktop. Download the `.mcpb` file from the release page, double-click to install. No manual config editing required.
- **MCPB build automation** — `scripts/build_mcpb.py` reads version from `pyproject.toml`, syncs `manifest.json`, and packages the `.mcpb` file. Old builds are auto-cleaned.
- **GitHub Actions release asset** — `.mcpb` file is automatically built and attached to GitHub Releases alongside PyPI publish.
- **`nlm doctor` and `nlm setup` documentation** — Added to AI docs (`nlm --ai`) and skill file.

### Changed
- **Manifest uses `uvx`** — Claude Desktop extension now uses `uvx --from notebooklm-mcp-cli notebooklm-mcp` for universal PATH compatibility.

### Removed
- Cleaned up `PROJECT_RECAP.md` and `todo.md` (outdated development artifacts).

## [0.2.17] - 2026-02-08

### Added
- **`nlm setup` command** - Automatically configure NotebookLM MCP for AI tools (Claude Code, Claude Desktop, Gemini CLI, Cursor, Windsurf). No more manual JSON editing! Thanks to **@997unix** for this contribution (PR #39)
  - `nlm setup list` - Show configuration status for all supported clients
  - `nlm setup add <client>` - Add MCP server config to a client
  - `nlm setup remove <client>` - Remove MCP server config
- **`nlm doctor` command** - Diagnose installation and configuration issues in one command. Checks authentication, Chrome profiles, and AI tool configurations. Also by **@997unix** (PR #39)

### Fixed
- **Version check not running** - Update notifications were never shown after CLI commands because `typer.Exit` exceptions bypassed the check. Moved `print_update_notification()` to a `finally` block so it always runs.
- **Missing import in setup.py** - Fixed `import os` placement for Windows compatibility

## [0.2.16] - 2026-02-05

### Fixed
- **Windows JSON parse errors** - Added `show_banner=False` to `mcp.run()` to prevent FastMCP banner from corrupting stdio JSON-RPC protocol on Windows (fixes #35)
- **Stdout pollution in MCP mode** - Replaced `print()` with logging in `auth.py` and `notebooks.py` to avoid corrupting JSON-RPC output
- **Profile handling in login check** - Fixed `nlm login --check` to use config's `default_profile` instead of hardcoded "default"

## [0.2.15] - 2026-02-04

### Fixed
- **Chat REPL command broken** - Fixed `nlm chat start` failing with `TypeError: BaseClient.__init__() got an unexpected keyword argument 'profile'`. Now uses proper `get_client(profile)` utility and handles dict/list API responses correctly. Thanks to **@eng-M-A-AbelLatif** for the detailed bug report and fix in issue #25!

### Removed
- **Dead code cleanup** - Removed unused `src/notebooklm_mcp/` directory. This legacy code was not packaged or distributed but caused confusion (e.g., PR #29 targeted it thinking it was active). The active MCP server is `notebooklm_tools.mcp.server`. Thanks to **@NOirBRight** for PR #29 which helped identify this dead code.

### Changed
- **Updated tests** - Removed references to deleted `notebooklm_mcp` package from test suite.

### Community Contributors
This release also acknowledges past community contributions that weren't properly thanked:
- **@latuannetnam** for HTTP transport support, debug logging, and query timeout configuration (PR #12)
- **@davidszp** for Linux Chrome detection fix (PR #6) and source_get_content tool (PR #1)
- **@saitrogen** for the research polling query fallback fix (PR #15)

## [0.2.14] - 2026-02-03

### Fixed
- **Automatic migration from old location** - Auth tokens and Chrome profiles are automatically migrated from `~/.notebooklm-mcp/` to `~/.notebooklm-mcp-cli/` on first use. Users upgrading from older versions don't need to re-authenticate.

## [0.2.13] - 2026-02-03

### Fixed
- **Unified storage location** - Consolidated all storage to `~/.notebooklm-mcp-cli/`. Previously some code still referenced the old `~/.notebooklm-mcp/` location, causing confusion. Now everything uses the single unified location.
- **Note**: v0.2.13 was missing migration support - upgrade to v0.2.14 instead.

## [0.2.12] - 2026-02-03

### Removed
- **`notebooklm-mcp-auth` standalone command** - The standalone authentication tool has been officially deprecated and removed. Use `nlm login` instead, which provides all the same functionality with additional features like named profiles. The headless auth for automatic token refresh continues to work behind the scenes.

### Fixed
- **Auth storage inconsistency** - Previously, `notebooklm-mcp-auth` stored tokens in a different location than `nlm login`, causing "Authentication expired" errors. Now there's only one auth path via `nlm login`.
- **Documentation typo** - Fixed `nlm download slides` → `nlm download slide-deck` in CLI guide.

## [0.2.11] - 2026-02-02

### Fixed
- **`nlm login` not launching Chrome** - Running `nlm login` without arguments now properly launches Chrome for authentication instead of showing help. Workaround for v0.2.10: use `nlm login -p default`.

## [0.2.10] - 2026-01-31

### Fixed
- **Version mismatch** - Synchronized version numbers across all package files

## [0.2.9] - 2026-01-31

### Changed
- **Documentation alignment** - Unified MCP and CLI documentation with comprehensive test plan
- **Build configuration** - Moved dev dependencies to optional-dependencies for standard compatibility

### Fixed
- **Studio custom focus prompt** - Extract custom focus prompt from correct position in API response

## [0.2.7] - 2026-01-30

### Removed
- **Redundant CLI commands** - Removed `nlm download-verb` and `nlm research-verb` (use `nlm download` and `nlm research` instead)

### Fixed
- **Documentation alignment** - Synchronized all CLI documentation with actual CLI behavior:
  - Fixed export command syntax: `nlm export to-docs` / `nlm export to-sheets` (not `docs`/`sheets`)
  - Fixed download command syntax: use `-o` flag for output path
  - Fixed slides format values: `detailed_deck` / `presenter_slides` (not `detailed`/`presenter`)
  - Removed non-existent `nlm mindmap list` from documentation

## [0.2.6] - 2026-01-30

### Fixed
- **Source List Display**: Fixed source list showing empty type by using `source_type_name` key correctly

## [0.2.5] - 2026-01-30

### Added
- **Unified Note Tool** - Consolidated 4 separate note tools (`note_create`, `note_list`, `note_update`, `note_delete`) into a single `note(action=...)` tool
- **CLI Shell Completion** - Enabled shell tab completion for `nlm skill` tool argument
- **Documentation Updates** - Updated `SKILL.md`, `command_reference.md`, `troubleshooting.md`, and `workflows.md` with latest features

### Fixed
- Fixed `nlm skill install other` automatically switching to project level
- Fixed `research_status` handling of `None` tasks in response
- Fixed note creation returning failure despite success (timing issue with immediate fetch)

## [0.2.4] - 2026-01-29

### Added
- **Skill Installer for AI Coding Assistants** (`nlm skill` commands)
  - Install NotebookLM skills for Claude Code, OpenCode, Gemini CLI, Antigravity, Cursor, and Codex
  - Support for user-level (`~/.config`) and project-level installation
  - Parent directory validation with smart prompts (create/switch/cancel)
  - Installation status tracking with `nlm skill list`
  - Export all formats with `nlm skill install other`
  - Unified CLI/MCP skill with intelligent tool detection logic
  - Consistent `nlm-skill` folder naming across all installations
  - Complete documentation in AI docs (`nlm --ai`)
- Integration tests for all CLI bug fixes (9 tests covering error handling, parameter passing, alias resolution)
- `nlm login profile rename` command for renaming authentication profiles
- **Multi-profile Chrome isolation** - each authentication profile now uses a separate Chrome session, allowing simultaneous logins to multiple Google accounts
- **Email capture during login** - profiles now display associated Google account email in `nlm login profile list`
- **Default profile configuration** - `nlm config set auth.default_profile <name>` to avoid typing `--profile` for every command
- **Auto-cleanup Chrome profile cache** after authentication to save disk space

### Fixed
- Fixed `console.print` using invalid `err=True` parameter (now uses `err_console = Console(stderr=True)`)
- Fixed verb-first commands passing OptionInfo objects instead of parameter values
- Fixed studio command parameter mismatches (format→format_code, length→length_code, etc.)
- Fixed studio methods not handling `source_ids=None` (now defaults to all notebook sources)

### Changed
- **Consolidated auth commands under login** - replaced `nlm auth status/list/delete` with `nlm login --check` and `nlm login profile list/delete/rename`
- Studio commands now work without explicit `--source-ids` parameter (defaults to all sources in notebook)
- Download commands now support notebook aliases (auto-resolved via `get_alias_manager().resolve()`)
- Added `--confirm` flag to `nlm alias delete` command
- Updated all documentation to reflect login command structure

## [0.2.0] - 2026-01-25

### Major Release: Unified CLI & MCP Package (Code Name: "Cancun Wind")

This release unifies the previously separate `notebooklm-cli` and `notebooklm-mcp-server` packages into a single `notebooklm-mcp-cli` package. One install now provides both the `nlm` CLI and `notebooklm-mcp` server.

### Added

#### Unified Package
- Single `notebooklm-mcp-cli` package replaces separate CLI and MCP packages
- Automatic migration from legacy packages (Chrome profiles and aliases preserved)
- Three executables: `nlm` (CLI), `notebooklm-mcp` (MCP server), `notebooklm-mcp-auth` (auth tool)

#### File Upload
- Direct file upload via HTTP resumable protocol (PDF, TXT, Markdown, Audio)
- No browser automation needed for uploads
- File type validation with clear error messages
- `--wait` parameter to block until source is ready

#### Download System
- Unified download commands for all artifact types (audio, video, reports, slides, infographics, mind maps, data tables)
- Streaming downloads with progress bars
- Interactive artifact support - Quiz and flashcards downloadable as JSON, Markdown, or HTML
- Alias support in download commands

#### Export to Google Workspace
- Export Data Tables to Google Sheets (`nlm export sheets`)
- Export Reports to Google Docs (`nlm export docs`)

#### Notes API
- Full CRUD operations: `nlm note create/list/update/delete`
- MCP tools: `note_create`, `note_list`, `note_update`, `note_delete`

#### Sharing API
- View sharing status and collaborators (`nlm share status`)
- Enable/disable public link access (`nlm share public/private`)
- Invite collaborators by email with role selection (`nlm share invite`)

#### Multi-Profile Authentication
- Named profiles for multiple Google accounts (`nlm login --profile <name>`)
- Profile management: `nlm login profile list/delete/rename`
- Each profile gets isolated Chrome session (no cross-account conflicts)

#### Dual CLI Command Structure
- **Noun-first**: `nlm notebook list`, `nlm source add`, `nlm studio create`
- **Verb-first**: `nlm list notebooks`, `nlm add url`, `nlm create audio`
- Both styles work interchangeably

#### AI Coding Assistant Integration
- Skill installer for Claude Code, Cursor, Gemini CLI, Codex, OpenCode, Antigravity
- `nlm skill install <tool>` adds NotebookLM expertise to AI assistants
- User-level and project-level installation options

#### MCP Server Improvements
- HTTP transport mode (`notebooklm-mcp --transport http --port 8000`)
- Debug logging (`notebooklm-mcp --debug`)
- Consolidated from 45+ tools down to 28 unified tools
- Modular server architecture with mixins

#### Research Improvements
- Query fallback for more reliable research polling
- Better status tracking for deep research tasks
- Task ID filtering for concurrent research operations

### Changed
- Storage location moved to `~/.notebooklm-mcp-cli/`
- Client refactored into modular mixin architecture (BaseClient, NotebookMixin, SourceMixin, etc.)
- MCP tools consolidated (e.g., separate `notebook_add_url/text/drive` → unified `source_add`)

## [0.1.14] - 2026-01-17

### Fixed
- **Critical Research Stability**:
  - `poll_research` now accepts status code `6` (Imported) as success, fixing "hanging" Fast Research.
  - Added `target_task_id` filtering to `poll_research` to ensure the correct research task is returned (essential for Deep Research).
  - Updated `research_status` and `research_import` to use task ID filtering.
  - `research_status` tool now accepts an optional `task_id` parameter.
- **Missing Source Constants**:
  - Included the code changes for `SOURCE_TYPE_UPLOADED_FILE`, `SOURCE_TYPE_IMAGE`, and `SOURCE_TYPE_WORD_DOC` that were omitted in v0.1.13.

## [0.1.13] - 2026-01-17

### Added
- **Source type constants** for proper identification of additional source types:
  - `SOURCE_TYPE_UPLOADED_FILE` (11): Direct file uploads (e.g., .docx uploaded directly)
  - `SOURCE_TYPE_IMAGE` (13): Image files (GIF, JPEG, PNG)
  - `SOURCE_TYPE_WORD_DOC` (14): Word documents via Google Drive
- Updated `SOURCE_TYPES` CodeMapper with `uploaded_file`, `image`, and `word_doc` mappings

## [0.1.12] - 2026-01-16

### Fixed
- **Standardized source timeouts** (supersedes #9)
  - Renamed `DRIVE_SOURCE_TIMEOUT` to `SOURCE_ADD_TIMEOUT` (120s)
  - Applied to all source additions: Drive, URL (websites/YouTube), and Text
  - Added graceful timeout handling to `add_url_source` and `add_text_source`
  - Prevents timeout errors when importing large websites or documents

## [0.1.11] - 2026-01-16

### Fixed
- **Close Chrome after interactive authentication** - Chrome is now properly terminated after `notebooklm-mcp-auth` completes, releasing the profile lock and enabling headless auth for automatic token refresh
- **Improve token reload from disk** - Removed the 5-minute timeout when reloading tokens during auth recovery. Previously, cached tokens older than 5 minutes were ignored even if the user had just run `notebooklm-mcp-auth`

These fixes resolve "Authentication expired" errors that occurred even after users re-authenticated.

## [0.1.10] - 2026-01-15

### Fixed
- **Timeout when adding large Drive sources** (fixes #9)
  - Extended timeout from 30s to 120s for Drive source operations
  - Large Google Slides (100+ slides) now add successfully
  - Returns `status: "timeout"` instead of error when timeout occurs, indicating operation may have succeeded
  - Added `DRIVE_SOURCE_TIMEOUT` constant in `api_client.py`

## [0.1.9] - 2026-01-11


### Added
- **Automatic re-authentication** - Server now survives token expirations without restart
  - Three-layer recovery: CSRF refresh → disk reload → headless Chrome auth
  - Works with long-running MCP sessions (e.g., MCP Super Assistant proxy)
- `refresh_auth` MCP tool for explicit token reload
- `run_headless_auth()` function for background authentication (if Chrome profile has saved login)
- `has_chrome_profile()` helper to check if profile exists

### Changed
- `launch_chrome()` now returns `subprocess.Popen` handle instead of `bool` for cleanup control
- `_call_rpc()` enhanced with `_deep_retry` parameter for multi-layer auth recovery

## [0.1.8] - 2026-01-10

### Added
- `constants.py` module as single source of truth for all API code-name mappings
- `CodeMapper` class with bidirectional lookup (name→code, code→name)
- Dynamic error messages now show valid options from `CodeMapper`

### Changed
- **BREAKING:** `quiz_create` now accepts `difficulty: str` ("easy"|"medium"|"hard") instead of `int` (1|2|3)
- All MCP tools now use `constants.CodeMapper` for input validation
- All API client output now uses `constants.CodeMapper` for human-readable names
- Removed ~10 static `_get_*_name` helper methods from `api_client.py`
- Removed duplicate `*_codes` dictionaries from `server.py` tool functions

### Fixed
- Removed duplicate code block in research status parsing

## [0.1.7] - 2026-01-10

### Fixed
- Fixed URL source retrieval by implementing correct metadata parsing in `get_notebook_sources_with_types`
- Added fallback for finding source type name in `get_notebook_sources_with_types`

## [0.1.6] - 2026-01-10

### Added
- `studio_status` now includes mind maps alongside audio/video/slides
- `delete_mind_map()` method with two-step RPC deletion
- `RPC_DELETE_MIND_MAP` constant for mind map deletion
- Unit tests for authentication retry logic

### Fixed
- Mind map deletion now works via `studio_delete` (fixes #7)
- `notebook_query` now accepts `source_ids` as JSON string for compatibility with some AI clients (fixes #5)
- Deleted/tombstone mind maps are now filtered from `list_mind_maps` responses
- Token expiration handling with auto-retry on RPC Error 16 and HTTP 401/403

### Changed
- Updated `bl` version to `boq_labs-tailwind-frontend_20260108.06_p0`
- `delete_studio_artifact` now accepts optional `notebook_id` for mind map fallback

## [0.1.5] - 2026-01-09

### Fixed
- Improved LLM guidance for authentication errors

## [0.1.4] - 2026-01-09

### Added
- `source_get_content` tool for raw text extraction from sources

## [0.1.3] - 2026-01-08

### Fixed
- Chrome detection on Linux distros

## [0.1.2] - 2026-01-07

### Fixed
- YouTube URL handling - use correct array position

## [0.1.1] - 2026-01-06

### Changed
- Improved research tool descriptions for better AI selection

## [0.1.0] - 2026-01-05

### Added
- Initial release
- Full NotebookLM API client with 31 MCP tools
- Authentication via Chrome DevTools or manual cookie extraction
- Notebook, source, query, and studio management
- Research (web/Drive) with source import
- Audio/Video overview generation
- Report, flashcard, quiz, infographic, slide deck creation
- Mind map generation
