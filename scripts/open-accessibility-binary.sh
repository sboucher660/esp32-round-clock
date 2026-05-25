#!/usr/bin/env bash
open -R "$HOME/Applications/ESP32 Clock.app" 2>/dev/null || {
  echo "Run ./scripts/install_usb_daemon.sh first" >&2
  exit 1
}
echo "Drag \"ESP32 Clock\" into System Settings → Privacy & Security → Accessibility"
