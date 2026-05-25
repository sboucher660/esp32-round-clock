#!/usr/bin/env bash
# Mac hotkeys → ESP32 page control (uses project .venv)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -x "$ROOT/.venv/bin/python3" ]]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
  .venv/bin/pip install -r scripts/requirements-mac-control.txt
fi

exec "$ROOT/.venv/bin/python3" "$ROOT/scripts/mac_page_control.py" "$@"
