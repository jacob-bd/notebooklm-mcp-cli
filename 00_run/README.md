# 00_run

Operator-facing runtime helpers for the scheduled refresh pipeline live here.

## Current Scripts

- `install_refresh_schedule.sh` installs the local `launchd` job used for nightly refreshes
- `uninstall_refresh_schedule.sh` removes that `launchd` job

## Scheduled Command

The installed schedule runs:

```bash
notebooklm-sync --all --apply --changed-only
```

## Evidence Paths

- `~/.config/notebooklm-mcp/refresh.log`
- `~/.config/notebooklm-mcp/sync_receipts/`

## Read-Only Smoke

For the routine non-mutating verification path, use the smoke ladder in
`docs/CLI.md`:

```bash
notebooklm-sync --list
```
