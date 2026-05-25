#!/usr/bin/env bash
# Stop background hotkey service and free the USB serial port.
set -euo pipefail

launchctl bootout "gui/$(id -u)" \
  "$HOME/Library/LaunchAgents/com.esp32-round-clock.pages" 2>/dev/null || true

# Kill hung send-page / hotkey Python holding /dev/cu.usbmodem*
for port in /dev/cu.usbmodem*; do
  [[ -e "$port" ]] || continue
  pids=$(lsof -t "$port" 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    echo "Closing processes on $port: $pids"
    kill $pids 2>/dev/null || true
  fi
done

pkill -f "mac_page_control.py" 2>/dev/null || true
pkill -f "esp32-clock-hotkeys" 2>/dev/null || true
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
echo "USB port should be free. Test:"
echo "  ~/Library/Application\\ Support/esp32-round-clock/send-page.sh next"
