# Receipt: Claudit Audit, Doc Freshness Pass, and META Refresh

- **Date**: 2026-05-31
- **Machine**: Mac-mini-2
- **Agent**: Atlas (Claude Code)
- **Branch**: main

## What was accomplished

1. **Claudit config audit** (comprehensive scope): 91 → **94/100, Grade A**, zero regressions
   from the 2026-04-10 pass. Applied fixes: project `.mcp.json` scoping `notebooklm-mcp`
   (PATH-portable), CLAUDE.md trim (101→97), narrowed `Bash(claude mcp list)` in
   settings.local.json, `docker rm`/`docker rmi` added to global deny list.
2. **Dismissed a false positive**: the codex plugin's `commands/` dir is current-spec slash
   commands (not legacy), recorded as `rejected` in claudit decision memory → Plugin Health
   88 → 95.
3. **Doc freshness pass**: CHANGELOG `[Unreleased]` gained 4 evidence-based entries
   (fastmcp 2.14.2→3.2.4 Security, `.mcp.json`, Python 3.13 pin, stignore Wave 1 re-align,
   CLAUDE 101→97). Regenerated PROJECT_PRIMER.md (SHA ff3bb2b) to drop stale embedded
   CLAUDE.md text. Refreshed META.yaml: `last_reviewed` → 2026-05-31, added missing
   `doc-refresh` executable.
4. **Verification**: `make health` → **53 passed in 3.22s**; all doc claims confirmed
   against ground truth (31 tools, fastmcp version, Python floor, doc-link targets).

## Key files changed

- `.mcp.json` (new), `CLAUDE.md`, `CHANGELOG.md`, `PROJECT_PRIMER.md` (regenerated), `META.yaml`
- Personal/global (not committed): `~/.claude/settings.json` (docker denies),
  `.claude/settings.local.json`, `.claude/claudit-decisions.json`

## Authority Map (drift resolved)

| Surface | Source of Truth | Status |
|---------|-----------------|--------|
| CLAUDE.md content in primer | `CLAUDE.md` (97 lines) | regenerated — stale text gone |
| Tool count (31) | `server.py` @mcp.tool() | matches all 6 doc surfaces |
| fastmcp version | `pyproject.toml` (==3.2.4) | logged in CHANGELOG Security |
| META executables | `pyproject.toml` entry points | added `doc-refresh` (generate-project-primer omitted — deprecated) |

## Commits this session

- `ff3bb2b` chore(config): scope notebooklm-mcp via .mcp.json + trim CLAUDE.md
- `f3a3b67` docs: refresh CHANGELOG and regenerate PROJECT_PRIMER
- (this) docs(meta): refresh last_reviewed + add doc-refresh executable

## TODOs / next steps

- [ ] Apply deferred `~/.claude.json` obsidian-files `transport: stdio` fix (run between
      sessions — live file is clobber-prone). One-liner recorded in claudit decision memory.
- [ ] Cosmetic: dead `if` field on verify-push hook — intentionally left (consistency risk).
- [ ] When convenient: remove deprecated `generate-project-primer` entry from pyproject.toml.
