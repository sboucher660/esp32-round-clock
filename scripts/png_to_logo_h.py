#!/usr/bin/env python3
"""Convert your boot splash PNG/JPG to TFT_eSPI RGB565 header (include/apple_logo.h).

The logo artwork lives in assets/ (e.g. apple_logo.png — user-provided image).
Output is a full round-display frame (240×240): e-ink paper background with the
logo scaled and centered — no visible square patch.

Usage:
  .venv/bin/python scripts/png_to_logo_h.py assets/apple_logo.png
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


def fit_logo_on_canvas(src: Image.Image, size: int, max_scale: float) -> tuple[Image.Image, Image.Image]:
    """Full size×size frame filled with e-ink paper; logo centered, aspect preserved."""
    paper = rgb565_to_rgb(COL_EINK_PAPER)
    canvas = Image.new("RGBA", (size, size), paper + (255,))
    mask = Image.new("L", (size, size), 0)

    logo = src.convert("RGBA")
    w, h = logo.size
    max_side = max(8, int(size * max_scale))
    scale = min(max_side / w, max_side / h)
    nw = max(1, int(w * scale))
    nh = max(1, int(h * scale))
    scaled = logo.resize((nw, nh), Image.Resampling.LANCZOS)

    ox = (size - nw) // 2
    oy = (size - nh) // 2
    canvas.paste(scaled, (ox, oy), scaled)
    mask.paste(scaled.split()[3], (ox, oy))
    return canvas.convert("RGB"), mask


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("image")
    parser.add_argument("--size", type=int, default=240, help="Output frame size (square, full display)")
    parser.add_argument(
        "--max-scale",
        type=float,
        default=0.68,
        help="Logo max fraction of frame (0.68 ≈ centered, not blown up)",
    )
    args = parser.parse_args()

    src = Path(args.image)
    if not src.exists():
        print(f"File not found: {src}")
        sys.exit(1)

    size = args.size
    img = Image.open(src)
    img, logo_mask = fit_logo_on_canvas(img, size, args.max_scale)

    w, h = img.size
    pixels = img.load()
    mask_px = logo_mask.load()
    data = []
    for y in range(h):
        for x in range(w):
            if mask_px[x, y] < 32:
                data.append(COL_EINK_PAPER)
            else:
                data.append(map_pixel(*pixels[x, y]))

    lines = [
        "#pragma once",
        "#include <pgmspace.h>",
        "",
        f"// Generated from {src.name} ({w}x{h} RGB565, e-ink palette, centered on paper)",
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
    print(f"Wrote {OUT} ({w}x{h}, max_scale={args.max_scale})")


if __name__ == "__main__":
    main()
