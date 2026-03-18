# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-03-18

### Fixed
- **Research Import Timeout (Issue #97)** — `research import` now uses a 300-second default timeout (up from 120s), fixing consistent timeouts on notebooks with many sources. The timeout is configurable via `--timeout` / `-t` in CLI and `timeout` parameter in MCP.
- **Research Start Deadlock (Issue #97)** — `research start` no longer hard-exits when previous research has un-imported sources. Instead, it shows a warning and prompts interactively, so users can choose to proceed or import first. Previously, if import timed out, users were stuck — unable to import or start new research without `--force`.

### Added
- **Configurable Import Timeout** — `nlm research import <notebook> <task-id> --timeout 600` for extra-large notebooks. Available in both CLI (`--timeout` / `-t`) and MCP (`timeout` parameter on `research_import`). Default: 300 seconds.
- **2 new unit tests** for timeout parameter forwarding (total: 624 tests)

## [0.4.9] - 2026-03-16

### Added
- **CC-Claw Skill Support** — Added `cc-claw` as a supported tool for `nlm skill install cc-claw` (`~/.cc-claw/workspace/skills/nlm-skill/`).

### Fixed
- **Windows CLI Argument Parsing (Issue #96)** — Fixed a bug where running `nlm add url <notebook_id> "https://..."` on Windows PowerShell incorrectly parsed the URL string into a list of characters, attempting to add dozens of duplicate sources instead of one.
- **Service Layer Robustness** — Added internal safeguards ensuring single string URL parsing never falls through to character unpacking across the API service boundary.

## [0.4.8] - 2026-03-14

### Added
- **Native Chat History Persistence** — Both the CLI (`nlm notebook query`) and the MCP server now perfectly persist their chat history directly into the NotebookLM web UI. All prompts sent via CLI or MCP agents will now appear in the notebook's native chat panel, sharing the same conversational context as the web UI. (Closes #92)
- **OpenCode Support** — Full support for OpenCode in the `nlm setup` command (`nlm setup add opencode`) to automatically configure the NotebookLM MCP server for OpenCode. Includes smart config array injection and parsing. Thanks to **@woohyun212** for the comprehensive implementation and thorough unit tests (PR #95, closes #95).

### Fixed
- **MCP Profile Switching** — Fixed a bug where the MCP server wouldn't respect dynamic authentication profile changes made via `nlm login switch <profile>`. The server now automatically detects token file changes and gracefully reloads the NotebookLM client in real-time, matching the active profile perfectly.
- **CC-Claw Skill Support** — Added `cc-claw` as a supported tool for `nlm skill install cc-claw` (`~/.cc-claw/workspace/skills/nlm-skill/`).
## [0.4.7] - 2026-03-13

### Changed
- **Skill path migration: `.gemini/skills/` → `.agents/skills/`** — Starting with Gemini CLI v0.33.1, `.agents/skills/` is the recommended cross-tool compatible path (higher priority than `.gemini/skills/`). `nlm skill install gemini-cli` and `nlm skill install codex` are replaced by `nlm skill install agents`, which installs to `~/.agents/skills/nlm-skill/`. This path works for Gemini CLI, Codex, and any tool that reads `.agents/skills/`. Users with existing `gemini-cli` or `codex` installations should run `nlm skill install agents` to reinstall at the new location.
- **Documentation updates** — Added v0.4.6 features (batch, cross-notebook, pipelines, tags) to SKILL.md, AGENTS_SECTION.md, and API_REFERENCE.md. Removed stale QUICK_REFERENCE.md.

## [0.4.6] - 2026-03-12

### Added
- **Batch Operations** — Perform actions across multiple notebooks at once. Thanks to **@fabianafurtadoff** for this contribution (PR #90)!
  - `nlm batch query` — Query multiple notebooks with the same question
  - `nlm batch add-source` — Add a URL to multiple notebooks
  - `nlm batch create` — Create multiple notebooks at once
  - `nlm batch delete` — Delete multiple notebooks (requires `--confirm`)
  - `nlm batch studio` — Generate artifacts across multiple notebooks
  - MCP: Consolidated `batch` tool with `action` parameter (query|add_source|create|delete|studio)
- **Cross-Notebook Query** — Query multiple notebooks and get aggregated answers with per-notebook citations. (PR #90, @fabianafurtadoff)
  - `nlm cross query "question" --notebooks "id1,id2"` — Ask across specific notebooks
  - `nlm cross query "question" --tags "ai,research"` — Query by tag
  - MCP: `cross_notebook_query` tool
- **Pipelines** — Define and execute multi-step notebook workflows. (PR #90, @fabianafurtadoff)
  - `nlm pipeline list` — List available pipelines (3 builtin: ingest-and-podcast, research-and-report, multi-format)
  - `nlm pipeline run <notebook> <pipeline-name>` — Execute a pipeline
  - User-defined pipelines via YAML files in `~/.notebooklm-mcp-cli/pipelines/`
  - MCP: Consolidated `pipeline` tool with `action` parameter (run|list)
- **Smart Select & Tagging** — Tag notebooks and find relevant ones by keyword matching. (PR #90, @fabianafurtadoff)
  - `nlm tag add <notebook> --tags "ai,research"` — Add tags
  - `nlm tag remove <notebook> --tags "ai"` — Remove tags
  - `nlm tag list` — List all tagged notebooks
  - `nlm tag select "query"` — Find notebooks by tag match
  - MCP: Consolidated `tag` tool with `action` parameter (add|remove|list|select)
- **Studio List Types** — Reference of all artifact types and their options, accessible via `studio_status(action="list_types")`
- **73 new unit tests** covering all new service modules (total: 576 tests)

### Changed
- **MCP Tool Consolidation** — Reduced 13 new tools to 4 consolidated tools with action parameters, keeping total MCP tools at 35 (down from what would have been 44). Follows existing patterns (`note`, `source_add`).

### Fixed
- **CLI import violations** — Fixed 3 CLI command files (`batch.py`, `cross.py`, `pipeline.py`) importing `get_client` from `mcp/tools/_utils` instead of `cli/utils`, violating architecture layering
- **Missing UTF-8 encoding** — Added `encoding='utf-8'` to 6 file I/O calls in `smart_select.py` and `pipeline.py` to prevent `UnicodeDecodeError` on Windows
- **Cross-notebook display crash** — Fixed `sources_used` field handling in `cross.py` display formatting (could crash on string values)

## [0.4.5] - 2026-03-10

### Fixed
- **`nlm doctor` crash on Windows (Issue #87)** — Fixed `UnicodeDecodeError` when running `claude mcp list` on Windows systems with non-UTF-8 default encodings (e.g., `cp936`, `cp1252`). Added explicit `encoding="utf-8"` and `errors="replace"` to the subprocess call. Also added a null check for `result.stdout` to prevent `AttributeError` when the subprocess returns no output.
- **Silent Chrome launch failures on Windows (Issue #86)** — `launch_chrome_process` was silently swallowing all `subprocess.Popen` exceptions, causing `nlm login` to report the cryptic "Cannot connect to browser on port XXXX" with no indication of what went wrong. Now logs the browser path, port, and exception details so users get actionable error messages. Added debug logging for successful launches as well.

## [0.4.4] - 2026-03-08

### Fixed
- **Complex citation parsing (PR #84)** — Fixed `notebook_query` dropping cited text when Google returns "direct" citation segments (integer-first elements) alongside the standard "wrapped" format. Both segment variants are now correctly handled. Thanks to **@meirtsvi** for this contribution!
- **Table citation extraction (PR #84)** — When a citation references a data table, the response now includes a structured `cited_table` field with `num_columns` and `rows` data. Table segments are indicated by a `<cited_table>` placeholder in the `cited_text` field.
- **Mind map JSON missing from MCP response (Issue #83)** — `studio_create` for mind maps was returning metadata (`root_name`, `children_count`) but dropping the actual `mind_map_json`. The full JSON now flows through to MCP clients. Thanks to **@cowhi** for reporting!

### Added
- **17 new unit tests** for citation parsing — Comprehensive test coverage for direct/wrapped segment detection, table placeholder insertion, `_extract_text_from_table_rows`, `_extract_table_from_detail`, and `cited_table` in `_extract_citation_data`. Total tests: 503.

## [0.4.3] - 2026-03-08

### Removed
- **`nlm setup add claude-desktop` removed** — Claude Desktop users should install via the `.mcpb` extension (download from [Releases](https://github.com/jacob-bd/notebooklm-mcp-cli/releases/latest), double-click to install). The CLI-based config file editing was unreliable compared to the extension approach. `nlm setup add claude-code` (for the Claude Code CLI) is unchanged.

## [0.4.2] - 2026-03-08

### Added
- **Expanded file format support (PR #82)** — File uploads now accept additional formats. Thanks to **@JumpLao** for this contribution!
  - Audio: `.m4a`, `.wav`, `.aac`, `.ogg`, `.opus` (previously only `.mp3`)
  - Images: `.gif`, `.webp` (previously only `.jpg`, `.jpeg`, `.png`)
  - Note: `.flac`, `.webm`, `.mov`, `.avi`, `.mkv` were removed from the original PR as Google's upload server does not accept them
- **Cited text passages in query output (PR #81)** — `notebook_query` responses now include a `references` array with the actual quoted passage text for each citation. Previously, only the source ID and citation number were returned; the passage text was already in the API response but was being discarded. Thanks to **@cbruyndoncx** for this contribution!
  - Each reference includes `source_id`, `citation_number`, and `cited_text`
  - Backward-compatible: existing `sources_used` and `citations` fields unchanged
  - Flows through MCP and CLI automatically
- **`nlm setup add all` — Interactive multi-tool setup** — Scans the system for installed AI tools, shows detection status, and lets you interactively choose which ones to configure with NotebookLM MCP
  - Detects: Claude Code, Claude Desktop, Gemini CLI, Cursor, Windsurf, Cline, Antigravity, Codex
  - Shows which tools are already configured vs. newly detected
  - Select `all`, specific numbers, or `none`
- **`nlm setup remove all`** — Remove NotebookLM MCP from all configured tools at once, with explicit confirmation and safety warnings. Uses CLI-first removal (e.g., `claude mcp remove`) where available.

### Changed
- **Codex skill path updated** — `nlm skill install codex` now installs to `~/.agents/skills/nlm-skill/SKILL.md` per [official Codex docs](https://developers.openai.com/codex/skills/), replacing the old `~/.codex/AGENTS.md` path. Users with the old installation should run `nlm skill install codex` to reinstall at the correct location.

## [0.4.1] - 2026-03-07

### Added
- **Cinematic Video Format (Experimental)** — Added support for NotebookLM's new "Cinematic" video format (`video_format="cinematic"`, format code `3`). This format produces higher-fidelity video overviews and is available to NotebookLM Plus/Ultra subscribers. Thanks to **@ovai-felix** for the detailed reverse-engineering and verified payload structure (Issue #79).
  - Core: Cinematic payloads use a 5-element inner options array (omitting `visual_style_code`), while Explainer/Brief continue to use 6 elements
  - MCP: `studio_create` with `video_format="cinematic"` 
  - CLI: `nlm video create <notebook> --format cinematic`
  - ⚠️ **Note for free/Pro users:** Cinematic is gated behind NotebookLM Plus/Ultra. Free and Pro tier users will see: `"NotebookLM rejected video creation. Try again later or create from NotebookLM UI for diagnosis."` — this is expected behavior, not a bug.

### Fixed
- **Claude Desktop `.mcpb` extension disconnects (Issue #78)** — The `.mcpb` bundle was incomplete (only contained `manifest.json` with no entrypoint) and relied on `uvx` being in PATH, which Claude Desktop's restricted macOS environment doesn't expose. Fixed by bundling a cross-platform Python launcher (`run_server.py`) that defensively resolves `uvx` across common install locations (`~/.local/bin`, `~/.cargo/bin`, `/opt/homebrew/bin`, etc.) and using `${__dirname}` for reliable path resolution. Thanks to **@abanoub-ashraf** for the detailed diagnosis and reproduction steps.

## [0.4.0] - 2026-03-05

### Added
- **Bulk Sharing (`notebook_share_batch`)** — Invite multiple collaborators to a notebook in a single API call (Issue #73). Supports mixed roles (viewer/editor) per recipient.
  - Core: `add_collaborators_bulk(notebook_id, recipients)` on `SharingMixin`
  - Service: `invite_collaborators_bulk(client, notebook_id, recipients)` with upfront validation
  - MCP: `notebook_share_batch` tool with `recipients` list and `confirm` flag
  - CLI: `nlm share batch <notebook> "a@gmail.com,b@gmail.com" --role viewer`
- **10 new unit tests** for bulk sharing (core + services)

### Fixed
- **Version mismatch (Patch)** — Bump internal `__version__` string in `__init__.py` to correctly report version (was omitted in `0.3.20` release).

## [0.3.20] - 2026-03-04

### Fixed
- **Type errors, thread safety, and silent exceptions (PR #74)**
  - Added Double-Checked Locking (`threading.Lock`) for thread-safe client initialization in MCP tools.
  - Surfaced previously swallowed exceptions for better debug visibility via `logger.debug()`.
  - Fixed multiple type annotations (`str = None` -> `str | None = None`) across the codebase.
  - Replaced unreachable code with explicit `ValidationError` throwing to ensure strict type checking completeness.
  - Thanks to **@adlewis82** for the excellent cleanup and safety improvements!

## [0.3.19] - 2026-03-02

### Fixed
- **JSON output word wrapping (Issue #72)** — CLI commands using `-j` flag (`note list`, `share status`, `export artifact`, `config show`) were producing invalid JSON due to Rich console wrapping long strings at terminal width. JSON output now bypasses Rich and goes directly to stdout. Thanks to **@pjeby** for reporting.

## [0.3.18] - 2026-03-02

### Added
- **Infographic visual styles** — Infographics now support 11 visual styles matching the NotebookLM web UI: `auto_select`, `sketch_note`, `professional`, `bento_grid`, `editorial`, `instructional`, `bricks`, `clay`, `anime`, `kawaii`, `scientific`. Available via MCP (`infographic_style` parameter on `studio_create`), CLI (`--style` flag on `nlm infographic create`), and Python API (`visual_style_code` on `create_infographic()`). Default is `auto_select` for backward compatibility.

## [0.3.17] - 2026-03-02

### Added
- **Multi-browser support for `nlm login`** — `nlm login` now detects and launches any Chromium-based browser, not just Google Chrome. Supported browsers (in priority order): Google Chrome, Arc (macOS), Brave, Microsoft Edge, Chromium, Vivaldi, Opera. Checks both system and user-local install paths. Error messages now dynamically list supported browsers per platform. Thanks to **@devnull03** for this contribution (PR #70).
- **Browser preference setting** — Users can now control which browser `nlm login` uses via `nlm config set auth.browser <name>`. Valid values: `auto` (default, first found wins), `chrome`, `arc`, `brave`, `edge`, `chromium`, `vivaldi`, `opera`. Falls back to auto-detection if the preferred browser is not installed. Also settable via `NLM_BROWSER` env var.

### Fixed
- **Deep research task_id mismatch (Issue #69)** — `nlm research status <nb> --task-id <id>` returned "no research found" for deep research because the backend assigns a new task_id internally. Now falls back to returning the only active task when the original task_id doesn't match. Thanks to **@danielbrodie** for reporting.

## [0.3.16] - 2026-02-28

### Fixed
- **Chrome profile isolation bug**: `nlm login` could reuse a Chrome instance from a different NLM profile. Implemented port-to-profile mapping to guarantee strict cross-profile isolation.
- **Auto-retry on Google account mismatch**: When switching NLM profiles (or when multiple users log in on the same machine), Chrome can cache the wrong Google login. The builtin login provider now detects `AccountMismatchError`, automatically clears the stale Chrome user-data-dir, and relaunches Chrome for a fresh Google sign-in.
- **`nlm login profile delete` validation**: Profile deletion was failing for broken/invalid profiles because it strictly checked for valid cookies. Now it checks if the profile directory exists, allowing deletion of empty/corrupt profiles.

## [0.3.15] - 2026-02-26

### Added
- **`nlm setup add json` — Interactive JSON config generator** — Run `nlm setup add json` to generate an MCP JSON config snippet for any tool not directly supported. Interactive wizard with numbered prompts lets you choose uvx vs regular mode, full path vs command name, and whether to include the `mcpServers` wrapper. Prints syntax-highlighted JSON and offers clipboard copy on macOS.

## [0.3.14] - 2026-02-26

### Fixed
- **MCP server instructions: incorrect parameter names** — The consolidated tools summary in the MCP server instructions advertised `type=` for `source_add`, `studio_create`, and `download_artifact`, but the actual tool schemas use `source_type` and `artifact_type`. AI clients reading the instructions would use wrong parameter names, causing validation errors. Also added value parameter hints for `source_add`.

## [0.3.13] - 2026-02-26

### Added
- **Bulk Source Add** — Add multiple URL sources in a single API call, dramatically reducing round-trips and avoiding rate limits (Issue #57).
  - Core: `add_url_sources(notebook_id, urls)` on `SourceMixin`
  - Service: `add_sources(client, notebook_id, sources)` — batches URL sources automatically, falls back to individual calls for other types
  - MCP: `source_add` now accepts optional `urls` list parameter for bulk URL add
  - CLI: `nlm source add <notebook> --url https://a.com --url https://b.com` (repeatable `--url` flag)
- **Bulk Source Delete** — Delete multiple sources in a single API call.
  - Core: `delete_sources(source_ids)` on `SourceMixin`
  - Service: `delete_sources(client, source_ids)` with validation
  - MCP: `source_delete` now accepts optional `source_ids` list parameter for bulk delete
  - CLI: `nlm source delete <id1> <id2> <id3> --confirm` (variadic arguments)
- **12 new unit tests** for bulk add/delete service functions (total: 443 tests)

## [Unreleased / 0.3.12]

### Fixed
- **Source additions bypassing Token Refresh** - Refactored `add_url_source`, `add_drive_source`, `add_text_source`, and multiple other methods in `core/sources.py` to use the unified `_call_rpc` mechanism instead of raw `client.post` requests. This ensures that adding sources now properly benefits from the automatic session/CSRF token refresh if authentication unexpectedly expires (Issue #62).
- **Notebook operations bypassing Token Refresh** - Refactored `list_notebooks` and `delete_notebook` in `core/notebooks.py` to use `_call_rpc`, ensuring they recover from expired CSRF tokens just like other core operations. Thanks to **@byingyang** for identifying this in PR #61.
- **OpenClaw skill path** - Fixed incorrect installation path for OpenClaw skills (`workplace` -> `workspace`) in code and documentation. Thanks to **@maxcanada** for reporting (Issue #63).
- **`create slides` default format** - Fixed a bug where `create slides` would error because it used an invalid format fallback. It now correctly defaults to `detailed_deck`. Added comprehensive tests for all verb defaults. (PR #64)

## [0.3.11] - 2026-02-22

### Added
- **Auto-extract build label (`bl`)** - The `bl` URL parameter is now automatically extracted from the NotebookLM page during `nlm login` and CSRF token refresh, instead of using a hardcoded value that goes stale every few weeks. This keeps API requests current with Google's latest build without any manual steps. The `NOTEBOOKLM_BL` env var still works as an override. The `save_auth_tokens` MCP tool also extracts `bl` from the `request_url` parameter when provided.

### Fixed
- **`sources_used` now populated in query responses** - The `sources_used` field was always returning `[]` even when the AI's answer contained citation markers like `[1]`, `[2]`. Google's response includes citation-to-source mapping data that was present but never parsed. Query responses now correctly return `sources_used` (list of cited source IDs) and `citations` (dict mapping each citation number to its parent source ID). This also enables the REPL's citation legend feature. Thanks to **@MinhDung2209** for reporting (issue #57).

## [0.3.10] - 2026-02-22

### Added
- **Source Rename (`source_rename`)** — Rename any source within a notebook via new RPC `b7Wfje`.
  - MCP tool: `source_rename` with `notebook_id`, `source_id`, and `new_title` params
  - CLI: `nlm source rename <source-id> <title> --notebook <notebook-id>`
  - Verb-first alias: `nlm rename source <source-id> <title> --notebook <notebook-id>`

## [0.3.9] - 2026-02-22

### Added
- **`--clear` flag for `nlm login`** - Added a `--clear` flag that wipes the cached Chrome profile before logging in. This solves an issue where `nlm login` would auto-login to an old, cached account without letting the user switch profiles or emails.

### Fixed
- **Accurate Email Extraction** - Fixed a bug in `extract_email` where the CLI would sometimes grab a shared note author's email off the dashboard instead of the logged-in user. The regex now prioritizes actual internal Google account fields before falling back to generic matching.
- **Skipping Migration on Clear** - Fixed an issue where using `--clear` would cause the CLI to mistakenly run a migration step from older CLI versions, reinstating the wrong account profile.

## [0.3.8] - 2026-02-22

### Added
- **CLI `--debug` Flag** - `nlm --debug <command>` enables debug logging across all CLI commands, showing raw API responses and internal state. Useful for diagnosing API issues.

### Fixed
- **Google API errors no longer silently swallowed** - When Google returns an error response (e.g., `INVALID_ARGUMENT`, `UserDisplayableError`) instead of an answer, the CLI now surfaces a clear error message instead of returning an empty answer. Previously, queries would succeed with `{'answer': ''}` and no indication of what went wrong. Thanks to **@MinhDung2209** for the detailed debugging that uncovered this (issue #57).

## [0.3.7] - 2026-02-22

### Added
- **Configurable Interface Language (`NOTEBOOKLM_HL`)** - Set `NOTEBOOKLM_HL` env var to control both the API's `hl` URL parameter and the default artifact creation language. Explicit `--language` flags still take priority. Thanks to **@beausea** for this contribution (PR #59, closes #58).

## [0.3.6] - 2026-02-22

### Added
- **Query Timeout Flag** - `nlm notebook query` and `nlm query notebook` now accept `--timeout` / `-t` to set query timeout in seconds (default: 120). Useful for long extraction prompts that need more processing time (closes #57).

## [0.3.5] - 2026-02-21

### Added
- **Slide Deck Revision (`studio_revise`)** — Revise individual slides in an existing slide deck via new RPC `KmcKPe`. Creates a new artifact with revisions applied; original is never modified.
  - MCP tool: `studio_revise` with `artifact_id`, `slide_instructions`, and `confirm` params
  - CLI: `nlm slides revise <artifact-id> --slide '1 Make the title larger' --confirm`
- **PPTX Download Support** — Download slide decks as PowerPoint (PPTX) in addition to PDF.
  - CLI: `nlm download slide-deck <notebook> --format pptx`
  - MCP: `download_artifact` with `slide_deck_format="pptx"`
- **Login Profile Protection** — Account mismatch guard prevents accidentally overwriting a profile with credentials from a different Google account. Use `--force` to override.
- **Reused Chrome Warning** — `nlm login` now warns when connecting to an existing Chrome instance instead of launching a fresh one.

### Changed
- **Faster Login** — Connection pooling and reduced sleep durations cut `nlm login` time from ~25s to under 3s. Thanks to **@pjeby** for this contribution (PR #54).

## [0.3.4] - 2026-02-19

### Fixed
- **`nlm login` hang on fresh install** - Optimized Chrome port availability scanning (using `socket.bind` instead of `httpx.get`) to avoid 20+ second timeouts on systems that drop network packets. Thanks to **@pjeby** for the diagnosis (closes #52)
- **Chrome "Restore Pages" Warning** - `nlm login` and headless authentication now perform a graceful shutdown of Chrome via CDP (`Browser.close`) rather than abruptly killing the process, resolving crashes on next browser start. Again, great work by **@pjeby** (fixes #52)

## [0.3.3] - 2026-02-16

### Fixed
- **OpenClaw skill path** - Fixed incorrect installation path for OpenClaw skills. Now correctly uses `~/.openclaw/workspace/skills/` instead of `~/.openclaw/skills/`.

## [0.3.2] - 2026-02-14

### Added
- **Focus Prompt Support** - Added `--focus` parameter to `nlm quiz create` and `nlm flashcards create` commands to specify custom instructions.
- **Improved Prompt Extraction** - `studio_status` now correctly extracts custom prompts for all artifact types (Audio, Video, Slides, Quiz, Flashcards).

### Fixed
- **Quiz/Flashcard Prompt Extraction** - Fixed a bug where custom instructions were not being extracted for Quiz and Flashcards artifacts (wrong API index).

## [0.3.1] - 2026-02-14

### Added
- **New AI Client Support** — Added `nlm skill install` support for:
  - **Cline** (`~/.cline/skills`) - Terminal-based AI agent
  - **Antigravity** (`~/.gemini/antigravity/skills`) - Advanced agentic framework
  - **OpenClaw** (`~/.openclaw/workspace/skills`) - Autonomous AI agent
  - **Codex** (`~/.codex/AGENTS.md`) - Now with version tracking
- **`nlm setup` support** — Added automatic MCP configuration for:
  - **Cline** (`nlm setup add cline`)
  - **Antigravity** (`nlm setup add antigravity`)
- **`nlm skill update` command** - Update installed AI skills to the latest version. Supports updating all skills or specific tools (e.g., `nlm skill update claude-code`).
- **Verb-first alias** - `nlm update skill` works identically to `nlm skill update`.
- **Version tracking** - `AGENTS.md` formats now support version tracking via injected comments.

### Fixed
- **Skill version validation** - `nlm skill list` now correctly identifies outdated skills and prevents "unknown" version status for Codex.
- **Package version** - Bumped to `0.3.1` to match release tag.

## [0.3.0] - 2026-02-13

### Added
- **Shared service layer** (`services/`) — 10 domain modules centralizing all business logic previously duplicated across CLI and MCP:
  - `errors.py`: Custom error hierarchy (`ServiceError`, `ValidationError`, `NotFoundError`, `CreationError`, `ExportError`)
  - `chat.py`: Chat configuration and notebook query logic
  - `downloads.py`: Artifact downloading with type/format resolution
  - `exports.py`: Google Docs/Sheets export
  - `notebooks.py`: Notebook CRUD, describe, query consolidation
  - `notes.py`: Note CRUD operations
  - `research.py`: Research start, polling, and source import
  - `sharing.py`: Public link, invite, and status management
  - `sources.py`: Source add/list/sync/delete with type validation
  - `studio.py`: Unified artifact creation (all 9 types), status, rename, delete
- **372 unit tests** covering all service modules (up from 331)

### Changed
- **Architecture: strict layering** — `cli/` and `mcp/` are now thin wrappers delegating to `services/`. Neither imports from `core/` directly.
- **MCP tools refactored** — Significant line count reductions across all tool files (e.g., studio 461→200 lines)
- **CLI commands refactored** — Business logic extracted to services, CLI retains only UX concerns (prompts, spinners, formatting)
- **Contributing workflow updated** — New features follow: `core/client.py` → `services/*.py` → `mcp/tools/*.py` + `cli/commands/*.py` → `tests/services/`

## [0.2.22] - 2026-02-13

### Fixed
- **Fail-fast for all studio create commands** — Audio, report, quiz, flashcards, slides, video, and data-table creation now exit non-zero with a clear error when the backend returns no artifact, instead of silently reporting success. Extends the infographic fix from v0.2.21 to all artifact types (closes #33)

## [0.2.21] - 2026-02-13

### Added
- **OpenClaw CDP login provider** — `nlm login --provider openclaw --cdp-url <url>` allows authentication via an already-running Chrome CDP endpoint (e.g., OpenClaw-managed browser sessions) instead of launching a separate Chrome instance. Thanks to **@kmfb** for this contribution (PR #47)
- **CLI Guide documentation for `nlm setup` and `nlm doctor`** — Added Setup and Doctor command reference sections, updated workflow example, and added tips. Cherry-picked from PR #48 by **@997unix**

### Fixed
- **Infographic create false success** — `nlm infographic create` now exits non-zero with a clear error when the backend returns `UserDisplayableError` and no artifact, instead of silently reporting success (closes #46). Thanks to **@kmfb** (PR #47)
- **Studio status code 4 mapping** — Studio artifact status code `4` now maps to `"failed"` instead of `"unknown"`, making artifact failures visible during polling. By **@kmfb** (PR #47)

### Changed
- **CDP websocket compatibility** — WebSocket connections now use `suppress_origin=True` for compatibility with managed Chrome endpoints, with fallback for older `websocket-client` versions

## [0.2.20] - 2026-02-11

### Added
- **Claude Desktop Extension detection** — `nlm setup list` and `nlm doctor` now detect NotebookLM when installed as a Claude Desktop Extension (`.mcpb`), showing version and enabled state.

### Fixed
- **Shell tab completion crash** — Fixed `nlm setup add <TAB>` crashing with `TypeError` due to incorrect completion callback signature.

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
