#!/usr/bin/env python3
"""Generate straight documentation screenshots (240×240, matches firmware layout).

Uses your real on-device text/content — not tilted phone photos. Run after UI changes:

  .venv/bin/python scripts/render_doc_screenshots.py
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("pip install pillow (or use project .venv)")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "images"

# RGB565 e-ink palette (matches firmware)
COL_PAPER = (198, 195, 188)
COL_INK = (227, 227, 227)
COL_GRAY = (156, 152, 147)
COL_LINE = (74, 73, 69)
SIZE = 240
CX, CY = 120, 120

# Layout constants from src/main.cpp
CLOCK_WEEKDAY_Y = 76
CLOCK_DATE_Y = 96
CLOCK_TIME_Y = 142


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
        if bold
        else [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    )
    for path in candidates:
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


def text_center(draw: ImageDraw.ImageDraw, text: str, y: int, font, fill) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((CX - w // 2, y - h // 2), text, font=font, fill=fill)
    return w


def text_width(text: str, font) -> int:
    bbox = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def draw_dots(draw: ImageDraw.ImageDraw, active: int, count: int = 4) -> None:
    spacing = 14
    x0 = CX - (count - 1) * spacing // 2
    for i in range(count):
        x = x0 + i * spacing
        r = 3 if i == active else 2
        fill = COL_INK if i == active else COL_GRAY
        outline = COL_GRAY if i != active else COL_INK
        draw.ellipse((x - r, 218 - r, x + r, 218 + r), fill=fill, outline=outline)


def draw_cloud(draw: ImageDraw.ImageDraw, cx: int, cy: int, scale: float = 1.0) -> None:
    r = int(14 * scale)
    draw.ellipse((cx - r, cy - 4, cx + r, cy + 10), fill=COL_GRAY)
    draw.ellipse((cx - r - 10, cy, cx - 2, cy + 14), fill=COL_GRAY)
    draw.ellipse((cx + 2, cy, cx + r + 10, cy + 14), fill=COL_GRAY)


def draw_spotify_bars(draw: ImageDraw.ImageDraw, cx: int, cy: int) -> None:
    heights = (10, 16, 12, 18, 14)
    x0 = cx - 24
    for i, h in enumerate(heights):
        bx = x0 + i * 12
        draw.rectangle((bx, cy - h, bx + 8, cy), fill=COL_INK)


def draw_wifi_bars(draw: ImageDraw.ImageDraw, cx: int, cy: int, filled: int, total: int = 4) -> None:
    spacing = 12
    x0 = cx - (total - 1) * spacing // 2
    for i in range(total):
        h = 8 + i * 6
        bx = x0 + i * spacing
        by = cy - h
        if i < filled:
            draw.rectangle((bx, by, bx + 8, cy), fill=COL_INK)
        else:
            draw.rectangle((bx, by, bx + 8, cy), outline=COL_GRAY, width=1)


def draw_clock_time(draw: ImageDraw.ImageDraw, time_s: str, sec_s: str) -> None:
    f_time = load_font(46, bold=True)
    f_sec = load_font(16)
    w_time = text_width(time_s, f_time)
    w_sec = text_width(sec_s, f_sec)
    total = w_time + w_sec
    x0 = CX - total // 2
    y = CLOCK_TIME_Y
    bbox_t = draw.textbbox((0, 0), time_s, font=f_time)
    th = bbox_t[3] - bbox_t[1]
    draw.text((x0, y - th // 2), time_s, font=f_time, fill=COL_INK)
    bbox_s = draw.textbbox((0, 0), sec_s, font=f_sec)
    sh = bbox_s[3] - bbox_s[1]
    draw.text((x0 + w_time, y - sh // 2 + 4), sec_s, font=f_sec, fill=COL_GRAY)


def render_clock() -> Image.Image:
    img, draw = new_screen()
    f2 = load_font(15)
    f4 = load_font(22, bold=True)

    text_center(draw, "Monday", CLOCK_WEEKDAY_Y, f2, COL_GRAY)
    text_center(draw, "25 May", CLOCK_DATE_Y, f4, COL_INK)
    draw_clock_time(draw, "13:37", ":04")
    draw_dots(draw, 0)
    return img


def render_weather() -> Image.Image:
    img, draw = new_screen()
    f2 = load_font(15)
    f7 = load_font(44, bold=True)

    draw_cloud(draw, CX, 82)
    text_center(draw, "15", 132, f7, COL_INK)
    text_center(draw, "Cloudy", 162, f2, COL_INK)
    text_center(draw, "10 km/h wind", 182, f2, COL_GRAY)
    draw_dots(draw, 1)
    return img


def render_spotify() -> Image.Image:
    img, draw = new_screen()
    f2 = load_font(15)
    f4 = load_font(18, bold=True)

    draw_spotify_bars(draw, CX, 58)
    text_center(draw, "spotify", 96, f2, COL_GRAY)
    text_center(draw, "Bela Lugosi's Dea", 128, f4, COL_INK)
    text_center(draw, "Bauhaus", 158, f2, COL_GRAY)
    text_center(draw, "playing", 198, f2, COL_INK)
    draw_dots(draw, 2)
    return img


def render_network() -> Image.Image:
    img, draw = new_screen()
    f2 = load_font(15)
    f4 = load_font(20, bold=True)

    draw_wifi_bars(draw, CX, 72, filled=3, total=4)
    text_center(draw, "-57 dBm", 108, f2, COL_GRAY)
    text_center(draw, "LAN", 118, f2, COL_GRAY)
    text_center(draw, "192.168.68.50", 140, f4, COL_INK)
    text_center(draw, "WAN", 168, f2, COL_GRAY)
    text_center(draw, "173.206.150.196", 190, f2, COL_INK)
    draw_dots(draw, 3)
    return img


def render_notification() -> Image.Image:
    img, draw = new_screen()
    f2 = load_font(15)
    f4 = load_font(18, bold=True)

    text_center(draw, "Alert", 78, f2, COL_INK)
    text_center(draw, "Teams", 104, f2, COL_GRAY)
    text_center(draw, "This is a very long", 138, f4, COL_INK)
    text_center(draw, "And here is an even longer m", 172, f2, COL_GRAY)
    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    screens = {
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
    raise SystemExit(main())
