#!/usr/bin/env python3
"""Capture real photos of the ESP32 round clock into docs/images/.

Point a webcam or iPhone Continuity Camera at the clock (fill the center of the
frame), then run this script. It cycles pages over USB and grabs one frame per
screen.

Usage:
  # List cameras (ffmpeg):
  ffmpeg -f avfoundation -list_devices true -i ""

  python3 scripts/capture_device_screenshots.py --camera 0
  python3 scripts/capture_device_screenshots.py --camera 1   # iPhone camera

  # After capture, optional crop tuning:
  python3 scripts/capture_device_screenshots.py --camera 0 --crop 0.42
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Install Pillow: .venv/bin/pip install pillow")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "images"
APP = Path.home() / "Library/Application Support/esp32-round-clock"
SEND = APP / "send_page.py"
VENV_PY = APP / ".venv/bin/python3"


def run_send(cmd: str) -> bool:
    py = VENV_PY if VENV_PY.is_file() else sys.executable
    script = SEND if SEND.is_file() else ROOT / "scripts" / "send_page.py"
    if not script.is_file():
        print(f"Missing {script}", file=sys.stderr)
        return False
    r = subprocess.run([str(py), str(script), cmd], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr or r.stdout, file=sys.stderr)
        return False
    print(r.stdout.strip())
    return True


def post_notify(host: str) -> None:
    url = f"http://{host}:8080/notify"
    body = json.dumps(
        {
            "app": "Teams",
            "title": "Documentation screenshot",
            "body": "Live notification test on the round clock",
        }
    ).encode()
    req = urllib.request.Request(
        url, data=body, method="POST", headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=2) as resp:
        print(f"notify → {host} ({resp.status})")


def read_clock_host() -> str | None:
    host_file = APP / "clock-host.txt"
    if host_file.is_file():
        for line in host_file.read_text().splitlines():
            h = line.strip()
            if h:
                return h
    return None


def capture_frame(camera: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "avfoundation",
        "-framerate",
        "30",
        "-i",
        camera,
        "-frames:v",
        "1",
        "-update",
        "1",
        "-y",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, timeout=60)


def crop_clock_face(img: Image.Image, frac: float) -> Image.Image:
    """Center square crop; frac = fraction of min(width,height) to keep."""
    w, h = img.size
    side = int(min(w, h) * frac)
    left = (w - side) // 2
    top = (h - side) // 2
    cropped = img.crop((left, top, left + side, top + side))
    return cropped.resize((240, 240), Image.Resampling.LANCZOS)


def grab(camera: str, name: str, crop_frac: float, settle: float) -> None:
    raw = OUT / f".{name}-raw.jpg"
    print(f"\n→ {name}: position clock in frame, capturing in {settle:.0f}s…")
    time.sleep(settle)
    capture_frame(camera, raw)
    img = Image.open(raw)
    img = crop_clock_face(img, crop_frac)
    out = OUT / f"{name}.png"
    img.save(out, optimize=True)
    raw.unlink(missing_ok=True)
    print(f"  saved {out}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture real clock photos into docs/images/")
    parser.add_argument(
        "--camera",
        default="0",
        help='ffmpeg avfoundation device index or name (e.g. "0", "1")',
    )
    parser.add_argument(
        "--crop",
        type=float,
        default=0.38,
        help="Center crop fraction of frame (smaller if clock is farther)",
    )
    parser.add_argument("--settle", type=float, default=3.0, help="Seconds before each shot")
    parser.add_argument("--skip-boot", action="store_true", help="Skip boot (needs manual reset)")
    parser.add_argument("--skip-notify", action="store_true")
    args = parser.parse_args()

    if not shutil_which("ffmpeg"):
        print("ffmpeg required (brew install ffmpeg)", file=sys.stderr)
        return 1

    print("=" * 60)
    print("Point the camera at the ROUND DISPLAY (center of frame).")
    print("Keep the clock still; USB will cycle pages automatically.")
    print("=" * 60)

    if not args.skip_boot:
        print("\nBoot splash: press RESET on the clock now, then wait…")
        time.sleep(2)
        grab(args.camera, "boot-splash", args.crop, args.settle)

    screens = [
        ("clock", None),
        ("weather", "next"),
        ("spotify", "next"),
        ("network", "next"),
    ]

    for name, cmd in screens:
        if cmd:
            if not run_send(cmd):
                return 1
            time.sleep(1.2)
        grab(args.camera, name, args.crop, args.settle)

    if not args.skip_notify:
        host = read_clock_host()
        if host:
            try:
                post_notify(host)
                time.sleep(0.5)
                grab(args.camera, "notification-alert", args.crop, max(args.settle, 4.0))
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                print(f"notify skipped ({exc}); capture alert manually after a test notify")
        else:
            print("No clock-host.txt — skip notification (or run test notify, then re-run with --skip-boot)")

    print("\nDone. Review docs/images/*.png and commit if they look good.")
    return 0


def shutil_which(cmd: str) -> str | None:
    from shutil import which

    return which(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
