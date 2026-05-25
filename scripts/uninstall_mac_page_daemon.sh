#!/usr/bin/env bash
set -euo pipefail

LABEL="com.esp32-round-clock.pages"
PLIST_DEST="$HOME/Library/LaunchAgents/${LABEL}.plist"

launchctl bootout "gui/$(id -u)" "$PLIST_DEST" 2>/dev/null || true
rm -f "$PLIST_DEST"

echo "Removed ${LABEL} (LaunchAgent stopped)"
echo "App data kept at: ~/Library/Application Support/esp32-round-clock/"
echo "Delete that folder too if you want a full cleanup."
