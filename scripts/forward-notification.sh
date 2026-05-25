#!/usr/bin/env bash
# Called by Apple Shortcuts when a Mac notification arrives.
# Usage: forward-notification.sh "App Name" "Title" "Body"
set -euo pipefail
APP_DIR="$HOME/Library/Application Support/esp32-round-clock"
PYTHON="${APP_DIR}/.venv/bin/python3"
exec "$PYTHON" "$APP_DIR/notification_forward.py" send \
  --app "${1:-Notification}" \
  --title "${2:-}" \
  --body "${3:-}"
