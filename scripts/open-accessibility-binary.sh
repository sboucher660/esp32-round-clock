#!/usr/bin/env bash
open -R "$HOME/Applications/ESP32 Clock Hotkeys.app" 2>/dev/null || {
  echo "Run ./scripts/install_mac_page_daemon.sh first." >&2
  exit 1
}
echo "Drag \"ESP32 Clock Hotkeys\" into System Settings → Accessibility"
