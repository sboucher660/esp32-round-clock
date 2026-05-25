#!/usr/bin/env python3
"""ESP32 round clock control — USB-only via persistent daemon (instant)."""

from __future__ import annotations

import argparse
import sys

_SCRIPT_DIR = __import__("os").path.dirname(__import__("os").path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from esp_port import find_port  # noqa: E402
from usb_daemon import send_command as usb_send, stop_daemon, start_daemon, daemon_running  # noqa: E402

APP_DIR = __import__("os").path.expanduser("~/Library/Application Support/esp32-round-clock")
CONFIG = APP_DIR + "/port.txt"

COMMANDS = {
    "next", "n", "prev", "p",
    "rotate-right", "right", "r",
    "rotate-left", "left", "l",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="ESP32 clock (USB only)")
    parser.add_argument("command", choices=sorted(COMMANDS))
    parser.add_argument("--port")
    parser.add_argument("--restart-daemon", action="store_true")
    parser.add_argument("--stop-daemon", action="store_true")
    args = parser.parse_args()

    if args.stop_daemon:
        stop_daemon()
        print("USB daemon stopped.")
        return 0

    if args.restart_daemon:
        stop_daemon()

    port = find_port(args.port, config_path=CONFIG, save=True)
    if not port:
        print("No ESP32 USB port. Plug in with a data cable.", file=sys.stderr)
        return 1

    try:
        if args.restart_daemon or not daemon_running():
            start_daemon(port)
        usb_send(args.command, port)
    except Exception as exc:
        print(exc, file=sys.stderr)
        print("Try: send_page.py --restart-daemon next", file=sys.stderr)
        print("Or reboot the clock (RESET button).", file=sys.stderr)
        return 1

    print(f"Sent '{args.command}' via USB → {port}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
