#!/usr/bin/env bash
# Stop USB daemon + hotkeys and free the serial port (before pio upload).
set -euo pipefail

UID_NUM="$(id -u)"
launchctl bootout "gui/$UID_NUM" \
  "$HOME/Library/LaunchAgents/com.esp32-round-clock.pages.plist" 2>/dev/null || true
launchctl bootout "gui/$UID_NUM" \
  "$HOME/Library/LaunchAgents/com.esp32-round-clock.hotkeys.plist" 2>/dev/null || true
launchctl bootout "gui/$UID_NUM" \
  "$HOME/Library/LaunchAgents/com.esp32-round-clock.usb-daemon.plist" 2>/dev/null || true

for port in /dev/cu.usbmodem*; do
  [[ -e "$port" ]] || continue
  pids=$(lsof -t "$port" 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    echo "Closing processes on $port: $pids"
    kill $pids 2>/dev/null || true
  fi
done

pkill -f "hotkey_listener.py" 2>/dev/null || true
pkill -f "ESP32 Clock.app" 2>/dev/null || true
pkill -f "send_page.py" 2>/dev/null || true

USB_PY="$HOME/Library/Application Support/esp32-round-clock/usb_daemon.py"
if [[ -f "$USB_PY" ]]; then
  "$HOME/Library/Application Support/esp32-round-clock/.venv/bin/python3" \
    "$USB_PY" --stop 2>/dev/null || true
fi
rm -f "$HOME/Library/Application Support/esp32-round-clock/bridge.sock" \
      "$HOME/Library/Application Support/esp32-round-clock/bridge.pid" \
      "$HOME/Library/Application Support/esp32-round-clock/usb.sock" \
      "$HOME/Library/Application Support/esp32-round-clock/usb-daemon.pid" 2>/dev/null || true

sleep 0.5
echo "Stopped (safe for pio upload)."
echo "After flash: ./scripts/install_usb_daemon.sh"
