#!/usr/bin/env python3
"""Keep ESP32 USB serial open for instant page/rotate commands (unix socket IPC)."""

from __future__ import annotations

import atexit
import os
import signal
import socket
import subprocess
import sys
import threading
import time

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from esp_port import find_port  # noqa: E402

APP_DIR = os.path.expanduser("~/Library/Application Support/esp32-round-clock")
CONFIG = os.path.join(APP_DIR, "port.txt")
SOCK_PATH = os.path.join(APP_DIR, "usb.sock")
PID_PATH = os.path.join(APP_DIR, "usb-daemon.pid")
LOG_PATH = os.path.join(APP_DIR, "usb-daemon.log")

CMD_BYTES = {
    "next": b"n",
    "prev": b"p",
    "rotate-right": b">",
    "rotate-left": b"<",
    "n": b"n",
    "p": b"p",
    "r": b">",
    "l": b"<",
    ">": b">",
    "<": b"<",
}


def log(msg: str) -> None:
    os.makedirs(APP_DIR, exist_ok=True)
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n"
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line)


class SerialSession:
    def __init__(self, port: str) -> None:
        self.port = port
        self._fd: int | None = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._reader: threading.Thread | None = None

    def open(self) -> None:
        self.close()
        self._fd = os.open(self.port, os.O_RDWR | os.O_NONBLOCK)
        self._stop.clear()
        self._reader = threading.Thread(target=self._drain_rx, daemon=True)
        self._reader.start()
        log(f"opened {self.port}")

    def close(self) -> None:
        self._stop.set()
        if self._reader:
            self._reader.join(timeout=0.5)
            self._reader = None
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None

    def _drain_rx(self) -> None:
        assert self._fd is not None
        while not self._stop.is_set():
            try:
                data = os.read(self._fd, 256)
                if not data:
                    time.sleep(0.02)
            except BlockingIOError:
                time.sleep(0.02)
            except OSError:
                break

    def write(self, payload: bytes) -> None:
        with self._lock:
            if self._fd is None:
                self.open()
            assert self._fd is not None
            try:
                os.write(self._fd, payload)
            except OSError as exc:
                log(f"write failed: {exc}, reconnecting")
                self.open()
                os.write(self._fd, payload)


def run_daemon(port: str) -> None:
    session = SerialSession(port)

    try:
        os.unlink(SOCK_PATH)
    except OSError:
        pass

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(SOCK_PATH)
    os.chmod(SOCK_PATH, 0o600)
    server.listen(16)
    server.settimeout(1.0)

    with open(PID_PATH, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))

    def cleanup() -> None:
        session.close()
        server.close()
        for path in (PID_PATH, SOCK_PATH):
            try:
                os.unlink(path)
            except OSError:
                pass

    atexit.register(cleanup)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))

    try:
        session.open()
    except OSError as exc:
        log(f"cannot open {port}: {exc}")
        sys.exit(1)

    log(f"listening {SOCK_PATH}")

    while True:
        try:
            conn, _ = server.accept()
        except TimeoutError:
            continue
        with conn:
            conn.settimeout(2.0)
            try:
                msg = conn.recv(32).decode("utf-8", errors="ignore").strip()
                payload = CMD_BYTES.get(msg)
                if not payload:
                    conn.sendall(b"err unknown\n")
                    continue
                session.write(payload)
                conn.sendall(b"ok\n")
            except OSError as exc:
                log(f"client error: {exc}")
                conn.sendall(f"err {exc}\n".encode())


def daemon_running() -> bool:
    if not os.path.isfile(PID_PATH):
        return False
    try:
        with open(PID_PATH, encoding="utf-8") as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        return os.path.exists(SOCK_PATH)
    except (OSError, ValueError):
        return False


def stop_daemon() -> None:
    if not os.path.isfile(PID_PATH):
        return
    try:
        with open(PID_PATH, encoding="utf-8") as f:
            pid = int(f.read().strip())
        os.kill(pid, signal.SIGTERM)
    except (OSError, ValueError):
        pass
    for path in (PID_PATH, SOCK_PATH):
        try:
            os.unlink(path)
        except OSError:
            pass


def start_daemon(port: str | None = None) -> None:
    if daemon_running():
        return
    stop_daemon()
    port = port or find_port(config_path=CONFIG, save=True)
    if not port:
        raise RuntimeError("No ESP32 USB port (plug in data cable)")

    subprocess.Popen(
        [sys.executable, __file__, "--run", "--port", port],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        cwd=APP_DIR,
    )
    for _ in range(40):
        if os.path.exists(SOCK_PATH):
            return
        time.sleep(0.05)
    raise TimeoutError("USB daemon did not start")


def send_command(cmd: str, port: str | None = None) -> None:
    if not daemon_running():
        start_daemon(port)
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(0.5)
    client.connect(SOCK_PATH)
    client.sendall((cmd + "\n").encode())
    reply = client.recv(64).decode("utf-8", errors="ignore").strip()
    client.close()
    if not reply.startswith("ok"):
        raise RuntimeError(reply or "daemon error")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs="?", choices=list(CMD_BYTES.keys()))
    parser.add_argument("--port")
    parser.add_argument("--run", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--stop", action="store_true")
    args = parser.parse_args()

    if args.stop:
        stop_daemon()
        print("USB daemon stopped.")
        return 0

    if args.run:
        port = args.port or find_port(config_path=CONFIG, save=True)
        if not port:
            log("no port")
            return 1
        run_daemon(port)
        return 0

    if not args.command:
        parser.error("command required")
    port = find_port(args.port, config_path=CONFIG, save=True) if args.port else None
    send_command(args.command, port)
    print(f"Sent '{args.command}' via USB (daemon)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
