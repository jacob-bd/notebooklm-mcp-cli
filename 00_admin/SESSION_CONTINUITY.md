# Session Continuity -- C021_notebooklm-mcp

<!-- Overwritten by /close-session. Do not edit manually. -->

## Last Session

- **Date**: 2026-05-31
- **Machine**: Mac-mini-2
- **Agent**: Atlas (Claude Code)
- **Branch**: main
- **Receipt**: 20_receipts/2026-05-31_claudit_audit_doc_freshness_and_meta_refresh.md
- **Commit**: 37608bc

## Summary

Ran a claudit config audit (91 → 94/100, Grade A, zero regressions) and applied fixes:
project `.mcp.json` scoping `notebooklm-mcp`, CLAUDE.md trim (101→97), narrowed
`claude mcp` permission, and global docker denies. Then a doc freshness pass updated
CHANGELOG (incl. fastmcp 2.14.2→3.2.4 Security entry), regenerated PROJECT_PRIMER.md, and
refreshed META.yaml. Verified clean: `make health` → 53 passed.

## Open Threads

- [ ] Remove deprecated `generate-project-primer` entry from `pyproject.toml` (cleanup when convenient).

## Known Hazards

- Reverse-engineered NotebookLM APIs require fragile local auth (~25 calls before cookie rotation on free tier).
- `PROJECT_PRIMER.md` is a generated artifact — regenerate via `generate-project-primer`, never hand-edit; it embeds the repo SHA so a 1-commit drift after committing is expected (do NOT amend-loop to fix).
- Repo syncs Mac↔Windows via Syncthing — honor cross-platform filename/symlink rules (no colons in timestamps, no symlinks in tree).
- `make verify`/`make health` run `uv run pytest` without `PYTHONPATH=src`; both that and the CLAUDE.md-documented `PYTHONPATH=src uv run pytest` work (package is import-discoverable).
