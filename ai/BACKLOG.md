# Project Backlog

_This file is the project to-do list. Updated by all tools and team members._
_Last updated: 2026-04-07 (session 7, enterprise improvements) by Claude Code_

---

## In progress

_(nothing active)_

---

## Up next

### Research tasks

- [x] **Enterprise SDK comparison** — Completed 2026-04-07. See findings below. | Priority: High | Owner: Claude Code | Due: —

### Enterprise API gaps (from SDK comparison — 2026-04-07)

- [x] **Separate endpoint_location from resource location** — Completed 2026-04-07. Added `endpoint_location` field to `EnterpriseConfig` and `NOTEBOOKLM_ENDPOINT_LOCATION` env var. `EnterpriseClient` now uses it as the API hostname prefix (falls back to `location`). | Priority: High | Owner: Claude Code | Due: —
- [x] **YouTube source type in enterprise** — Completed 2026-04-07. `enterprise_adapter.add_url_source()` now detects `youtube.com/youtu.be` URLs and routes to `add_source_youtube()` which uses the correct `videoContent` body format. | Priority: Med | Owner: Claude Code | Due: —
- [x] **Retry with exponential backoff** — Completed 2026-04-07. `_request()` in `enterprise_client.py` retries up to 3x on 429/500/502/503/504 with 500ms–5s backoff, ±25% jitter, and Retry-After header support. | Priority: Med | Owner: Claude Code | Due: —
- [x] **`NBLM_ACCESS_TOKEN` env var support** — Completed 2026-04-07. `_get_token()` checks `NBLM_ACCESS_TOKEN` env var before falling back to gcloud CLI. | Priority: Med | Owner: Claude Code | Due: —
- [ ] **Surface `isShareable`/`isShared` in notebook responses** — These fields come back from the Enterprise API `notebookMetadata` but we likely discard them. Surface in `notebook_get`/`notebook_list` responses. | Priority: Low | Owner: Claude Code | Due: —
- [ ] **`youtubeMetadata` in source responses** — `channelName` and `videoId` come back for YouTube sources. Surface in source list/get responses. | Priority: Low | Owner: Claude Code | Due: —
- [ ] **Docker research**: Design a minimal secure single-user container image for team distribution. Questions to answer: (1) base image choice (python:3.11-slim vs distroless), (2) how user authenticates their Google account into the container, (3) auth persistence across container restarts (volume mount vs re-auth), (4) how the container exposes the MCP server (SSE/HTTP transport), (5) how a user's Claude Desktop/Code points to the remote container, (6) what the distribution story looks like (Docker Hub, ghcr.io, private registry), (7) security hardening (non-root user, read-only fs, minimal capabilities). Goal: two options — local install (current) vs hosted container — for teams who want to avoid running anything on their laptops. | Priority: Med | Owner: Research | Due: —

### New features (consumer API — from teng-lin/notebooklm-py v0.3.x research)

- [x] **Infographic style selection** — Already implemented (discovered during session 7 audit). 10 styles in `constants.py`, exposed via `studio_create` MCP tool and `nlm infographic create --style`. | Priority: Med | Owner: Claude Code | Due: —
- [x] **PPTX download for slide decks** — Already implemented (discovered during session 7 audit). `download_artifact` accepts `slide_deck_format=pptx`; CLI exposes `--format pptx`. | Priority: Med | Owner: Claude Code | Due: —

### New features from fork research

- [ ] **brainupgrade-in**: Add `custom_style_description` param to video overview — when `visual_style=custom`, passes free-text style description at position 6 of RPC options array. ~100 lines across 4 files. | Priority: Low | Owner: Claude Code | Due: —
- [ ] **EPUB source type** — Google added EPUB as a supported source format. Test whether existing `add_source` with `source_type="file"` handles `.epub` files, or if a new type/MIME mapping is needed. | Priority: Low | Owner: Claude Code | Due: —
- [ ] **"Agentspace" → "Gemini Enterprise" rename** — Google renamed Agentspace to Gemini Enterprise (Oct 9, 2025). Grep docs and comments for "Agentspace" and update to "Gemini Enterprise". | Priority: Low | Owner: Claude Code | Due: —

### Enterprise UX improvements (from 2026-04-07 live test)

- [x] **`studio_status` enterprise gap** — Completed 2026-04-07. `poll_studio_status` in enterprise adapter now raises `NotImplementedError` with a clear message; `services/studio.py` propagates it as a user-facing `ServiceError`. | Priority: Med | Owner: Claude Code | Due: —
- [x] **Bot-blocked domain list** — Completed 2026-04-07. Added `thehackernews.com`, `orca.security`, `securityonline.info` to `KNOWN_PAYWALL_DOMAINS` in `services/sources.py`. | Priority: Med | Owner: Claude Code | Due: —

### Maintenance

- [ ] Branch protection on `main` (manual: GitHub Settings → Branches → Add ruleset; require PR + CI status checks, block force push) | Priority: Med | Owner: Brian | Due: —
- [ ] Test configure_mode + full enterprise workflow end-to-end | Priority: Med | Owner: Brian | Due: —

---

## Backlog

- [ ] dizz fork: OAuth 2.1 provider for remote MCP — enables claude.ai remote MCP connector to authenticate against self-hosted HTTP server. 373-line new module, no new deps. Would enable hosted-server scenario from Docker research. | Priority: Low | Owner: Claude Code | Due: —
- [ ] Watch Discovery Engine API for v1alpha → v1 promotion (no longer triggers upstream PR — just informs our own stability posture) | Priority: Low | Owner: Brian | Due: —
- [ ] Consider adding `nlm config set sources.approved_domains` to README quick-start for paywall guidance | Priority: Low | Owner: Brian | Due: —

---

## Completed

- [x] Fork jacob-bd/notebooklm-mcp-cli | Completed: 2026-03
- [x] Enterprise REST API client (EnterpriseClient + EnterpriseAdapter) | Completed: 2026-03
- [x] Persistent config — [enterprise] section in config.toml | Completed: 2026-03
- [x] configure_mode MCP tool with auth pre-checks | Completed: 2026-03
- [x] Audio overview fix — empty body (API rejects documented fields) | Completed: 2026-03
- [x] Standalone Podcast API (enterprise, v1 stable) | Completed: 2026-03
- [x] server_info auth status for both modes | Completed: 2026-03
- [x] Security hardening — token leakage, ID validation, path traversal | Completed: 2026-03
- [x] Remove duplicate MCP server / 0.5.10 version nag | Completed: 2026-03
- [x] Bump version to 1.0.0 | Completed: 2026-03
- [x] Paywall detection for URL sources (domain list + HTTP HEAD check) | Completed: 2026-04-03
- [x] SSRF fix in paywall checker (private IP blocking) | Completed: 2026-04-03
- [x] Per-URL bulk source results (individual processing, partial success) | Completed: 2026-04-03
- [x] docs/AUTHENTICATION.md — enterprise auth section | Completed: 2026-04-03
- [x] Security audit — 0 CRITICAL/HIGH findings | Completed: 2026-04-03
- [x] Merge enterprise PR to Robiton/notebooklm-mcp-cli (PR #1) | Completed: 2026-04-03
- [x] Open upstream enterprise PR jacob-bd/notebooklm-mcp-cli#126 | Completed: 2026-04-03
- [x] Open upstream podcast PR jacob-bd/notebooklm-mcp-cli#129 | Completed: 2026-04-03
- [x] Rebrand fork README as enterprise-first | Completed: 2026-04-03
- [x] Fix podcast PR #129 CI — 3 root causes: unused import, upstream drift, ruff version mismatch | Completed: 2026-04-06
- [x] Add AI project scaffold (api-integration overlay) | Completed: 2026-04-06
- [x] Commit + push scaffold branch, open and merge Robiton/notebooklm-mcp-cli#2 | Completed: 2026-04-06
- [x] Phase 0+1: package rename, CI fix, pyproject.toml, README — Robiton#3 (merged) | Completed: 2026-04-06
- [x] Phase 2: CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, issue templates — Robiton#4 (merged) | Completed: 2026-04-06
- [x] Phase 3-A: fix test_mcp_download_report (use download_artifact, remove stale skip) | Completed: 2026-04-06
- [x] Phase 3-B: fix 5 TestFileUploadProtocol failures (_profile missing in SourceMixin.__new__) | Completed: 2026-04-06
- [x] Phase 3-C: CHANGELOG fork header (v1.0.0 entry above upstream history) | Completed: 2026-04-06
- [x] Phase 3 cleanup: fix pre-existing ruff errors (F401, I001, SIM105) across 13 files | Completed: 2026-04-06
- [x] Phase 4-A: ai/MEMORY.md upstream sync conflict hotspots, PR status update | Completed: 2026-04-06
- [x] Phase 4-B: .github/workflows/upstream-check.yml (weekly upstream drift alert) | Completed: 2026-04-06
- [x] Phase 5: Populate .codex with architecture, test commands, version locations, hard rules | Completed: 2026-04-06
- [x] Phase 6: ai/PLANNING.md release checklist + trigger rules | Completed: 2026-04-06
- [x] D-intelligence: _safe_output_path() + chmod 0o700 on credential dirs | Completed: 2026-04-07
- [x] hectorreyes: unconditional SSRF block + sensitive-dir file blocklist | Completed: 2026-04-07
- [x] RhysEJF: CDP cookie scope to NotebookLM domain only | Completed: 2026-04-07
- [x] Merge enterprise-url-support → main (PR #8, squash merge) | Completed: 2026-04-07
- [x] Release v1.0.1 to PyPI (GitHub release tag, publish.yml triggered) | Completed: 2026-04-07
- [x] Swap local install from upstream notebooklm-mcp-cli to notebooklm-enterprise-mcp v1.0.1 | Completed: 2026-04-07
- [x] Close upstream contribution strategy — jacob-bd closed #126 (enterprise) and #129 (podcast); fork is now one-way sync only | Completed: 2026-04-07
