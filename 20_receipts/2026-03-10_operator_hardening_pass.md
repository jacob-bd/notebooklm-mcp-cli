# 2026-03-10 Operator Hardening Pass

PRD: PRD-NR01

## What changed

- Reviewed the last 7 nightly refresh runs (`2026-02-27` through `2026-03-05`)
  using `~/.config/notebooklm-mcp/refresh.log` and the paired batch receipts in
  `~/.config/notebooklm-mcp/sync_receipts/`.
- Updated `10_docs/prds/PRD-NR01_nightly_notebook_refresh.md` with the reviewed
  soak evidence and checked the unattended-run success criterion.
- Added a documented read-only smoke ladder to operator-facing docs so routine
  trust checks can use `notebooklm-sync --list`, `notebook_list`, and
  `notebook_get` without mutating NotebookLM state.
- Aligned the auth guidance surfaces around auto mode as the preferred operator
  path, with file mode documented as a manual fallback.
- Replaced the tracked `cookies.txt` template with `cookies.example.txt` and
  removed guidance that suggested pasting live cookies into the repo working tree.
- Refreshed `00_run/README.md` so it reflects the actual launchd schedule scripts
  and evidence locations.
- Updated `ROADMAP.md` so it reflects the new next steps instead of repeating
  work completed in this pass.

## Why

- The prior repo probe left three operator-trust threads open: nightly soak
  evidence, a non-mutating smoke workflow, and auth/template doc parity.
- The auth/template story had drifted across README, docs, CLAUDE guidance, and
  CLI help output, which made it too easy to pick the wrong path or paste secrets
  into a tracked filename.
- The repo needed evidence-first documentation that matches what the nightly
  receipts and the current local auth state actually show.

## Nightly review evidence

- Seven consecutive nightly batch receipts exist for `2026-02-27` through
  `2026-03-05`.
- `C021_notebooklm-mcp` was `skipped` with `reason=no_content_changes` on all
  seven nights.
- No orphan ledger activity appeared in the reviewed window
  (`orphans_cleaned=0`, `orphans_tracked=0` in each receipt).
- Failures in that window were artifact wait timeouts in other repos:
  - `P151_clouddriveinventory` on `2026-02-27`
  - `C001_mission-control`, `C003_sadb_canonical`, `C010_standards` on `2026-03-01`
  - `C010_standards` on `2026-03-02`
  - `C010_standards`, `C012_round-table` on `2026-03-03`
- Result: the unattended-run criterion is now evidenced, but the orphan/duplicate
  closeout still needs a window with actual replace activity or direct notebook-state verification.

## Verification

- `make verify`
  - `40 passed in 3.21s`
- `uv run notebooklm-mcp-auth --help`
  - confirms auto mode is now the recommended path and file mode is labeled manual fallback
- `uv run notebooklm-sync --help`
  - confirms CLI remains healthy after the doc/help changes
- `git diff --check`
  - clean
- `uv run notebooklm-sync --list`
  - currently fails with `ValueError: Cookies have expired. Please re-authenticate by running 'notebooklm-mcp-auth'.`
  - this was expectedly read-only and informed the new smoke/troubleshooting docs; no auth refresh was performed in this pass

## Files touched

- `README.md`
- `CLAUDE.md`
- `ROADMAP.md`
- `00_run/README.md`
- `docs/AUTHENTICATION.md`
- `docs/CLI.md`
- `docs/TROUBLESHOOTING.md`
- `docs/NOTEBOOKLM_MCP_OPERATIONS_MANUAL.md`
- `docs/notebooklm_mcp/SECURITY_AND_PRIVACY.md`
- `src/notebooklm_mcp/auth_cli.py`
- `.gitignore`
- `10_docs/prds/PRD-NR01_nightly_notebook_refresh.md`
- `cookies.example.txt`
- removed `cookies.txt`
