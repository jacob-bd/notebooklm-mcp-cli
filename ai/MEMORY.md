# Project Memory

_Persistent context. Updated when architectural or design decisions are made._
_Never put credentials, API keys, or PHI here._

---

## Project overview

**NotebookLM MCP Server & CLI** — programmatic access to Google NotebookLM via a
Model Context Protocol (MCP) server and command-line interface (`nlm`). One install
gives both executables: `notebooklm-mcp` (MCP server) and `nlm` (CLI).

This is a **fork of [jacob-bd/notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli)**
focused on enterprise NotebookLM support. It adds the official Discovery Engine REST API
client alongside the existing personal batchexecute client, with seamless mode switching.

Users: developers and AI power users who want to automate NotebookLM from Claude Desktop,
Cursor, Codex, or other MCP-compatible AI tools.

Deployment: local machine tool, installed via `uv tool install .`. Config in `~/.notebooklm-mcp-cli/`.

Current state: v1.0.0, in active use. Enterprise mode tested against GCP project YOUR_PROJECT_ID.

---

## Architecture decisions

| Date | Decision | Why | Alternatives rejected |
|------|----------|-----|-----------------------|
| 2026-03 | Use official Discovery Engine REST API for enterprise (not batchexecute) | Stable, documented, supported | Enterprise batchexecute: works but fragile, same RPC IDs don't map cleanly |
| 2026-03 | Adapter pattern for enterprise client | Lets all existing MCP tools work in both modes without `if is_enterprise:` branches everywhere | Forking each service function: too much duplication |
| 2026-03 | Persistent config in `config.toml` `[enterprise]` section | Survives restarts; no env var editing | Env vars only: not persistent, requires manual editing of shell config and Claude Desktop JSON |
| 2026-03 | `configure_mode` validates auth before switching | Prevents confusing 400/401 errors when switching modes without the right auth | Silent switch: caused hard-to-debug auth failures |
| 2026-03 | Empty body for audio overview API | Enterprise audio API rejects all documented fields (episodeFocus, sourceIds, languageCode) despite documentation claiming support | Using documented fields: returns 400 |
| 2026-03 | Per-URL individual processing in bulk add | One failed URL shouldn't fail the whole batch; returns per-URL results | Batch API call: fails atomically, no partial results |
| 2026-04 | `tests/conftest.py` forces `NOTEBOOKLM_MODE=personal` | Prevents local config.toml enterprise mode from breaking the test suite | Per-test mode: harder to maintain |

---

## Key conventions

- **Mode selection**: `get_client()` in `mcp/tools/_utils.py` reads `get_config().enterprise.mode` and returns either `NotebookLMClient` (personal) or `EnterpriseAdapter(EnterpriseClient())` (enterprise)
- **Error surfacing**: `ServiceError.user_message` is what Claude sees; the internal message is for logs
- **Confirmation pattern**: Destructive operations require `confirm=True` parameter — Claude must ask the user before setting it
- **Enterprise unsupported features**: `enterprise_adapter.py` raises `NotImplementedError` with a clear "not available in enterprise mode" message — these propagate through `studio.py` service to the MCP tool response
- **Podcast tool**: The standalone podcast tool (`mcp/tools/podcast.py`) is self-contained — its own GCP auth, no dependency on enterprise client

---

## Known issues and gotchas

- **Enterprise audio overview API**: The API rejects all documented request fields. Must send empty `{}` body. The API automatically uses all notebook sources with default settings. Documented in `core/enterprise_client.py` comments.
- **Discovery Engine API is v1alpha**: Unstable — Google can change endpoints without notice. This is why upstream (`jacob-bd/notebooklm-mcp-cli`) declined the enterprise PR (#126). Watch for promotion to v1.
- **Personal batchexecute**: Reverse-engineered internal API. RPC IDs are obfuscated codes like `rG2vCb`, `tHcQ6c`. These can change with Google deployments. Build label (`bl`) is auto-extracted from the page on each session.
- **Duplicate MCP server issue**: If Claude Desktop shows two notebooklm servers or old version numbers, check Claude extensions (`~/.config/Claude/extensions-installations.json`) for a stale `local.mcpb.jacob-ben-david.notebooklm-mcp` entry.
- **Token expiry**: GCP tokens expire ~1 hour. gcloud handles refresh automatically on `gcloud auth print-access-token`. Personal cookies stable for weeks but some rotate per-request.
- **Pre-existing test failures resolved**: `TestFileUploadProtocol` tests (5 failures) were fixed by adding `client._profile = APIProfile()` when constructing `SourceMixin` via `__new__`. Root cause: `_profile` was added to `BaseClient.__init__` after these tests were written. The `TestFileUploadE2E::test_upload_text_file` error is expected when live credentials are expired — it's gated by `@pytest.mark.e2e`.

---

## External dependencies and integrations

| Name | Purpose | Where credentials are stored |
|------|---------|------------------------------|
| `notebooklm.google.com` | Personal NotebookLM API (batchexecute) | `~/.notebooklm-mcp-cli/profiles/<name>/auth.json` |
| `notebooklm.cloud.google.com` | Enterprise NotebookLM (not called directly — uses REST API) | n/a |
| `discoveryengine.googleapis.com/v1alpha` | Enterprise notebooks, sources, audio overview | GCP OAuth2 via `gcloud` — not stored by this project |
| `discoveryengine.googleapis.com/v1` | Standalone Podcast API (stable) | GCP OAuth2 via `gcloud` — not stored by this project |
| `accounts.google.com` | GCP authentication | Managed by `gcloud` SDK |
| Claude Desktop | MCP host (primary use case) | `~/Library/Application Support/Claude/claude_desktop_config.json` |

---

## Fork relationship

- **Upstream**: `jacob-bd/notebooklm-mcp-cli` — personal NotebookLM only
- **This fork**: `Robiton/notebooklm-mcp-cli` — enterprise + personal
- **PyPI package name**: `notebooklm-enterprise-mcp` — jacob-bd owns `notebooklm-mcp-cli` on PyPI at v0.5.16
- **Current synced upstream version**: v0.5.16 (cherry-picked through 2026-04-06)
- **Merged PRs on fork** (all into `enterprise-url-support`):
  - Robiton#2 — AI scaffold adoption — merged
  - Robiton#3 — package rename, CI fix, README identity — merged
  - Robiton#4 — CONTRIBUTING, CoC, SECURITY, issue templates — merged
  - Robiton#5 — debt cleanup, upstream sync workflow, .codex, release process — merged
  - Robiton#6 — upstream sync v0.5.11–v0.5.16 cherry-picks — merged
- **Upstream PR strategy**: **No further PRs to jacob-bd.** Both #126 (enterprise) and #129 (podcast) were closed by jacob-bd — his project is intentionally personal-only. We are a dual-use fork; that scope divergence is permanent. We will cherry-pick useful upstream fixes/features into our fork, but we no longer submit PRs back.
- **Skipped upstream commit**: `b31ab7e` (dual RPC fallback) — permanently skip; incompatible with our enterprise adapter design
- **Sync strategy**: Periodically cherry-pick from upstream/main; weekly upstream-check.yml opens a GitHub issue if we fall behind. One-way only — upstream → us.
- **`gh pr create` in fork**: Always use `--repo Robiton/notebooklm-mcp-cli --base <target> --head <branch>` explicitly — default detects upstream parent (jacob-bd) and creates PR there instead
- **ruff version**: Lock file pins ruff 0.14.14. Use `uv run --extra dev ruff` (NOT `uvx ruff`) for CI-consistent checks

### Upstream sync conflict hotspots

These files conflict on every upstream cherry-pick. Resolve manually:

| File | Conflict type |
|------|---------------|
| `mcp/server.py` | Enterprise tools registered alongside personal tools |
| `core/__init__.py` | Exports for both clients |
| `utils/config.py` | Enterprise config section |
| `pyproject.toml` | Version, package name, and deps |
| `CHANGELOG.md` | Upstream adds entries at top; our fork header must stay at top — always `git checkout --ours CHANGELOG.md` |

---

## Repository setup status (as of 2026-04-06)

| Item | Status |
|------|--------|
| GitHub Issues | ✅ Enabled |
| GitHub Discussions | ✅ Enabled |
| Issue templates (4) | ✅ In `.github/ISSUE_TEMPLATE/` |
| PR template | ✅ In `.github/PULL_REQUEST_TEMPLATE.md` |
| Dependabot | ✅ Weekly pip + Actions updates |
| SECURITY.md | ✅ Root level, GitHub recognizes it |
| CONTRIBUTING.md | ✅ Root level |
| CODE_OF_CONDUCT.md | ✅ Root level |
| Branch protection on main | ❌ Not yet — manual GitHub Settings step |
| Star history chart | ❌ Removed — re-add when repo has traction |
| PyPI trusted publisher (OIDC) | ✅ Configured (environment: pypi) |

---

## Fork ecosystem research (2026-04-06)

Reviewed ~430 active forks of jacob-bd/notebooklm-mcp-cli. Key findings:

### Worth implementing (not yet done)

| Fork | What it adds | Priority |
|------|-------------|----------|
| **D-intelligence** | `_safe_output_path()` — path traversal protection in downloads; `chmod 0o700` on credential dirs | High |
| **hectorreyes-ship-it** | SSRF URL validation (blocks private IPs, metadata endpoints); sensitive-dir blocklist in `add_file` | High |
| **RhysEJF** | CDP cookie allowlist: `Network.getCookies` filtered to NotebookLM domain instead of `getAllCookies` (prevents Gmail/Drive cookie capture) | High |
| **brainupgrade-in** | `custom_style_description` param for video overview — position 6 in RPC options array, ~100 lines | Low |
| **dizz** | OAuth 2.1 AS for remote MCP via claude.ai — enables hosted server scenario; no new deps | Low |

### Skipped

| Fork | Why |
|------|-----|
| **scguoi** | Different enterprise approach (RPC translation vs our REST API) — architecturally incompatible |
| **sc1zox** | Deliberately removes `delete_notebook` — reduces functionality |
| **byingyang/GugaMed/VooDisss** | Older `notebooklm-mcp` package format — needs porting, not worth it |
| Others | Personal tooling, localization, noise |

### Docker / hosted deployment research (pending)

Single-user container (one Google account per container) is viable as a distribution option for teams who don't want to install anything locally. Key open questions documented in BACKLOG.md Docker research task. Multi-user (multiple Google accounts per container) requires new multi-tenancy architecture not yet designed.

---

## 2026-04-06 — Scaffold adoption
- Decision: Add AI project scaffold (`Robiton/ai-project-scaffold`) to this repo
- Why: Persistent context across sessions; works with Claude Code, Cursor, Codex, Windsurf
- Overlay applied: `api-integration`
- Previous CLAUDE.md content migrated into this file and `ai/CODING.md`
