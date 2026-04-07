# Team Roster and Ownership

_Updated when team membership or ownership changes._

---

## Team members

| Name | Role | AI tool | GitHub handle | Contact |
|------|------|---------|---------------|---------|
| Brian Worrell | IT / InfoSec | Claude Code, Claude Web | @Robiton | |

---

## Project ownership

| Area | Owner | Notes |
|------|-------|-------|
| Enterprise client + adapter | Brian | core/enterprise_client.py, core/enterprise_adapter.py |
| Personal client | Upstream (jacob-bd) | core/client.py — sync from upstream |
| MCP tools | Brian (fork additions) + Upstream | New tools in this fork owned by Brian |
| Config system | Brian | utils/config.py enterprise/sources sections |
| Security standards | Brian | ai/SECURITY.md |
| Upstream relationship | Brian | PRs, sync, tracking v1alpha promotion |

---

## Working agreements

- Never commit directly to `main` — always branch and PR
- `ai/SESSION.md` and `ai/BACKLOG.md` must be updated before closing any session
- Run `./sync-check.sh` before starting work
- Periodically check upstream for new commits and merge into enterprise-url-support
- Tag all releases before merging to main

---

## Upstream relationship

| Repo | Role |
|------|------|
| `jacob-bd/notebooklm-mcp-cli` | Upstream — personal NotebookLM features, sync source |
| `Robiton/notebooklm-mcp-cli` | This fork — enterprise + personal, Brian owns |
