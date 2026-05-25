#!/usr/bin/env bash
# Rotate display — USB only (same daemon as send-page).
set -euo pipefail
APP_DIR="$HOME/Library/Application Support/esp32-round-clock"
PYTHON="${APP_DIR}/.venv/bin/python3"

case "${1:-}" in
  right|r|cw) cmd=rotate-right ;;
  left|l|ccw) cmd=rotate-left ;;
  *)
    echo "Usage: $0 left|right" >&2
    exit 1
    ;;
esac

exec "$PYTHON" "$APP_DIR/send_page.py" "$cmd"
