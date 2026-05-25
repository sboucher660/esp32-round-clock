#!/usr/bin/env bash
# USB instant control + built-in macOS hotkeys.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="$HOME/Library/Application Support/esp32-round-clock"
LABEL="com.esp32-round-clock.usb-daemon"
HOTKEYS_LABEL="com.esp32-round-clock.hotkeys"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
HOTKEYS_PLIST="$HOME/Library/LaunchAgents/${HOTKEYS_LABEL}.plist"
PYTHON="$APP_DIR/.venv/bin/python3"
MAC_APP="$HOME/Applications/ESP32 Clock.app"
MAC_EXE="$MAC_APP/Contents/MacOS/esp32-clock"
GUI="gui/$(id -u)"

"$ROOT/scripts/cleanup_mac_install.sh"

mkdir -p "$APP_DIR" "$HOME/Applications"
cp "$ROOT/scripts/esp_port.py" "$ROOT/scripts/usb_daemon.py" "$ROOT/scripts/send_page.py" \
  "$ROOT/scripts/hotkey_listener.py" \
  "$ROOT/scripts/send-page.sh" "$ROOT/scripts/send-rotate.sh" "$APP_DIR/"
chmod +x "$APP_DIR"/*.sh "$APP_DIR/usb_daemon.py" "$APP_DIR/send_page.py" \
  "$APP_DIR/hotkey_listener.py" 2>/dev/null || true

if [[ ! -x "$PYTHON" ]]; then
  python3 -m venv "$APP_DIR/.venv"
fi
"$PYTHON" -m pip install -q -r "$ROOT/scripts/requirements-mac-hotkeys.txt"

# Background app bundle (macOS links Accessibility to the .app, not raw Python).
mkdir -p "$MAC_APP/Contents/MacOS"
cat > "$MAC_EXE" <<EOF
#!/bin/bash
exec "$PYTHON" "$APP_DIR/hotkey_listener.py"
EOF
chmod +x "$MAC_EXE"

cat > "$MAC_APP/Contents/Info.plist" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleExecutable</key>
  <string>esp32-clock</string>
  <key>CFBundleIdentifier</key>
  <string>com.esp32-round-clock.hotkeys</string>
  <key>CFBundleName</key>
  <string>ESP32 Clock</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>LSMinimumSystemVersion</key>
  <string>12.0</string>
  <key>LSUIElement</key>
  <true/>
</dict>
</plist>
EOF

sed "s|HOME_PLACEHOLDER|$HOME|g" "$ROOT/scripts/com.esp32-round-clock.usb-daemon.plist" > "$PLIST"
sed "s|HOME_PLACEHOLDER|$HOME|g" "$ROOT/scripts/com.esp32-round-clock.hotkeys.plist" > "$HOTKEYS_PLIST"

launchctl bootout "$GUI" "$PLIST" 2>/dev/null || true
launchctl bootout "$GUI" "$HOTKEYS_PLIST" 2>/dev/null || true
launchctl bootstrap "$GUI" "$PLIST"
launchctl bootstrap "$GUI" "$HOTKEYS_PLIST"

sleep 0.5
open -gj "$MAC_APP" 2>/dev/null || true

"$PYTHON" "$APP_DIR/send_page.py" --restart-daemon next 2>/dev/null || \
  echo "Plug in USB, then: ~/Library/Application\\ Support/esp32-round-clock/send-page.sh next"

echo ""
echo "=== Installed (USB daemon + hotkeys) ==="
echo "USB daemon:  launchctl print $GUI/$LABEL"
echo "Hotkeys app: $MAC_APP"
echo "Data:        $APP_DIR"
echo ""
echo "Hotkeys:"
echo "  ⌘⇧→  next page     ⌘⇧←  previous page"
echo "  ⌘⇧↑  rotate right   ⌘⇧↓  rotate left"
echo ""
echo "=== One-time: enable Accessibility ==="
echo "System Settings → Privacy & Security → Accessibility"
echo "  Turn ON: ESP32 Clock"
echo "Then: open -a 'ESP32 Clock'"
echo "Test:  $PYTHON $APP_DIR/hotkey_listener.py --test-keys"
echo ""
echo "Log: $APP_DIR/hotkey-events.log"
echo "Before pio upload: ./scripts/stop-hotkeys.sh"
