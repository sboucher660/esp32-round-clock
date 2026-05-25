#!/usr/bin/env python3
"""Extract 240×240 circular doc shots from phone photos.

Keeps only the round display (transparent outside the circle). Works with
light e-ink panels, black OLED-style screens, and boot splash.

  .venv/bin/python scripts/process_device_photos.py
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "images"
SRC_DIR = ROOT / "assets" / "doc-photos"
OUT_SIZE = 240
COARSE_SKEW_LIMIT = 12.0

CURSOR_DIR = Path(
    "/Users/seb/Library/Application Support/Cursor/User/workspaceStorage/empty-window/images"
)

DEFAULT_INPUTS: dict[str, Path] = {
    "clock.png": SRC_DIR / "clock-source.png",
    "weather.png": SRC_DIR / "weather-source.png",
    "spotify.png": SRC_DIR / "spotify-source.png",
    "network.png": SRC_DIR / "network-source.png",
    "notification-alert.png": SRC_DIR / "notification-source.png",
    "boot-splash.png": SRC_DIR / "boot-splash-source.png",
}

# Latest Cursor chat uploads
CURSOR_SOURCES: dict[str, Path] = {
    "clock.png": CURSOR_DIR
    / "A466AC0B-ED26-41A3-92CB-1E817D4A59E3-501e4a15-1dd7-4794-8378-80862a0e62ef.png",
    "weather.png": CURSOR_DIR
    / "6619233E-EDF3-4B86-8C43-E69441B8D98F-69e6fdff-7d33-40fd-bfcb-2bc2added769.png",
    "spotify.png": CURSOR_DIR
    / "12688796-A56E-4998-853E-ADBAF9D8F286-b92285da-c596-4472-a05f-8bbbf5c35d66.png",
    "network.png": CURSOR_DIR
    / "0288E823-ABBA-444E-AE02-A50777C66E75-dbfe81e6-61ba-44f9-ac36-bb42d8f29cf8.png",
    "notification-alert.png": CURSOR_DIR
    / "DF224BE5-3B5B-4BAA-A6BD-DBFB5A49A46E-0146f87d-81cf-4733-8fdb-5a4e502fbb5d.png",
    "boot-splash.png": CURSOR_DIR
    / "A27721C5-2837-4232-93AE-C726D8CAD42F-438ba501-8876-4914-9794-64dac4354b61.png",
}


def light_panel_mask(bgr: np.ndarray) -> np.ndarray:
    """E-ink / light-gray active display (not black OLED)."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    cyan = cv2.inRange(hsv, (78, 20, 85), (115, 255, 255))
    light_gray = cv2.inRange(hsv, (0, 0, 95), (180, 70, 240))
    mask = cv2.bitwise_or(cyan, light_gray)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((17, 17), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
    return mask


def dark_panel_mask(bgr: np.ndarray) -> np.ndarray:
    """Black OLED active display."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    dark = (gray < 58).astype(np.uint8) * 255
    dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, np.ones((31, 31), np.uint8))
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    return dark


def panel_mask(bgr: np.ndarray) -> np.ndarray:
    return cv2.bitwise_or(light_panel_mask(bgr), dark_panel_mask(bgr))


def largest_contour(mask: np.ndarray) -> np.ndarray | None:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    c = max(contours, key=cv2.contourArea)
    if cv2.contourArea(c) < 800:
        return None
    return c


def _circle_from_contour(contour: np.ndarray, trim: float) -> tuple[int, int, int]:
    (cx, cy), radius = cv2.minEnclosingCircle(contour)
    return int(cx), int(cy), max(10, int(radius * trim))


def detect_circle(bgr: np.ndarray) -> tuple[int, int, int]:
    h, w = bgr.shape[:2]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    min_area = (min(h, w) * 0.28) ** 2

    # Light e-ink panel first (avoid mistaking outer black bezel for the screen)
    light_c = largest_contour(light_panel_mask(bgr))
    if light_c is not None and cv2.contourArea(light_c) > min_area * 0.45:
        return _circle_from_contour(light_c, 0.88)

    dark_c = largest_contour(dark_panel_mask(bgr))
    if dark_c is not None and cv2.contourArea(dark_c) > min_area:
        cx, cy, r = _circle_from_contour(dark_c, 0.90)
        roi = gray[max(0, cy - r) : cy + r, max(0, cx - r) : cx + r]
        if roi.size and float(np.median(roi)) < 70:
            return cx, cy, r

    gray_blur = cv2.GaussianBlur(gray, (7, 7), 0)
    circles = cv2.HoughCircles(
        gray_blur,
        cv2.HOUGH_GRADIENT,
        dp=1.15,
        minDist=min(h, w) // 2,
        param1=100,
        param2=34,
        minRadius=int(min(h, w) * 0.22),
        maxRadius=int(min(h, w) * 0.48),
    )
    if circles is not None:
        best: tuple[int, int, int] | None = None
        best_score = 1e9
        for c in circles[0]:
            cx, cy, r = float(c[0]), float(c[1]), float(c[2])
            dist = (cx - w / 2) ** 2 + (cy - h / 2) ** 2
            score = dist + abs(r - min(h, w) * 0.35) * 8
            if score < best_score:
                best_score = score
                best = (int(cx), int(cy), int(r * 0.90))
        if best is not None:
            return best

    return w // 2, h // 2, int(min(h, w) * 0.42)


def text_mask(bgr: np.ndarray, panel: np.ndarray, dark_ui: bool) -> np.ndarray:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    thresh = 120 if dark_ui else 175
    _, bright = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY)
    tm = cv2.bitwise_and(bright, panel)
    return cv2.morphologyEx(tm, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))


def is_dark_panel(bgr: np.ndarray, cx: int, cy: int, r: int) -> bool:
    patch = bgr[max(0, cy - r) : cy + r, max(0, cx - r) : cx + r]
    if patch.size == 0:
        return False
    return float(np.median(patch)) < 42


def skew_detection_mask(text: np.ndarray) -> np.ndarray:
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


def measure_skew(bgr: np.ndarray, dark_ui: bool) -> float | None:
    panel = panel_mask(bgr)
    text = skew_detection_mask(text_mask(bgr, panel, dark_ui))
    if text.sum() < 300:
        return None
    return hough_skew_angle(text)


def rotate_bgr(bgr: np.ndarray, center: tuple[float, float], angle: float) -> np.ndarray:
    if abs(angle) < 0.15:
        return bgr
    h, w = bgr.shape[:2]
    m = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(bgr, m, (w, h), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)


def find_straighten_angle(bgr: np.ndarray, center: tuple[float, float], dark_ui: bool) -> float:
    if panel_mask(bgr).sum() < 400:
        return 0.0
    initial = measure_skew(bgr, dark_ui)
    best_angle = 0.0
    best_residual = abs(initial) if initial is not None else 90.0

    for angle in np.linspace(-COARSE_SKEW_LIMIT, COARSE_SKEW_LIMIT, 161):
        rotated = rotate_bgr(bgr, center, float(angle))
        ha = measure_skew(rotated, dark_ui)
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


def apply_circle_alpha(bgra: np.ndarray, rcx: int, rcy: int, rr: int) -> np.ndarray:
    mask = np.zeros((OUT_SIZE, OUT_SIZE), dtype=np.uint8)
    cv2.circle(mask, (rcx, rcy), rr, 255, -1)
    mask = cv2.GaussianBlur(mask, (5, 5), 0)
    out = bgra.copy()
    out[:, :, 3] = cv2.min(out[:, :, 3], mask)
    return out


def extract_display(bgr: np.ndarray) -> np.ndarray:
    cx, cy, r = detect_circle(bgr)
    dark_ui = is_dark_panel(bgr, cx, cy, r)

    # Tight square crop — trim bezel (more on light e-ink panels)
    trim = 0.96 if dark_ui else 0.82
    r_crop = max(10, int(r * trim))
    h, w = bgr.shape[:2]
    x1, x2 = max(0, cx - r_crop), min(w, cx + r_crop)
    y1, y2 = max(0, cy - r_crop), min(h, cy + r_crop)
    patch = bgr[y1:y2, x1:x2].copy()

    center = (patch.shape[1] / 2, patch.shape[0] / 2)
    angle = find_straighten_angle(patch, center, dark_ui)
    if abs(angle) >= 0.15:
        patch = rotate_bgr(patch, center, angle)

    for _ in range(3):
        ha = measure_skew(patch, dark_ui)
        if ha is None or abs(ha) < 0.4:
            break
        center = (patch.shape[1] / 2, patch.shape[0] / 2)
        patch = rotate_bgr(patch, center, ha)

    patch = cv2.resize(patch, (OUT_SIZE, OUT_SIZE), interpolation=cv2.INTER_LANCZOS4)

    # Re-fit circle on final frame for a clean mask
    cx2, cy2, r2 = detect_circle(patch)
    trim2 = 0.96 if is_dark_panel(patch, cx2, cy2, r2) else 0.90
    r2 = max(10, min(int(r2 * trim2), OUT_SIZE // 2 - 2))

    bgra = cv2.cvtColor(patch, cv2.COLOR_BGR2BGRA)
    return apply_circle_alpha(bgra, cx2, cy2, r2)


def resolve_source(out_name: str) -> Path:
    local = DEFAULT_INPUTS[out_name]
    cursor = CURSOR_SOURCES.get(out_name)
    if cursor and cursor.is_file():
        SRC_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(cursor, local)
        return local
    if local.is_file():
        return local
    if cursor:
        return cursor
    return local


def process_file(src: Path, dest: Path) -> None:
    bgr = cv2.imread(str(src))
    if bgr is None:
        raise RuntimeError(f"Could not read {src}")
    out = extract_display(bgr)
    dest.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(dest), out, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    print(f"{src.name} → {dest}  (circular crop, transparent outside)")


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
            print(f"Skip {out_name}: missing {src}", file=sys.stderr)
            continue
        process_file(src, OUT / out_name)

    print(f"\nSaved to {OUT}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
