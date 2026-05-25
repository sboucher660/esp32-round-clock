#!/usr/bin/env bash
# Install Mac → clock notification forwarding (requires clock on Wi-Fi).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="$HOME/Library/Application Support/esp32-round-clock"
LABEL="com.esp32-round-clock.notifications"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
PYTHON="$APP_DIR/.venv/bin/python3"

mkdir -p "$APP_DIR"
cp "$ROOT/scripts/notification_forward.py" "$ROOT/scripts/forward-notification.sh" "$APP_DIR/"
chmod +x "$APP_DIR/notification_forward.py" "$APP_DIR/forward-notification.sh"

if [[ ! -x "$PYTHON" ]]; then
  python3 -m venv "$APP_DIR/.venv"
fi

if [[ ! -f "$APP_DIR/clock-host.txt" ]]; then
  echo "Save clock IP first (Network screen on device):"
  echo "  $PYTHON $APP_DIR/send_page.py --save-host 192.168.x.x"
  exit 1
fi

sed "s|HOME_PLACEHOLDER|$HOME|g" > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${PYTHON}</string>
    <string>${APP_DIR}/notification_forward.py</string>
    <string>watch</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${APP_DIR}/notification-forward.log</string>
  <key>StandardErrorPath</key>
  <string>${APP_DIR}/notification-forward.log</string>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo ""
echo "Notification forwarder installed (experimental log stream)."
echo "Reliable option: Apple Shortcuts — see docs/NOTIFICATIONS.md"
echo ""
echo "Test:"
echo "  $APP_DIR/notification_forward.py test"
echo "Log: $APP_DIR/notification-forward.log"
