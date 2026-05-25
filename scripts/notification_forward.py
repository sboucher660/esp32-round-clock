#!/usr/bin/env python3
"""Forward Mac notifications to the ESP32 round clock (HTTP POST /notify)."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

APP_DIR = os.path.expanduser("~/Library/Application Support/esp32-round-clock")
HOST_FILE = os.path.join(APP_DIR, "clock-host.txt")
LOG_PATH = os.path.join(APP_DIR, "notification-forward.log")
MDNS_HOST = "esp32-clock.local"
HTTP_PORT = 8080
DEBOUNCE_SEC = 2.0

_last_key = ""
_last_at = 0.0

# log stream lines sometimes contain app + message (macOS version dependent)
_RE_APP = re.compile(r"(?i)(Teams|Outlook|Mail|Messages|FaceTime|Phone|Slack|Discord|WhatsApp)")
_RE_JSON = re.compile(r"\{.*\}")


def log(msg: str) -> None:
    os.makedirs(APP_DIR, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")


def read_hosts() -> list[str]:
    hosts: list[str] = []
    if os.path.isfile(HOST_FILE):
        with open(HOST_FILE, encoding="utf-8") as f:
            for line in f:
                h = line.strip()
                if h:
                    hosts.append(h)
    if MDNS_HOST not in hosts:
        hosts.append(MDNS_HOST)
    return hosts


def post_notify(app: str, title: str, body: str) -> bool:
    global _last_key, _last_at

    app = (app or "Notification").strip()[:19]
    title = (title or "").strip()[:43]
    body = (body or "").strip()[:79]

    key = f"{app}|{title}|{body}"
    now = time.monotonic()
    if key == _last_key and (now - _last_at) < DEBOUNCE_SEC:
        return True
    _last_key = key
    _last_at = now

    payload = json.dumps({"app": app, "title": title, "body": body}).encode("utf-8")
    for host in read_hosts():
        url = f"http://{host}:{HTTP_PORT}/notify"
        try:
            req = urllib.request.Request(
                url,
                data=payload,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    log(f"→ {host} {app}: {title}")
                    return True
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            log(f"fail {host}: {exc}")
    return False


def send_cli(app: str, title: str, body: str) -> int:
    if post_notify(app, title, body):
        print(f"Sent to clock: {app} — {title}")
        return 0
    print("Could not reach clock. Check Wi-Fi and clock-host.txt.", file=sys.stderr)
    return 1


def parse_log_line(line: str) -> tuple[str, str, str] | None:
    line = line.strip()
    if len(line) < 8:
        return None

    lower = line.lower()
    if "notification" not in lower and "usernoted" not in lower and "deliver" not in lower:
        return None

    app = "Notification"
    m = _RE_APP.search(line)
    if m:
        app = m.group(1)

    title = ""
    body = line
    if ":" in line:
        parts = line.split(":", 2)
        if len(parts) >= 2:
            title = parts[-1].strip()[:43]
            body = title

    if len(title) < 2 and len(body) < 4:
        return None

    return app, title or app, body


def stream_logs() -> None:
    predicate = (
        'subsystem == "com.apple.UserNotifications" '
        'OR process == "NotificationCenter" '
        'OR process == "usernotificationsd"'
    )
    cmd = ["log", "stream", "--style", "compact", "--predicate", predicate]
    log(f"start: {' '.join(cmd)}")

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )
    assert proc.stdout is not None

    for line in proc.stdout:
        parsed = parse_log_line(line)
        if parsed:
            post_notify(*parsed)


def main() -> int:
    parser = argparse.ArgumentParser(description="Forward Mac notifications to ESP32 clock")
    parser.add_argument("command", nargs="?", choices=["send", "watch", "test"], default="watch")
    parser.add_argument("--app", default="Test")
    parser.add_argument("--title", default="Hello")
    parser.add_argument("--body", default="From your Mac")
    args = parser.parse_args()

    if args.command == "send":
        return send_cli(args.app, args.title, args.body)

    if args.command == "test":
        return send_cli("Test", "Notification test", "If you see this, alerts work.")

    try:
        stream_logs()
    except KeyboardInterrupt:
        log("stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
