#!/usr/bin/env bash
set -euo pipefail

TARGET_PLIST="$HOME/Library/LaunchAgents/com.notebooklm-mcp.refresh.plist"

if [[ -f "$TARGET_PLIST" ]]; then
  launchctl unload "$TARGET_PLIST" >/dev/null 2>&1 || true
  rm -f "$TARGET_PLIST"
  echo "Removed launchd job: $TARGET_PLIST"
else
  echo "No launchd job found at: $TARGET_PLIST"
fi
