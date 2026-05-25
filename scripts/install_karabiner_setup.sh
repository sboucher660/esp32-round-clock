#!/usr/bin/env bash
# Install Karabiner-friendly scripts + optional login cleanup (no background hotkey app).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="$HOME/Library/Application Support/esp32-round-clock"
LABEL="com.esp32-round-clock.login-cleanup"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"

mkdir -p "$APP_DIR"
cp "$ROOT/scripts/esp_port.py" "$ROOT/scripts/send_page.py" "$ROOT/scripts/send-page.sh" \
  "$ROOT/scripts/send-rotate.sh" \
  "$ROOT/scripts/karabiner-next.zsh" "$ROOT/scripts/karabiner-prev.zsh" \
  "$ROOT/scripts/karabiner-rotate-right.zsh" "$ROOT/scripts/karabiner-rotate-left.zsh" \
  "$APP_DIR/"
chmod +x "$APP_DIR/send-page.sh" "$APP_DIR/send-rotate.sh" "$APP_DIR/send_page.py" \
  "$APP_DIR"/karabiner-*.zsh 2>/dev/null || true
chmod +x "$APP_DIR/send-page.sh" "$APP_DIR/send_page.py" \
  "$APP_DIR/karabiner-next.zsh" "$APP_DIR/karabiner-prev.zsh"

# Stop old background hotkey service if present (conflicts with Karabiner + USB).
"$ROOT/scripts/stop-hotkeys.sh" 2>/dev/null || true
launchctl bootout "gui/$(id -u)" \
  "$HOME/Library/LaunchAgents/com.esp32-round-clock.pages.plist" 2>/dev/null || true

# After each login: free stale USB bridge only (fast, no hotkey listener).
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>${APP_DIR}/karabiner-next.zsh</string>
  </array>
  <key>RunAtLoad</key>
  <false/>
  <key>StartInterval</key>
  <integer>0</integer>
</dict>
</plist>
EOF

# Fix plist: login should only run stop-hotkeys, not send next
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>-lc</string>
    <string>${ROOT}/scripts/stop-hotkeys.sh</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${APP_DIR}/login-cleanup.log</string>
  <key>StandardErrorPath</key>
  <string>${APP_DIR}/login-cleanup.log</string>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

K_NEXT="$APP_DIR/karabiner-next.zsh"
K_PREV="$APP_DIR/karabiner-prev.zsh"

echo ""
echo "=== Installed ==="
echo "  $APP_DIR"
echo ""
echo "Karabiner shell_command (use these — stable after reboot):"
echo "  $K_NEXT"
echo "  $K_PREV"
echo ""
echo "=== Karabiner app ==="
echo "1. Karabiner-Elements → Settings → enable start at login"
echo "2. System Settings → General → Login Items → Karabiner ON"
echo "3. System Settings → Privacy → Input Monitoring → Karabiner ON"
echo "4. Complex Modifications → your rules → shell_command:"
echo "     $K_NEXT"
echo "     $K_PREV"
echo ""
echo "=== Test (clock on USB) ==="
echo "  $K_NEXT"
echo ""
