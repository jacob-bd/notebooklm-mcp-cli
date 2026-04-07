# Session Log

_Updated at the end of every working session, by every tool and every person._
_Most recent session at the top._

---

## 2026-04-07 — Brian Worrell — Claude Code (session 6)

**Who worked on this:** Brian Worrell + Claude Code (claude-sonnet-4-6)

**What we worked on:**
- Planned and implemented three high-priority security fixes from fork research on `fix/security-hardening` branch
- Fix 1 (D-intelligence): Added `_safe_output_path()` to `services/downloads.py` — validates output path is within HOME, cwd, or system temp before any download write; added `chmod 0o700` to all credential dir creation in `utils/config.py`
- Fix 2 (hectorreyes-ship-it): Moved SSRF `_is_private_url()` check unconditionally before paywall check in `add_source()` so `skip_paywall_check=True` can no longer bypass it; added `_SENSITIVE_DIR_BLOCKLIST` and `_assert_file_safe()` to block file uploads from `~/.ssh`, `~/.aws`, `~/.gnupg`, `~/.config`, `~/.notebooklm-mcp-cli`
- Fix 3 (RhysEJF): Changed `get_page_cookies()` in `utils/cdp.py` from `Network.getAllCookies` to `Network.getCookies` with `_NOTEBOOKLM_COOKIE_URLS` filter — scopes cookie capture to notebooklm.google.com and accounts.google.com only
- Opened Robiton/notebooklm-mcp-cli#7 into enterprise-url-support; 664 tests passing, ruff clean

**Decisions made:**
- `_safe_output_path` also allows system temp dir — tests use `/tmp/...` which macOS resolves to `/private/tmp`; both `tempfile.gettempdir()` and `/tmp` are added as allowed roots
- `_assert_file_safe` passes the resolved path to `client.add_file()` (canonicalises symlinks); updated test assertion accordingly
- All three fixes in one PR (simpler than three PRs for closely related security changes)

**Problems encountered:**
- `tempfile.gettempdir()` on macOS returns `/var/folders/.../T` (resolves to `/private/var/...`) while test paths used `/tmp` (resolves to `/private/tmp`) — these are different; fixed by adding both

**Next steps:**
- Merge PR #7 into enterprise-url-support (wait for CI green)
- Docker research: design minimal secure single-user container
- brainupgrade-in: custom_style_description for video overview (low priority)
- Branch protection on main (manual GitHub Settings)
- Merge enterprise-url-support → main for first clean release

**Backlog changes:**
- Moved 3 security fix items from "up next" to completed
- Added PR #7 to "in progress"

---

## 2026-04-06 — Brian Worrell — Claude Code (session 5)

**Who worked on this:** Brian Worrell + Claude Code (claude-sonnet-4-6)

**What we worked on:**
- Resumed from context limit (session 4 ended mid-upstream cherry-pick)
- Completed cherry-picks from upstream v0.5.11–v0.5.16 onto `chore/upstream-sync-v0.5.16`:
  - `10f0cd7` auth.json chmod 0o600 (clean)
  - `67ff30c` auth recovery + --cdp-url fix (clean)
  - `86e2603` Python 3.13 Literal crash + CDP proxy bypass (clean)
  - `055629c` research polling loop — minor conflict resolved in services/research.py and tests/
  - `4ea50fc` configurable base URL merge — many conflicts; kept our enterprise URL routing via APIProfile throughout
- Fixed 6 ruff errors introduced by cherry-picks (unused imports, B904, I001, SIM105)
- All tests: 664 passed, 37 skipped — clean
- Opened and merged Robiton/notebooklm-mcp-cli#6 (upstream sync) into enterprise-url-support
- README updates: added "What this fork adds" table, updated Vibe Coding Alert to Robiton voice, added demo video attribution note, replaced legacy upgrade section with "Switching from Upstream" guide, removed star history chart
- Added 4 GitHub issue templates (bug-enterprise, bug-personal, feature-request, question)
- Added "Reporting Issues" section to README with routing table
- Enabled GitHub Issues on the repo (was disabled)
- Added PR template (.github/PULL_REQUEST_TEMPLATE.md)
- Added Dependabot config (.github/dependabot.yml) — weekly pip + GitHub Actions updates
- Fixed publish.yml: MCPB build/upload steps now skip on workflow_dispatch (only run on release events)
- Researched all ~430 active forks of jacob-bd/notebooklm-mcp-cli for useful contributions
- Deep-dived dizz (OAuth 2.1 remote MCP) and brainupgrade-in (custom video style) forks

**Decisions made:**
- Star history chart removed — new fork with near-zero stars looks worse than no chart; re-add when repo has traction
- Upstream cherry-pick `b31ab7e` (dual RPC fallback) permanently skipped — incompatible with our enterprise adapter design
- For 4ea50fc conflicts: kept our APIProfile-based URL routing throughout; upstream's `get_base_url()` approach is a simpler but less flexible design
- Docker strategy: single-user container (one Google account per container) is viable and useful as a distributable option for teams; multi-user requires significant new architecture
- High-priority fork contributions to implement: D-intelligence (path traversal), hectorreyes-ship-it (SSRF + sensitive dir blocklist), RhysEJF (CDP cookie allowlist)

**Problems encountered:**
- `gh pr create` defaulted to jacob-bd repo again — always use `--repo Robiton/notebooklm-mcp-cli --base <branch>` explicitly
- 4ea50fc was a merge commit requiring `-m 1` flag for cherry-pick

**Next steps:**
- Security fixes from forks: D-intelligence path traversal, hectorreyes SSRF + sensitive-dir blocklist, RhysEJF CDP cookie allowlist
- Research Docker single-user container: what does a minimal secure image look like, and how would distribution/deployment work for teams
- Add brainupgrade-in custom_style_description for video overview (low effort, good feature)
- Branch protection on main (manual GitHub Settings → Branches)
- Merge enterprise-url-support → main for first clean main release

**Backlog changes:**
- Completed: upstream sync v0.5.11–v0.5.16 (PR #6), README identity overhaul, issue templates, PR template, Dependabot, GitHub Issues enabled, publish.yml MCPB guard
- Added to up-next: 3 security fixes from fork research, Docker research task, brainupgrade-in video feature
- Removed from up-next: all items that are now done (PR #5, GitHub About, Discussions, PyPI OIDC were completed in earlier sessions)

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
