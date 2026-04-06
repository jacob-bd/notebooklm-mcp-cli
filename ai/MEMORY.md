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

Current state: v1.0.0, in active use. Enterprise mode tested against GCP project 204404889700.

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
- **Pre-existing test failures**: `tests/services/test_downloads.py` and `tests/test_file_upload.py` have ~19 pre-existing failures unrelated to this fork's changes. These were present in upstream before forking.

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
- **Open PRs on fork**:
  - Robiton/notebooklm-mcp-cli#2 — scaffold adoption (chore/add-scaffold → enterprise-url-support) — open
- **Open upstream PRs**:
  - `#129` — standalone podcast tool (podcast-standalone branch) — pending review
  - `#126` — full enterprise support — declined (v1alpha instability concern)
- **Sync strategy**: Periodically merge upstream/main into enterprise-url-support branch
- **Re-submit enterprise PR trigger**: When Discovery Engine API promotes from v1alpha to v1
- **`gh pr create` in fork**: Always use `--repo Robiton/notebooklm-mcp-cli --head <branch>` or it defaults to the upstream parent (jacob-bd)

---

## 2026-04-06 — Scaffold adoption
- Decision: Add AI project scaffold (`Robiton/ai-project-scaffold`) to this repo
- Why: Persistent context across sessions; works with Claude Code, Cursor, Codex, Windsurf
- Overlay applied: `api-integration`
- Previous CLAUDE.md content migrated into this file and `ai/CODING.md`
