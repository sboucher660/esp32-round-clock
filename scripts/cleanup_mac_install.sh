#!/usr/bin/env bash
# Reset Mac install artifacts before install_usb_daemon.sh.
set -euo pipefail

APP_DIR="$HOME/Library/Application Support/esp32-round-clock"
GUI="gui/$(id -u)"

echo "Stopping old LaunchAgents..."
for plist in \
  "$HOME/Library/LaunchAgents/com.esp32-round-clock.pages.plist" \
  "$HOME/Library/LaunchAgents/com.esp32-round-clock.login-cleanup.plist"; do
  launchctl bootout "$GUI" "$plist" 2>/dev/null || true
  rm -f "$plist"
done

echo "Stopping USB daemon..."
if [[ -f "$APP_DIR/usb_daemon.py" ]]; then
  "$APP_DIR/.venv/bin/python3" "$APP_DIR/usb_daemon.py" --stop 2>/dev/null || true
fi
pkill -f "usb_daemon.py --run" 2>/dev/null || true
pkill -f "hotkey_listener.py" 2>/dev/null || true

echo "Removing obsolete app bundle..."
rm -rf "$HOME/Applications/ESP32 Clock Hotkeys.app"

echo "Cleaning Application Support..."
cd "$APP_DIR" 2>/dev/null || exit 0
rm -f \
  bridge.log bridge.pid bridge.sock \
  clock-host.txt \
  login-cleanup.log \
  requirements.txt \
  hotkey-events.log 2>/dev/null || true
rm -f "$APP_DIR"/*.zsh 2>/dev/null || true
rm -rf logs 2>/dev/null || true

echo ""
echo "Run: ./scripts/install_usb_daemon.sh"
