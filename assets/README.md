# Boot splash image

The boot screen uses **your provided Apple logo artwork** — not a generated placeholder.

| File | Role |
|------|------|
| `apple_logo.png` / `apple_logo.jpg` | **Source image** (what you supplied) |
| `include/apple_logo.h` | RGB565 data for TFT_eSPI (built from that image, committed in repo) |

Firmware draws a **full 240×240** frame (e-ink paper + centered logo) on every boot — matches the round UI background.

## Replace the artwork

1. Put your new PNG or JPG here (e.g. overwrite `apple_logo.png`).
2. Regenerate the header and reflash:

```bash
.venv/bin/pip install pillow   # once, if needed
.venv/bin/python scripts/png_to_logo_h.py assets/apple_logo.png
pio run -e esp32c3_round -t upload
```

`scripts/png_to_logo_h.py` only **converts** your image to C — it does not create the logo design.
