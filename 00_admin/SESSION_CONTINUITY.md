# Session Continuity -- C021_notebooklm-mcp

<!-- Overwritten by /close-session. Do not edit manually. -->

## Last Session

- **Date**: 2026-04-10
- **Machine**: Mac-mini-2
- **Agent**: Atlas (Claude Code)
- **Branch**: main
- **Receipt**: 20_receipts/2026-04-10_claude_md_optimization_and_claudit_audit.md
- **Commit**: 08cef0d

## Summary

Three-pass CLAUDE.md optimization (improver → claudit → claudit re-audit) reduced the file from 202 → 101 lines (50% reduction, ~1,200 token savings per session). Claudit score improved 84 → 91 (B → A). Documentation freshness audit confirmed all surfaces current; archived WEEKEND_ROADMAP.md, deleted orphaned rules_now.md. Settings.local.json pruned to 35 clean rules (31 MCP + 4 Bash).

## Open Threads

- [ ] MCP server sprawl (11 global servers) — main Claudit ceiling (MCP Config: 75/100)
- [ ] Superpowers plugin SessionStart hook missing timeout (upstream issue)
- [ ] `generate-project-primer` entry still in pyproject.toml (deprecated, clean up when convenient)
- [ ] Consider project `.mcp.json` to scope notebooklm-mcp server to this repo

## Known Hazards

- Reverse-engineered NotebookLM APIs require fragile local auth (~25 calls before cookie rotation on free tier)
- macOS-only hooks (afplay, osascript) in global settings.json will fail silently on Windows sync target
