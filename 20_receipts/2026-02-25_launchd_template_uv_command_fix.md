# Receipt: launchd template command path fix

Date: 2026-02-25

## What changed
- Updated `30_config/com.notebooklm-mcp.refresh.plist` so future `make install-schedule` installs use:
  - `__HOME__/.local/bin/uv run notebooklm-sync --all --apply --changed-only`

## Why
- launchd runs with a minimal PATH, and `notebooklm-sync` was not reliably discoverable via plain command name.
- Using the explicit `uv` path makes scheduled execution consistent for this environment.

## Verification
- `plutil -lint 30_config/com.notebooklm-mcp.refresh.plist` -> `OK`
- Confirmed command string contains `uv run notebooklm-sync --all --apply --changed-only`.

## Files touched
- `30_config/com.notebooklm-mcp.refresh.plist`
