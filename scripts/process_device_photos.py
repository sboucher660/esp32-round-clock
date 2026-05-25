#!/usr/bin/env python3
"""Extract level 240×240 doc shots from phone photos of the physical display.

Output is a circular PNG with transparent corners (no square matte around the dial).
Preserves on-device fonts, spacing, and colours from your photos.

  .venv/bin/python scripts/process_device_photos.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "images"
SRC_DIR = ROOT / "assets" / "doc-photos"
OUT_SIZE = 240
DISPLAY_RADIUS = 110
TEXT_THRESHOLD = 188
SKEW_ANGLE_LIMIT = 35.0
COARSE_SKEW_LIMIT = 12.0

DEFAULT_INPUTS: dict[str, Path] = {
    "clock.png": SRC_DIR / "clock-source.png",
    "weather.png": SRC_DIR / "weather-source.png",
    "spotify.png": SRC_DIR / "spotify-source.png",
    "network.png": SRC_DIR / "network-source.png",
    "notification-alert.png": SRC_DIR / "notification-source.png",
}

CURSOR_SOURCES: dict[str, Path] = {
    "clock.png": Path(
        "/Users/seb/Library/Application Support/Cursor/User/workspaceStorage/"
        "empty-window/images/84939662-F87F-450D-BBD2-4B3963C34C9E-1441374c-e6fd-4276-9c70-461d9010a285.png"
    ),
    "weather.png": Path(
        "/Users/seb/Library/Application Support/Cursor/User/workspaceStorage/"
        "empty-window/images/130A17E7-2487-4BBE-ACBB-CF759CB9423A-f8444e41-dca4-4ba9-b96b-7fe7fd4a89ee.png"
    ),
    "spotify.png": Path(
        "/Users/seb/Library/Application Support/Cursor/User/workspaceStorage/"
        "empty-window/images/8F6C81A8-BBF1-43FC-B1C4-32954E4EE996-94f8d59f-ed24-4546-97ad-fdc7e4f4b116.png"
    ),
    "network.png": Path(
        "/Users/seb/Library/Application Support/Cursor/User/workspaceStorage/"
        "empty-window/images/2FE6E3D3-A450-4350-BDB6-C2169408574E-0d89f41a-0370-4e2b-a26b-c5ac6b5bca56.png"
    ),
    "notification-alert.png": Path(
        "/Users/seb/Library/Application Support/Cursor/User/workspaceStorage/"
        "empty-window/images/58AC6115-F2C9-499F-9C02-489D8BC93144-2d957e07-8239-4bf1-b36b-acb48eb8ccad.png"
    ),
}


def order_quad(pts: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).reshape(-1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def display_mask(bgr: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (78, 25, 90), (115, 255, 255))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((21, 21), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    return mask


def largest_contour(mask: np.ndarray) -> np.ndarray | None:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    c = max(contours, key=cv2.contourArea)
    if cv2.contourArea(c) < 500:
        return None
    return c


def warp_display_frontal(bgr: np.ndarray) -> np.ndarray:
    mask = display_mask(bgr)
    contour = largest_contour(mask)
    if contour is None:
        return bgr

    rect = cv2.minAreaRect(contour)
    box = order_quad(cv2.boxPoints(rect))
    side = int(max(rect[1]) * 1.05)
    side = max(side, 140)
    dst = np.array([[0, 0], [side - 1, 0], [side - 1, side - 1], [0, side - 1]], dtype=np.float32)
    m = cv2.getPerspectiveTransform(box, dst)
    return cv2.warpPerspective(bgr, m, (side, side), flags=cv2.INTER_LANCZOS4)


def find_display_circle(bgr: np.ndarray) -> tuple[int, int, int]:
    mask = display_mask(bgr)
    contour = largest_contour(mask)
    if contour is not None:
        (cx, cy), radius = cv2.minEnclosingCircle(contour)
        return int(cx), int(cy), int(radius * 0.96)

    h, w = bgr.shape[:2]
    return w // 2, h // 2, int(min(h, w) * 0.46)


def text_mask(bgr: np.ndarray, panel_mask: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    _, bright = cv2.threshold(gray, TEXT_THRESHOLD, 255, cv2.THRESH_BINARY)
    tm = cv2.bitwise_and(bright, panel_mask)
    return cv2.morphologyEx(tm, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))


def skew_detection_mask(text: np.ndarray) -> np.ndarray:
    """Ignore page dots and top bezel for angle detection."""
    h, w = text.shape
    m = text.copy()
    m[int(h * 0.82) :, :] = 0
    m[: int(h * 0.06), :] = 0
    return m


def hough_skew_angle(mask: np.ndarray) -> float | None:
    edges = cv2.Canny(mask, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 18, minLineLength=22, maxLineGap=12)
    if lines is None:
        return None

    angles: list[float] = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        dx, dy = x2 - x1, y2 - y1
        if abs(dx) < 12:
            continue
        ang = float(np.degrees(np.arctan2(dy, dx)))
        while ang > 45:
            ang -= 90.0
        while ang < -45:
            ang += 90.0
        if abs(ang) <= 25:
            angles.append(ang)

    if not angles:
        return None
    return float(np.median(angles))


def measure_skew_on_bgr(bgr: np.ndarray) -> float | None:
    panel = display_mask(bgr)
    text = skew_detection_mask(text_mask(bgr, panel))
    if text.sum() < 300:
        return None
    return hough_skew_angle(text)


def find_straighten_angle(
    bgr: np.ndarray,
    center: tuple[float, float],
    limit: float = SKEW_ANGLE_LIMIT,
    steps: int = 161,
) -> float:
    """Pick rotation that minimizes |hough skew| on the rotated frame."""
    if display_mask(bgr).sum() < 400:
        return 0.0

    initial = measure_skew_on_bgr(bgr)
    best_angle = 0.0
    best_residual = abs(initial) if initial is not None else 90.0

    for angle in np.linspace(-limit, limit, steps):
        rotated = rotate_bgr(bgr, center, float(angle))
        ha = measure_skew_on_bgr(rotated)
        if ha is None:
            continue
        residual = abs(ha)
        if residual < best_residual - 0.05 or (
            residual <= best_residual + 0.05 and abs(float(angle)) < abs(best_angle)
        ):
            best_residual = residual
            best_angle = float(angle)

    if best_residual > 1.0:
        return 0.0
    return best_angle


def rotate_bgr(bgr: np.ndarray, center: tuple[float, float], angle: float) -> np.ndarray:
    if abs(angle) < 0.15:
        return bgr
    h, w = bgr.shape[:2]
    m = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(bgr, m, (w, h), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)


def apply_circle_alpha(bgra: np.ndarray, rcx: int, rcy: int, rr: int) -> np.ndarray:
    mask = np.zeros((OUT_SIZE, OUT_SIZE), dtype=np.uint8)
    cv2.circle(mask, (rcx, rcy), rr, 255, -1)
    mask = cv2.GaussianBlur(mask, (5, 5), 0)
    out = bgra.copy()
    out[:, :, 3] = cv2.min(out[:, :, 3], mask)
    return out


def extract_display(bgr: np.ndarray, out_size: int = OUT_SIZE) -> np.ndarray:
    bgr = warp_display_frontal(bgr)

    cx, cy, r = find_display_circle(bgr)
    h, w = bgr.shape[:2]
    x1, x2 = max(0, cx - r), min(w, cx + r)
    y1, y2 = max(0, cy - r), min(h, cy + r)
    patch = bgr[y1:y2, x1:x2].copy()
    patch = cv2.resize(patch, (out_size, out_size), interpolation=cv2.INTER_LANCZOS4)

    center = (out_size / 2, out_size / 2)
    angle = find_straighten_angle(patch, center, limit=COARSE_SKEW_LIMIT, steps=161)
    if abs(angle) >= 0.15:
        patch = rotate_bgr(patch, center, angle)

    # Refine: rotate by remaining line tilt (fixes false ±mirror Hough minima)
    for _ in range(3):
        ha = measure_skew_on_bgr(patch)
        if ha is None or abs(ha) < 0.4:
            break
        patch = rotate_bgr(patch, center, ha)

    bgra = cv2.cvtColor(patch, cv2.COLOR_BGR2BGRA)
    return apply_circle_alpha(bgra, OUT_SIZE // 2, OUT_SIZE // 2, DISPLAY_RADIUS)


def resolve_source(out_name: str) -> Path:
    local = DEFAULT_INPUTS[out_name]
    if local.is_file():
        return local
    cursor = CURSOR_SOURCES[out_name]
    if cursor.is_file():
        SRC_DIR.mkdir(parents=True, exist_ok=True)
        import shutil

        shutil.copy2(cursor, local)
        return local
    return cursor


def process_file(src: Path, dest: Path) -> None:
    bgr = cv2.imread(str(src))
    if bgr is None:
        raise RuntimeError(f"Could not read {src}")
    out = extract_display(bgr)
    dest.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(dest), out, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    print(f"{src.name} → {dest}  (straightened, circular alpha)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("images", nargs="*", help="Optional image paths in default order")
    args = parser.parse_args()

    names = list(DEFAULT_INPUTS.keys())
    if args.images:
        sources = args.images[: len(names)]
        pairs = {names[i]: Path(sources[i]) for i in range(len(sources))}
    else:
        pairs = {name: resolve_source(name) for name in names}

    for out_name, src in pairs.items():
        if not src.is_file():
            print(f"Missing {src}", file=sys.stderr)
            return 1
        process_file(src, OUT / out_name)

    print(f"\nSaved to {OUT}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
