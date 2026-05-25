#!/usr/bin/env python3
"""Extract clean 240×240 circular display shots from phone photos."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "images"
OUT_SIZE = 240

# Cursor upload paths for this session (newest five device photos)
DEFAULT_INPUTS: dict[str, Path] = {
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


def find_display_circle(bgr: np.ndarray) -> tuple[int, int, int]:
    h, w = bgr.shape[:2]
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

    # Lit LCD (cyan / light blue)
    mask = cv2.inRange(hsv, (78, 25, 90), (115, 255, 255))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((21, 21), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        contour = max(contours, key=cv2.contourArea)
        (cx, cy), radius = cv2.minEnclosingCircle(contour)
        r = int(radius * 0.92)
        if r > min(h, w) * 0.12:
            return int(cx), int(cy), r

    gray = cv2.GaussianBlur(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), (9, 9), 2)
    circles = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=min(h, w) // 2,
        param1=100,
        param2=35,
        minRadius=int(min(h, w) * 0.14),
        maxRadius=int(min(h, w) * 0.46),
    )
    if circles is not None:
        c = max(circles[0], key=lambda x: x[2])
        return int(c[0]), int(c[1]), int(c[2] * 0.92)

    return w // 2, h // 2, int(min(h, w) * 0.32)


def display_mask(bgr: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (78, 25, 90), (115, 255, 255))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((21, 21), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    return mask


def warp_display_frontal(bgr: np.ndarray) -> np.ndarray:
    mask = display_mask(bgr)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return bgr

    contour = max(contours, key=cv2.contourArea)
    if cv2.contourArea(contour) < 500:
        return bgr

    rect = cv2.minAreaRect(contour)
    box = cv2.boxPoints(rect)
    box = np.array(box, dtype=np.float32)

    w, h = rect[1]
    side = int(max(w, h))
    side = max(side, 80)

    dst = np.array([[0, 0], [side - 1, 0], [side - 1, side - 1], [0, side - 1]], dtype=np.float32)
    order = np.argsort(box[:, 1])
    box_sorted = box[order]
    top = box_sorted[:2]
    bottom = box_sorted[2:]
    top = top[np.argsort(top[:, 0])]
    bottom = bottom[np.argsort(bottom[:, 0])]
    src = np.array([top[0], top[1], bottom[1], bottom[0]], dtype=np.float32)

    m = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(bgr, m, (side, side), flags=cv2.INTER_LANCZOS4)


def sample_edge_color(bgr: np.ndarray, cx: int, cy: int, r: int) -> np.ndarray:
    h, w = bgr.shape[:2]
    samples = []
    for deg in range(0, 360, 12):
        rad = np.deg2rad(deg)
        x = int(cx + np.cos(rad) * (r * 0.82))
        y = int(cy + np.sin(rad) * (r * 0.82))
        if 0 <= x < w and 0 <= y < h:
            samples.append(bgr[y, x])
    if samples:
        return np.median(samples, axis=0).astype(np.uint8)
    return np.array([176, 198, 210], dtype=np.uint8)


def deskew_by_ellipse(bgr: np.ndarray) -> np.ndarray:
    mask = display_mask(bgr)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return bgr
    contour = max(contours, key=cv2.contourArea)
    if len(contour) < 5:
        return bgr
    ellipse = cv2.fitEllipse(contour)
    angle = ellipse[2]
    if ellipse[1][0] < ellipse[1][1]:
        angle += 90.0
    if abs(angle) > 45:
        angle -= 90.0
    if abs(angle) < 0.5:
        return bgr
    h, w = bgr.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(bgr, m, (w, h), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)


def extract_display(bgr: np.ndarray, out_size: int = OUT_SIZE) -> np.ndarray:
    bgr = warp_display_frontal(bgr)
    bgr = deskew_by_ellipse(bgr)
    cx, cy, r = find_display_circle(bgr)
    h, w = bgr.shape[:2]
    x1, x2 = max(0, cx - r), min(w, cx + r)
    y1, y2 = max(0, cy - r), min(h, cy + r)
    patch = bgr[y1:y2, x1:x2].copy()
    patch = cv2.resize(patch, (out_size, out_size), interpolation=cv2.INTER_LANCZOS4)

    rcx, rcy, rr = find_display_circle(patch)
    rr = max(8, rr - 6)
    bg = sample_edge_color(patch, rcx, rcy, rr)

    mask = np.zeros((out_size, out_size), dtype=np.uint8)
    cv2.circle(mask, (rcx, rcy), rr, 255, -1)

    smooth = cv2.bilateralFilter(patch, 5, 60, 60)
    denoised = cv2.fastNlMeansDenoisingColored(smooth, None, 4, 4, 7, 15)
    bg_img = np.full_like(denoised, bg)
    mask3 = cv2.merge([mask, mask, mask]) / 255.0
    result = (denoised * mask3 + bg_img * (1.0 - mask3)).astype(np.uint8)

    # Square frame: corners match screen edge (no hub/bezel)
    result = np.where(mask3 > 0.5, result, bg_img).astype(np.uint8)
    return result


def process_file(src: Path, dest: Path) -> None:
    bgr = cv2.imread(str(src))
    if bgr is None:
        raise RuntimeError(f"Could not read {src}")
    out = extract_display(bgr)
    dest.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(dest), out, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    print(f"{src.name} → {dest}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("images", nargs="*", help="Optional: src:out pairs or files in order")
    args = parser.parse_args()

    if args.images:
        if len(args.images) % 2 == 0:
            pairs = dict(zip(args.images[0::2], args.images[1::2]))
        else:
            names = list(DEFAULT_INPUTS.keys())
            pairs = {names[i]: args.images[i] for i in range(min(len(names), len(args.images)))}
        for out_name, src in pairs.items():
            process_file(Path(src), OUT / out_name)
    else:
        for out_name, src in DEFAULT_INPUTS.items():
            if not src.is_file():
                print(f"Missing {src}", file=sys.stderr)
                return 1
            process_file(src, OUT / out_name)

    print(f"\nSaved to {OUT}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
