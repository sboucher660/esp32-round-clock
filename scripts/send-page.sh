#!/usr/bin/env bash
# Page control — USB only, instant (persistent daemon).
set -euo pipefail
APP_DIR="$HOME/Library/Application Support/esp32-round-clock"
PYTHON="${APP_DIR}/.venv/bin/python3"
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SELF_DIR/.." && pwd)"

# When run from the git repo, refresh Application Support copies.
if [[ "$REPO_ROOT" == */esp32-round-clock ]]; then
  mkdir -p "$APP_DIR"
  for f in esp_port.py usb_daemon.py send_page.py send-rotate.sh; do
    cp "$REPO_ROOT/scripts/$f" "$APP_DIR/"
  done
  chmod +x "$APP_DIR/send-page.sh" "$APP_DIR/send-rotate.sh" \
    "$APP_DIR/usb_daemon.py" "$APP_DIR/send_page.py" 2>/dev/null || true
fi

if [[ ! -x "$PYTHON" ]]; then
  python3 -m venv "$APP_DIR/.venv"
fi

if [[ ! -f "$APP_DIR/send_page.py" ]]; then
  echo "Missing $APP_DIR/send_page.py — run: ./scripts/install_usb_daemon.sh" >&2
  exit 1
fi

exec "$PYTHON" "$APP_DIR/send_page.py" "$@"
