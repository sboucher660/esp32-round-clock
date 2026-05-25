#!/usr/bin/env bash
# Remove obsolete ESP32 clock Mac helpers (Wi-Fi hotkeys, bridge, login-cleanup).
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

echo "Stopping USB daemon (restart with install_usb_daemon.sh)..."
if [[ -f "$APP_DIR/usb_daemon.py" ]]; then
  "$APP_DIR/.venv/bin/python3" "$APP_DIR/usb_daemon.py" --stop 2>/dev/null || true
fi
pkill -f "usb_daemon.py --run" 2>/dev/null || true
pkill -f "mac_page_control.py" 2>/dev/null || true

echo "Removing old hotkey app..."
rm -rf "$HOME/Applications/ESP32 Clock Hotkeys.app"

echo "Removing obsolete Application Support files..."
cd "$APP_DIR" 2>/dev/null || exit 0
rm -f \
  bridge.log bridge.pid bridge.sock \
  clock-host.txt \
  login-cleanup.log \
  mac_page_control.py \
  requirements.txt \
  hotkey-events.log 2>/dev/null || true
rm -rf logs 2>/dev/null || true

echo ""
echo "Kept (active USB daemon setup):"
ls -1 "$APP_DIR" 2>/dev/null | grep -v __pycache__ | grep -v '^\.venv$' || true
echo ""
echo "To restart USB control:"
echo "  cd ~/Documents/esp32-round-clock && ./scripts/install_usb_daemon.sh"
