# Project Backlog

_This file is the project to-do list. Updated by all tools and team members._
_Last updated: 2026-04-06 (session 2) by Claude Code_

---

## In progress

- [ ] Scaffold PR review: Robiton/notebooklm-mcp-cli#2 (chore/add-scaffold → enterprise-url-support) | Priority: High | Owner: Brian | Due: —
- [ ] Upstream PR review: jacob-bd/notebooklm-mcp-cli#129 (standalone podcast) | Priority: Med | Owner: jacob-bd (reviewer) | Due: —

---

## Up next

- [ ] Sync upstream changes into enterprise-url-support branch | Priority: Med | Owner: Brian | Due: —
- [ ] Test configure_mode + full enterprise workflow end-to-end after scaffold adoption | Priority: Med | Owner: Brian | Due: —

---

## Backlog

- [ ] Watch Discovery Engine API for v1alpha → v1 promotion; re-submit enterprise PR upstream when stable | Priority: Low | Owner: Brian | Due: —
- [ ] Consider adding `nlm config set sources.approved_domains` to README quick-start for paywall guidance | Priority: Low | Owner: Brian | Due: —
- [ ] Pre-existing test failures in test_downloads.py and test_file_upload.py (~19 failures) — investigate root cause | Priority: Low | Owner: Brian | Due: —

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
- [x] Fix podcast PR lint failures (ruff format + import sort) | Completed: 2026-04-06
- [x] Add AI project scaffold (api-integration overlay) | Completed: 2026-04-06
- [x] Commit + push scaffold branch, open Robiton/notebooklm-mcp-cli#2 | Completed: 2026-04-06
- [x] Update ai/ context files (SESSION, BACKLOG, MEMORY) post-session | Completed: 2026-04-06
