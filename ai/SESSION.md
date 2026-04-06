# Session Log

_Updated at the end of every working session, by every tool and every person._
_Most recent session at the top._

---

## 2026-04-06 — Brian Worrell — Claude Code (session 4)

**Who worked on this:** Brian Worrell + Claude Code (claude-sonnet-4-6)

**What we worked on:**
- Resumed from context limit (session 3 ended mid-execution after merging PRs #2, #3, #4)
- Created `chore/p3-debt` branch from enterprise-url-support
- P3-A: Fixed `test_mcp_download_report` — was importing removed `download_report`; updated to use `download_artifact` (async), removed `@pytest.mark.skip`
- P3-B: Fixed 5 `TestFileUploadProtocol` failures — added `client._profile = APIProfile()` when constructing `SourceMixin.__new__`; `_profile` was added to `BaseClient.__init__` after tests were written
- P3-C: Added v1.0.0 fork header to CHANGELOG.md above upstream history
- P3 cleanup: Fixed pre-existing ruff errors across 13 files (F401, I001 import sort, SIM105 → contextlib.suppress) — all were blocking CI
- P4-A: Updated `ai/MEMORY.md` — upstream sync conflict hotspots table, updated PR status
- P4-B: Created `.github/workflows/upstream-check.yml` — weekly check for upstream drift; opens/updates GitHub issue if behind
- P5: Populated `.codex` with architecture layers, test commands, version locations, upstream sync guidance, and hard rules
- P6: Expanded `ai/PLANNING.md` with full release checklist (version locations, PyPI OIDC) and release trigger rules
- Opened Robiton/notebooklm-mcp-cli#5 (chore/p3-debt → enterprise-url-support)

**Decisions made:**
- SIM105 (try/except/pass) → `contextlib.suppress(Exception)` is safe for both enterprise_adapter.py and enterprise_client.py cases
- ruff format auto-reformatted 13 pre-existing files — these are all cosmetic and CI-safe
- BACKLOG "~19 pre-existing failures" item removed — the downloads.py failures were already fixed upstream; the file_upload.py failures were fixed in P3-B

**Problems encountered:**
- ruff check found 9 pre-existing errors on the branch; fixed 8 with `--fix`, 2 SIM105 needed manual `contextlib.suppress`
- `test_file_upload.py TestFileUploadE2E::test_upload_text_file` still errors with 400 when live credentials are expired — this is expected behavior for e2e tests and was pre-existing

**Next steps:**
- Merge PR #5 into enterprise-url-support
- GitHub About section (manual UI): description + topics
- Enable GitHub Discussions (manual UI toggle)
- PyPI OIDC trusted publisher setup (manual on pypi.org — one-time before first release)
- Monitor upstream podcast PR #129 for review from jacob-bd

**Backlog changes:**
- Completed: All of Phases 3-6 (PRs #3 and #4 were merged in session 3, PR #5 opened this session)
- Removed: "Pre-existing test failures ~19" — resolved
- Added to up-next: merge PR #5, GitHub About, Discussions, PyPI OIDC

---

## 2026-04-06 — Brian Worrell — Claude Code (session 2)

**Who worked on this:** Brian Worrell + Claude Code (claude-sonnet-4-6)

**What we worked on:**
- Resumed from context limit with all scaffold files already staged
- Committed scaffold adoption (21 files, 960 insertions) as commit `6c494d0` on `chore/add-scaffold`
- Pushed `chore/add-scaffold` to `Robiton/notebooklm-mcp-cli`
- Opened Robiton/notebooklm-mcp-cli#2 (scaffold PR targeting enterprise-url-support)
- Accidentally opened jacob-bd/notebooklm-mcp-cli#130 (immediately closed with note)
- Updated all ai/ context files per scaffold end-of-session requirements

**Decisions made:**
- Scaffold PR targets `enterprise-url-support` (fork's active base), not `main`
- `main` on Robiton fork tracks upstream; enterprise-url-support is where real work happens

**Problems encountered:**
- `gh pr create` defaults to upstream parent repo (jacob-bd) when run inside a fork
  — solution: always use `--repo Robiton/notebooklm-mcp-cli --head <branch>` flags

**Next steps:**
- Merge scaffold PR (Robiton/notebooklm-mcp-cli#2)
- Discuss project next steps with Brian
- Wait for upstream podcast PR #129 review from jacob-bd

**Backlog changes:**
- Completed: scaffold commit + push + PR (Robiton/notebooklm-mcp-cli#2)

---

## 2026-04-06 — Brian Worrell — Claude Code (session 1)

**Who worked on this:** Brian Worrell + Claude Code (claude-sonnet-4-6)

**What we worked on:**
- Fixed CI lint failure on upstream podcast PR #129 (ruff format + import sort)
- Added AI project scaffold (`Robiton/ai-project-scaffold`) to this repo
  - Created `ai/` folder with all 8 context files
  - Applied api-integration overlay to STANDARDS.md and CODING.md
  - Migrated CLAUDE.md institutional knowledge → ai/MEMORY.md
  - Replaced CLAUDE.md with AGENTS.md + gitignored symlink
  - Added hook files (.cursorrules, .windsurfrules, .codex, copilot-instructions.md)
  - Added GitHub scaffold files (PR template, CODEOWNERS, scaffold-check CI)
  - Added sync-check.sh, .editorconfig, version file

**Decisions made:**
- Scaffold overlay: api-integration (project calls two Google API surfaces)
- CLAUDE.md content moved to ai/MEMORY.md; CLAUDE.md becomes gitignored symlink to AGENTS.md
- ai/ files committed to repo so context is portable across machines and tools

**Problems encountered:**
- Upstream PR #129 failed lint CI: ruff format and import sort issues in podcast.py,
  __init__.py, server.py — fixed and pushed

**Next steps:**
- Commit scaffold and open PR (carried into session 2)

**Backlog changes:**
- Added: scaffold adoption task (completed same session)
- Completed: scaffold adoption, lint fix for podcast PR

---

## 2026-04-03 — Brian Worrell — Claude Code

**Who worked on this:** Brian Worrell + Claude Code

**What we worked on:**
- Completed remaining pre-PR items: paywall detection, per-URL bulk results, enterprise auth docs
- Fixed SSRF vulnerability in paywall URL checker (private IP blocking)
- Ran full security audit — no CRITICAL/HIGH findings; SSRF was the only actionable issue
- Wrote detailed project write-up
- Merged enterprise PR to Robiton fork (PR #1 → main)
- Opened upstream PR jacob-bd/notebooklm-mcp-cli#126 (enterprise support — full)
- Received response from jacob-bd: declined due to v1alpha instability + feature parity gap
- Opened focused upstream PR jacob-bd/notebooklm-mcp-cli#129 (standalone podcast only)
- Rebranded fork README as enterprise-first with "Why This Fork?" section

**Decisions made:**
- Don't fight the upstream decision — maintain as enterprise fork
- Podcast-only PR is the right small contribution to upstream
- Watch v1alpha promotion as the trigger for re-submission

**Problems encountered:**
- Podcast PR #129 failed upstream CI on lint (fixed 2026-04-06)

---

## 2026-03 (multiple sessions) — Brian Worrell — Claude Code

**Who worked on this:** Brian Worrell + Claude Code

**What we worked on:**
- Forked jacob-bd/notebooklm-mcp-cli
- Built enterprise NotebookLM support via Discovery Engine REST API
  - EnterpriseClient, EnterpriseAdapter, APIProfile
  - Persistent config (EnterpriseConfig in config.toml)
  - configure_mode MCP tool with auth pre-checks
  - Standalone Podcast API
  - Audio overview fix (empty body — API rejects documented fields)
  - server_info auth status display
- Security hardening: token leakage prevention, ID validation, path traversal fix
- Removed duplicate MCP server / 0.5.10 nag
- Bumped version to 1.0.0
- Tested against enterprise GCP project 204404889700
- Added paywall detection with SSRF protection
- Updated docs (README enterprise section, AUTHENTICATION.md enterprise section)
