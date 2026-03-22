# Revision History

This file records repo-local integration and operator notes that complement the upstream release-focused [CHANGELOG.md](CHANGELOG.md).

## 2026-03-22

### mcp_stuff Promotion And Shared-State Setup Summary

- Promoted the repo from `pending_mcps/notebooklm-mcp-cli` to top-level `mcp_stuff/notebooklm-mcp-cli`.
- Installed the package with `uv` and validated the unified `nlm` CLI plus `notebooklm-mcp` server workflow.
- Configured Codex with an env-aware `notebooklm-mcp` entry so NotebookLM state resolves through `NOTEBOOKLM_MCP_CLI_PATH` instead of a separate default home-path tree.
- Used a durable data root under `/Volumes/Data/_ai/_mcp/mcp-data/notebooklm-mcp-cli` so manual CLI use, Codex MCP launches, and future client reuse can share profiles and auth state.
- Installed the cross-tool NotebookLM skill via `nlm skill install agents` and exported the reusable bundle with `nlm skill install other --level project` for future Claude Code and Ollama-adjacent agent setup.
- Set the preferred auth browser, completed browser-based login, and verified the saved profile with `nlm login --check`.

### Validation Notes

- Confirmed the Codex MCP entry resolves to `notebooklm-mcp` with `NOTEBOOKLM_MCP_CLI_PATH` set.
- Confirmed `nlm setup list` shows Codex configured.
- Confirmed `nlm skill list` shows the skill install succeeded.
- Confirmed both direct env-based invocation and a fresh shell loading the shared env path can run `nlm login --check` successfully.

### Caveats

- In this validated shared-state deployment, `nlm doctor` did not fully recognize the env-aware Codex entry even though direct MCP and auth checks succeeded.
- Machine-local shell exports, MCP client config files, and authentication material are intentionally not tracked in git; only the workflow and operational notes are recorded here.
