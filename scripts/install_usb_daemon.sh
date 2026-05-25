#!/usr/bin/env bash
# USB-only instant control: LaunchAgent daemon (proper macOS install).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="$HOME/Library/Application Support/esp32-round-clock"
LABEL="com.esp32-round-clock.usb-daemon"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
PYTHON="$APP_DIR/.venv/bin/python3"

"$ROOT/scripts/cleanup_mac_install.sh"

mkdir -p "$APP_DIR"
cp "$ROOT/scripts/esp_port.py" "$ROOT/scripts/usb_daemon.py" "$ROOT/scripts/send_page.py" \
  "$ROOT/scripts/send-page.sh" "$ROOT/scripts/send-rotate.sh" "$APP_DIR/"
chmod +x "$APP_DIR"/*.sh "$APP_DIR/usb_daemon.py" "$APP_DIR/send_page.py" 2>/dev/null || true

if [[ ! -x "$PYTHON" ]]; then
  python3 -m venv "$APP_DIR/.venv"
fi

sed "s|HOME_PLACEHOLDER|$HOME|g" "$ROOT/scripts/com.esp32-round-clock.usb-daemon.plist" > "$PLIST"

launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

sleep 0.5
"$PYTHON" "$APP_DIR/send_page.py" --restart-daemon next 2>/dev/null || \
  echo "Plug in USB, then: ~/Library/Application\\ Support/esp32-round-clock/send-page.sh next"

echo ""
echo "=== Installed ==="
echo "Daemon:  launchctl print gui/$(id -u)/$LABEL"
echo "Data:    $APP_DIR"
echo "Commands:"
echo "  ~/Library/Application\\ Support/esp32-round-clock/send-page.sh next|prev"
echo "  ~/Library/Application\\ Support/esp32-round-clock/send-rotate.sh left|right"
echo "Log:     $APP_DIR/usb-daemon.log"
