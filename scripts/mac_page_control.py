#!/usr/bin/env python3
"""
Mac hotkeys → ESP32 round clock (Cmd+Shift+Left / Cmd+Shift+Right).

Requires Accessibility for: ESP32 Clock Hotkeys.app (in ~/Applications)
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
import threading
import time

LOG_PATH = os.path.expanduser(
    "~/Library/Application Support/esp32-round-clock/hotkey-events.log"
)

try:
    import serial
    import serial.tools.list_ports
    from pynput import keyboard
except ImportError:
    print("Run: ./scripts/install_mac_page_daemon.sh", file=sys.stderr)
    sys.exit(1)

DEBOUNCE_SEC = 0.35
WAIT_POLL_SEC = 2.0
CONFIG_PATH = os.path.expanduser(
    "~/Library/Application Support/esp32-round-clock/port.txt"
)
ESPRESSIF_VID = 0x303A


def log_event(msg: str) -> None:
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n"
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line)
    print(msg, flush=True)


def _esp_port_module():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    import esp_port

    return esp_port


def read_config_port() -> str | None:
    return _esp_port_module().read_saved_port(CONFIG_PATH)


def find_esp_port() -> str | None:
    return _esp_port_module().find_port(config_path=CONFIG_PATH, save=True)


def wait_for_port(explicit: str | None) -> str:
    while True:
        port = explicit or read_config_port() or find_esp_port()
        if port:
            return port
        log_event("Waiting for Espressif USB…")
        time.sleep(WAIT_POLL_SEC)


class ClockSerial:
    def __init__(self, port: str, baud: int, wait: bool) -> None:
        self._explicit = port
        self._baud = baud
        self._wait = wait
        self._ser: serial.Serial | None = None
        self._lock = threading.Lock()
        self._last_send = 0.0

    def _resolve_port(self) -> str:
        if self._explicit:
            return self._explicit
        found = read_config_port() or find_esp_port()
        if found:
            return found
        if self._wait:
            return wait_for_port(None)
        raise serial.SerialException("no Espressif serial port")

    def open(self) -> str:
        while True:
            port = self._resolve_port()
            try:
                self._ser = serial.Serial(port, self._baud, timeout=0.1)
                time.sleep(0.2)
                return port
            except serial.SerialException as exc:
                if self._ser and self._ser.is_open:
                    self._ser.close()
                self._ser = None
                if not self._wait:
                    raise
                log_event(f"Cannot open {port}: {exc} — retrying")
                time.sleep(WAIT_POLL_SEC)

    def send(self, cmd: bytes) -> None:
        now = time.monotonic()
        with self._lock:
            if now - self._last_send < DEBOUNCE_SEC:
                return
            self._last_send = now
            if not self._ser or not self._ser.is_open:
                try:
                    self.open()
                except serial.SerialException as exc:
                    log_event(f"Serial open failed: {exc}")
                    return
            try:
                self._ser.write(cmd)
                self._ser.flush()
                log_event(f"Sent {cmd!r} to {self._ser.port}")
            except serial.SerialException as exc:
                log_event(f"Serial write failed: {exc}")
                self.close()
                try:
                    self.open()
                    if self._ser and self._ser.is_open:
                        self._ser.write(cmd)
                        self._ser.flush()
                        log_event(f"Sent {cmd!r} after reconnect")
                except serial.SerialException:
                    pass

    def close(self) -> None:
        if self._ser and self._ser.is_open:
            self._ser.close()
        self._ser = None


def check_accessibility_hint() -> None:
    """pynput logs to stderr when not trusted; warn in our log too."""
    log_event(
        "Starting hotkey listener. If shortcuts do nothing, enable "
        "'ESP32 Clock Hotkeys' in System Settings → Privacy → Accessibility, "
        "then run: open -a 'ESP32 Clock Hotkeys'"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", help="Serial port")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--list-ports", action="store_true")
    parser.add_argument(
        "--test-keys",
        action="store_true",
        help="Listen 15s and log any key (verify Accessibility)",
    )
    args = parser.parse_args()

    if args.list_ports:
        print("Configured:", read_config_port() or "(none)")
        for info in serial.tools.list_ports.comports():
            if info.vid == ESPRESSIF_VID or "usbmodem" in (info.device or ""):
                print(
                    f"  {info.device}  vid={info.vid:#06x}  "
                    f"{info.manufacturer or ''}  {info.description or ''}"
                )
        print("Auto-pick:", find_esp_port())
        return 0

    link = ClockSerial(args.port or "", args.baud, args.wait)
    try:
        port = link.open()
    except serial.SerialException as exc:
        print(f"Cannot open serial: {exc}", file=sys.stderr)
        return 1

    log_event(f"Serial OK on {port}")

    def on_next() -> None:
        link.send(b"n")

    def on_prev() -> None:
        link.send(b"p")

    hotkeys = {
        "<cmd>+<shift>+<right>": on_next,
        "<cmd>+<shift>+<left>": on_prev,
        "<cmd>+<shift>+]": on_next,
        "<cmd>+<shift>+[": on_prev,
    }

    if args.test_keys:
        log_event("TEST MODE: press Cmd+Shift+arrows (15 seconds)")
        pressed: list[str] = []

        def on_press(key):
            try:
                pressed.append(str(key))
            except Exception:
                pressed.append("?")
            log_event(f"Key pressed: {key}")

        with keyboard.Listener(on_press=on_press) as listener:
            time.sleep(15)
            listener.stop()
        log_event(f"Test done, saw {len(pressed)} key events")
        return 0 if pressed else 1

    check_accessibility_hint()

    try:
        with keyboard.GlobalHotKeys(hotkeys) as hk:
            log_event("GlobalHotKeys active (Cmd+Shift+Left/Right)")
            hk.join()
    except KeyboardInterrupt:
        pass
    finally:
        link.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
