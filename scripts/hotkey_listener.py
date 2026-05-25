#!/usr/bin/env python3
"""
Global macOS hotkeys → ESP32 USB daemon.

Requires one-time Accessibility for: ESP32 Clock.app
"""

from __future__ import annotations

import argparse
import os
import sys
import time

APP_DIR = os.path.expanduser("~/Library/Application Support/esp32-round-clock")
CONFIG_PATH = os.path.join(APP_DIR, "port.txt")
LOG_PATH = os.path.join(APP_DIR, "hotkey-events.log")

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

try:
    from pynput import keyboard
except ImportError:
    print("Run: ./scripts/install_usb_daemon.sh", file=sys.stderr)
    raise SystemExit(1) from None

from esp_port import find_port  # noqa: E402
from usb_daemon import daemon_running, send_command, start_daemon  # noqa: E402

DEBOUNCE_SEC = 0.35
_last_fire: dict[str, float] = {}

HOTKEY_TO_CMD = {
    "<cmd>+<shift>+<right>": "next",
    "<cmd>+<shift>+<left>": "prev",
    "<cmd>+<shift>+<up>": "rotate-right",
    "<cmd>+<shift>+<down>": "rotate-left",
}


def log_event(msg: str) -> None:
    os.makedirs(APP_DIR, exist_ok=True)
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n"
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line)
    print(msg, flush=True)


def dispatch(cmd: str) -> None:
    now = time.monotonic()
    if now - _last_fire.get(cmd, 0.0) < DEBOUNCE_SEC:
        return
    _last_fire[cmd] = now
    try:
        if not daemon_running():
            port = find_port(config_path=CONFIG_PATH, save=True)
            if not port:
                log_event(f"hotkey {cmd}: no USB port")
                return
            start_daemon(port)
        send_command(cmd)
        log_event(f"hotkey → {cmd}")
    except Exception as exc:
        log_event(f"hotkey {cmd} failed: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--test-keys",
        action="store_true",
        help="Listen 15s and log any key (verify Accessibility)",
    )
    args = parser.parse_args()

    if args.test_keys:
        log_event("TEST MODE: press ⌘⇧ arrow keys (15 seconds)")
        count = 0

        def on_press(key: keyboard.Key | keyboard.KeyCode) -> None:
            nonlocal count
            count += 1
            log_event(f"key: {key}")

        with keyboard.Listener(on_press=on_press) as listener:
            time.sleep(15)
            listener.stop()
        return 0 if count else 1

    log_event(
        "Hotkeys active (⌘⇧→ next, ← prev, ↑ rotate right, ↓ rotate left). "
        "If nothing happens: System Settings → Privacy → Accessibility → "
        "ESP32 Clock ON, then: open -a 'ESP32 Clock'"
    )

    hotkeys = {combo: (lambda c=cmd: dispatch(c)) for combo, cmd in HOTKEY_TO_CMD.items()}

    try:
        with keyboard.GlobalHotKeys(hotkeys) as hk:
            hk.join()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
