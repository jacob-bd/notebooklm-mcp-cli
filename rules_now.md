# C021 NotebookLM MCP — Rules Now

## Source of Truth Priority
- Highest for this repo: `AGENTS.md` and `CLAUDE.md`, then `README.md` and `META.yaml`.
- For deeper standards, defer to `/Users/jeremybradford/SyncedProjects/C010_standards`.

## Immediate Execution Rules
- Keep changes focused; avoid new top-level directories without explicit approval.
- Never commit secrets, tokens, or raw auth data.
- Use `20_receipts/` entries for substantive, non-trivial edits.
- Prefer verification-first; run local checks before reporting done.

## Core Commands
- Run tests: `make verify`
- Run all tests with coverage: `uv run pytest --cov=notebooklm_mcp --cov-report=term-missing -q`
- Install locally (for local development): `uv tool install .`

## Repo-Specific Operational Notes
- Auth depends on NotebookLM cookies; avoid committing any cookie content.
- Primary structure is canonical `0X_` folders with `src/` as current legacy source layout.
- Keep `10_docs/` as the active workspace for notes and receipts-backed operational planning.
