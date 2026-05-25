#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.esp32-round-clock.pages"
PLIST_DEST="$HOME/Library/LaunchAgents/${LABEL}.plist"
APP_DIR="$HOME/Library/Application Support/esp32-round-clock"
PYTHON="$APP_DIR/.venv/bin/python3"
SCRIPT="$APP_DIR/mac_page_control.py"
LOG_DIR="$APP_DIR/logs"
MAC_APP="$HOME/Applications/ESP32 Clock Hotkeys.app"
MAC_EXE="$MAC_APP/Contents/MacOS/esp32-clock-hotkeys"
SEND_PAGE="$ROOT/scripts/send-page.sh"

mkdir -p "$APP_DIR/logs" "$HOME/Applications"
cp "$ROOT/scripts/mac_page_control.py" "$SCRIPT"
cp "$ROOT/scripts/esp_port.py" "$APP_DIR/esp_port.py"
cp "$ROOT/scripts/send_page.py" "$APP_DIR/send_page.py"
cp "$ROOT/scripts/send-page.sh" "$APP_DIR/send-page.sh"
chmod +x "$APP_DIR/send_page.py" "$APP_DIR/send-page.sh" "$ROOT/scripts/send_page.py" "$ROOT/scripts/send-page.sh"
cp "$ROOT/scripts/requirements-mac-control.txt" "$APP_DIR/requirements.txt"

if [[ ! -x "$PYTHON" ]]; then
  python3 -m venv "$APP_DIR/.venv"
  "$PYTHON" -m pip install -q -r "$APP_DIR/requirements.txt"
fi

DETECTED=$("$PYTHON" "$SCRIPT" --list-ports 2>/dev/null | awk '/Auto-pick:/ {print $2}')
if [[ -n "${DETECTED:-}" ]]; then
  echo "$DETECTED" > "$APP_DIR/port.txt"
fi

mkdir -p "$MAC_APP/Contents/MacOS"
cat > "$MAC_EXE" <<EOF
#!/bin/bash
exec "$PYTHON" "$SCRIPT" --wait
EOF
chmod +x "$MAC_EXE"

cat > "$MAC_APP/Contents/Info.plist" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleExecutable</key>
  <string>esp32-clock-hotkeys</string>
  <key>CFBundleIdentifier</key>
  <string>com.esp32-round-clock.hotkeys</string>
  <key>CFBundleName</key>
  <string>ESP32 Clock Hotkeys</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>LSMinimumSystemVersion</key>
  <string>12.0</string>
  <key>LSUIElement</key>
  <true/>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)" "$PLIST_DEST" 2>/dev/null || true

# Launch the .app via `open` so macOS links Accessibility to the bundle (not raw launchd exec).
cat > "$PLIST_DEST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/open</string>
    <string>-gj</string>
    <string>${MAC_APP}</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <dict>
    <key>SuccessfulExit</key>
    <false/>
  </dict>
  <key>ThrottleInterval</key>
  <integer>30</integer>
</dict>
</plist>
EOF

launchctl bootstrap "gui/$(id -u)" "$PLIST_DEST"
sleep 2
open -gj "$MAC_APP" 2>/dev/null || true

echo ""
echo "=== FIX ACCESSIBILITY (required for Cmd+Shift+arrows) ==="
echo "1. System Settings → Privacy & Security → Accessibility"
echo "2. Click + → Applications → ESP32 Clock Hotkeys → ON"
echo "3. In Terminal, run:"
echo "     open -a 'ESP32 Clock Hotkeys'"
echo "4. Test keys (15 sec):"
echo "     $PYTHON $SCRIPT --test-keys"
echo "   Check: ~/Library/Application Support/esp32-round-clock/hotkey-events.log"
echo ""
echo "=== IF STILL BROKEN: use Apple Shortcuts (always works) ==="
echo "See: scripts/SHORTCUTS-SETUP.md"
echo ""
echo "Quick test serial (no hotkeys):"
echo "  $APP_DIR/send-page.sh next"
echo ""
open -R "$MAC_APP" 2>/dev/null || true
