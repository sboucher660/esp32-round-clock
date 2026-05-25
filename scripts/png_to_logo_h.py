#!/usr/bin/env python3
"""Convert a PNG/JPG boot splash to TFT_eSPI RGB565 header (include/apple_logo.h).

Usage:
  python3 scripts/png_to_logo_h.py path/to/image.png
  python3 scripts/png_to_logo_h.py path/to/image.jpg --size 240
"""

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Install Pillow in project venv: python3 -m venv .venv && .venv/bin/pip install pillow")
    sys.exit(1)

OUT = Path(__file__).resolve().parent.parent / "include" / "apple_logo.h"

COL_EINK_PAPER = 0x3186
COL_EINK_INK = 0xE71C
COL_EINK_GRAY = 0x9CD3
COL_EINK_LINE = 0x4A69


def luma(r, g, b):
    return (r * 299 + g * 587 + b * 114) // 1000


def blend_channel(a, b, t):
    return int(a + (b - a) * t)


def rgb565(r, g, b):
    # TFT_eSPI pushImage + setSwapBytes(true) expects high byte first in memory
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def rgb565_to_rgb(color):
    r = ((color >> 11) & 0x1F) * 255 // 31
    g = ((color >> 5) & 0x3F) * 255 // 63
    b = (color & 0x1F) * 255 // 31
    return r, g, b


def blend565(c0, c1, t):
    r0, g0, b0 = rgb565_to_rgb(c0)
    r1, g1, b1 = rgb565_to_rgb(c1)
    return rgb565(blend_channel(r0, r1, t), blend_channel(g0, g1, t), blend_channel(b0, b1, t))


def map_pixel(r, g, b):
    y = luma(r, g, b)
    if y < 24:
        return COL_EINK_PAPER
    if y > 210:
        return COL_EINK_INK
    t = (y - 24) / (210 - 24)
    if t < 0.45:
        return blend565(COL_EINK_PAPER, COL_EINK_GRAY, t / 0.45)
    if t < 0.75:
        return blend565(COL_EINK_GRAY, COL_EINK_INK, (t - 0.45) / 0.30)
    return COL_EINK_INK


def content_center(img, luma_threshold=36):
    gray = img.convert("L")
    pixels = gray.load()
    w, h = gray.size
    xs = []
    ys = []
    for y in range(h):
        for x in range(w):
            if pixels[x, y] > luma_threshold:
                xs.append(x)
                ys.append(y)
    if not xs:
        return w // 2, h // 2
    return sum(xs) // len(xs), sum(ys) // len(ys)


def crop_zoom_centered(img, size, zoom):
    w, h = img.size
    cx, cy = content_center(img)
    base_side = min(w, h)
    crop_side = max(32, int(base_side / zoom))
    left = cx - crop_side // 2
    top = cy - crop_side // 2
    left = max(0, min(left, w - crop_side))
    top = max(0, min(top, h - crop_side))
    cropped = img.crop((left, top, left + crop_side, top + crop_side))
    return cropped.resize((size, size), Image.Resampling.LANCZOS)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("image")
    parser.add_argument("--size", type=int, default=240, help="Output width/height (square)")
    parser.add_argument("--zoom", type=float, default=1.32, help=">1 zooms in on logo")
    args = parser.parse_args()

    src = Path(args.image)
    if not src.exists():
        print(f"File not found: {src}")
        sys.exit(1)

    size = args.size
    img = Image.open(src).convert("RGB")
    img = crop_zoom_centered(img, size, args.zoom)

    w, h = img.size
    pixels = img.load()
    data = [map_pixel(*pixels[x, y]) for y in range(h) for x in range(w)]

    lines = [
        "#pragma once",
        "#include <pgmspace.h>",
        "",
        f"// Generated from {src.name} ({w}x{h} RGB565, e-ink palette)",
        f"#define APPLE_LOGO_WIDTH {w}",
        f"#define APPLE_LOGO_HEIGHT {h}",
        "",
        f"const uint16_t apple_logo[{w * h}] PROGMEM = {{",
    ]

    for i in range(0, len(data), 12):
        chunk = ", ".join(f"0x{v:04X}" for v in data[i : i + 12])
        lines.append(f"  {chunk},")

    lines.append("};")
    lines.append("")

    OUT.write_text("\n".join(lines))
    print(f"Wrote {OUT} ({w}x{h})")


if __name__ == "__main__":
    main()
