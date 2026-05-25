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
DISPLAY_RADIUS_FRAC = 0.46  # fraction of output side for active circle

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
    """Mask of the lit round panel (blue-gray e-ink background in photos)."""
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
    return w // 2, h // 2, int(min(h, w) * DISPLAY_RADIUS_FRAC)


def text_mask(bgr: np.ndarray, disp_mask: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    _, bright = cv2.threshold(gray, 175, 255, cv2.THRESH_BINARY)
    return cv2.bitwise_and(bright, disp_mask)


def rotation_search(mask: np.ndarray, center: tuple[float, float]) -> float:
    h, w = mask.shape[:2]
    best_angle = 0.0
    best_height = 1e9

    for angle in np.linspace(-30, 30, 121):
        m = cv2.getRotationMatrix2D(center, float(angle), 1.0)
        rot = cv2.warpAffine(mask, m, (w, h), flags=cv2.INTER_NEAREST, borderValue=0)
        pts = cv2.findNonZero(rot)
        if pts is None or len(pts) < 60:
            continue
        rect = cv2.minAreaRect(pts)
        height = min(rect[1])
        if height < best_height:
            best_height = height
            best_angle = float(angle)

    return best_angle


def rotate_about(bgr: np.ndarray, center: tuple[float, float], angle: float) -> np.ndarray:
    if abs(angle) < 0.25:
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


def final_deskew(bgra: np.ndarray, rcx: int, rcy: int, rr: int) -> np.ndarray:
    rgb = bgra[:, :, :3]
    panel = np.zeros((OUT_SIZE, OUT_SIZE), dtype=np.uint8)
    cv2.circle(panel, (rcx, rcy), rr, 255, -1)
    tmask = text_mask(rgb, panel)
    angle = rotation_search(tmask, (OUT_SIZE / 2, OUT_SIZE / 2))
    if abs(angle) < 0.2:
        return bgra
    m = cv2.getRotationMatrix2D((OUT_SIZE / 2, OUT_SIZE / 2), angle, 1.0)
    rotated = cv2.warpAffine(
        bgra,
        m,
        (OUT_SIZE, OUT_SIZE),
        flags=cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0),
    )
    return apply_circle_alpha(rotated, rcx, rcy, rr)


def extract_display(bgr: np.ndarray, out_size: int = OUT_SIZE) -> np.ndarray:
    bgr = warp_display_frontal(bgr)

    cx, cy, r = find_display_circle(bgr)
    center = (float(cx), float(cy))
    disp = display_mask(bgr)
    tmask = text_mask(bgr, disp)
    angle = rotation_search(tmask, center)
    bgr = rotate_about(bgr, center, angle)

    h, w = bgr.shape[:2]
    x1, x2 = max(0, cx - r), min(w, cx + r)
    y1, y2 = max(0, cy - r), min(h, cy + r)
    patch = bgr[y1:y2, x1:x2].copy()
    patch = cv2.resize(patch, (out_size, out_size), interpolation=cv2.INTER_LANCZOS4)

    mid = (out_size / 2, out_size / 2)
    fine = rotation_search(text_mask(patch, display_mask(patch)), mid)
    patch = rotate_about(patch, mid, fine)

    rcx, rcy, rr = find_display_circle(patch)
    # Trim outer bezel; keep only the lit panel
    rr = max(10, int(rr * 0.92))

    sharp = cv2.addWeighted(patch, 1.15, cv2.GaussianBlur(patch, (0, 0), 1.2), -0.15, 0)
    bgra = cv2.cvtColor(sharp, cv2.COLOR_BGR2BGRA)
    bgra = apply_circle_alpha(bgra, rcx, rcy, rr)
    return final_deskew(bgra, rcx, rcy, rr)


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
    print(f"{src.name} → {dest}  (circular, transparent outside)")


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
