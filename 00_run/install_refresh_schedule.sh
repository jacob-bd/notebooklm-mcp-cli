#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCE_PLIST="$REPO_ROOT/30_config/com.notebooklm-mcp.refresh.plist"
TARGET_DIR="$HOME/Library/LaunchAgents"
TARGET_PLIST="$TARGET_DIR/com.notebooklm-mcp.refresh.plist"
LOG_DIR="$HOME/.config/notebooklm-mcp"

if [[ ! -f "$SOURCE_PLIST" ]]; then
  echo "Missing plist template: $SOURCE_PLIST" >&2
  exit 1
fi

mkdir -p "$TARGET_DIR" "$LOG_DIR"

TMP_PLIST="$(mktemp)"
sed \
  -e "s|__HOME__|$HOME|g" \
  -e "s|__REPO_ROOT__|$REPO_ROOT|g" \
  "$SOURCE_PLIST" > "$TMP_PLIST"

cp "$TMP_PLIST" "$TARGET_PLIST"
rm -f "$TMP_PLIST"

launchctl unload "$TARGET_PLIST" >/dev/null 2>&1 || true
launchctl load "$TARGET_PLIST"

echo "Installed launchd job: $TARGET_PLIST"
echo "Log path: $LOG_DIR/refresh.log"
echo "Scheduled: nightly at 02:00 local time"
