#!/usr/bin/env python3
"""Generate documentation screenshots (240×240 e-ink style) for docs/images/."""

from __future__ import annotations

import math
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("pip install pillow (or use project .venv)")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "images"
ASSETS = ROOT / "assets"

# RGB565 palette → RGB (matches firmware)
COL_PAPER = (198, 195, 188)
COL_INK = (227, 227, 227)
COL_GRAY = (156, 152, 147)
COL_LINE = (74, 73, 69)
SIZE = 240
CX, CY = 120, 120


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = (
        [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial Bold.ttf",
        ]
        if bold
        else [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial.ttf",
        ]
    )
    for path in names:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def new_screen() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (SIZE, SIZE), COL_PAPER)
    draw = ImageDraw.Draw(img)
    draw.ellipse((2, 2, 237, 237), outline=COL_LINE, width=1)
    draw.ellipse((3, 3, 236, 236), outline=COL_LINE, width=1)
    return img, draw


def text_center(draw: ImageDraw.ImageDraw, text: str, y: int, font, fill) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    draw.text((CX - w // 2, y - (bbox[3] - bbox[1]) // 2), text, font=font, fill=fill)


def draw_dots(draw: ImageDraw.ImageDraw, active: int, count: int = 4) -> None:
    spacing = 14
    x0 = CX - (count - 1) * spacing // 2
    for i in range(count):
        x = x0 + i * spacing
        r = 3 if i == active else 2
        fill = COL_INK if i == active else COL_GRAY
        draw.ellipse((x - r, 218 - r, x + r, 218 + r), fill=fill)


def render_clock() -> Image.Image:
    img, draw = new_screen()
    f2 = load_font(14)
    f4 = load_font(20, bold=True)
    f7 = load_font(52, bold=True)
    fsec = load_font(18, bold=True)

    text_center(draw, "Thursday", 76, f2, COL_INK)
    text_center(draw, "May 21", 96, f4, COL_INK)

    time = "2:45"
    bbox = draw.textbbox((0, 0), time, font=f7)
    tw = bbox[2] - bbox[0]
    draw.text((CX - tw // 2 - 8, 108), time, font=f7, fill=COL_INK)
    draw.text((CX + tw // 2 + 4, 118), "32", font=fsec, fill=COL_INK)
    draw.ellipse((CX + tw // 2 - 2, 125, CX + tw // 2 + 6, 133), fill=COL_INK)

    draw_dots(draw, 0)
    return img


def render_weather() -> Image.Image:
    img, draw = new_screen()
    f2 = load_font(14)
    f7 = load_font(48, bold=True)
    text_center(draw, "weather", 52, f2, COL_GRAY)
    text_center(draw, "18°", 132, f7, COL_INK)
    text_center(draw, "Partly cloudy", 162, f2, COL_INK)
    text_center(draw, "12 km/h wind", 182, f2, COL_GRAY)
    draw_dots(draw, 1)
    return img


def render_network() -> Image.Image:
    img, draw = new_screen()
    f2 = load_font(14)
    f4 = load_font(18, bold=True)
    text_center(draw, "network", 52, f2, COL_GRAY)
    text_center(draw, "-58 dBm", 92, f2, COL_INK)
    for i in range(4):
        h = 8 + i * 6
        draw.rectangle((98 + i * 12, 110 - h, 104 + i * 12, 110), fill=COL_INK)
    text_center(draw, "LAN", 118, f2, COL_GRAY)
    text_center(draw, "192.168.1.42", 140, f4, COL_INK)
    text_center(draw, "WAN", 168, f2, COL_GRAY)
    text_center(draw, "73.45.12.8", 190, f2, COL_INK)
    draw_dots(draw, 3)
    return img


def render_spotify() -> Image.Image:
    img, draw = new_screen()
    f2 = load_font(14)
    f4 = load_font(17, bold=True)
    text_center(draw, "spotify", 96, f2, COL_GRAY)
    text_center(draw, "Song Title That Scrolls", 128, f4, COL_INK)
    text_center(draw, "Artist Name", 158, f2, COL_GRAY)
    text_center(draw, "playing", 198, f2, COL_INK)
    for i in range(5):
        h = 10 + (i % 3) * 8
        draw.rectangle((88 + i * 10, 72 - h, 94 + i * 10, 72), fill=COL_INK)
    draw_dots(draw, 2)
    return img


def render_notification() -> Image.Image:
    img, draw = new_screen()
    f2 = load_font(14)
    f4 = load_font(17, bold=True)
    text_center(draw, "Alert", 78, f2, COL_INK)
    text_center(draw, "Teams", 104, f2, COL_GRAY)
    text_center(draw, "New message", 138, f4, COL_INK)
    text_center(draw, "Alex: standup in 5 min", 172, f2, COL_GRAY)
    return img


def render_boot() -> Image.Image:
    img, draw = new_screen()
    logo_path = ASSETS / "apple_logo.png"
    if logo_path.exists():
        logo = Image.open(logo_path).convert("RGBA")
        max_side = int(SIZE * 0.68)
        scale = min(max_side / logo.width, max_side / logo.height)
        nw, nh = int(logo.width * scale), int(logo.height * scale)
        logo = logo.resize((nw, nh), Image.Resampling.LANCZOS)
        ox, oy = CX - nw // 2, CY - nh // 2
        img.paste(logo, (ox, oy), logo)
    else:
        draw.ellipse((CX - 40, CY - 10, CX + 40, CY + 50), fill=COL_INK)
        draw.polygon([(CX - 12, CY - 30), (CX + 2, CY - 48), (CX + 2, CY - 26)], fill=COL_INK)
    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    screens = {
        "boot-splash": render_boot,
        "clock": render_clock,
        "weather": render_weather,
        "spotify": render_spotify,
        "network": render_network,
        "notification-alert": render_notification,
    }
    for name, fn in screens.items():
        path = OUT / f"{name}.png"
        fn().save(path, optimize=True)
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
