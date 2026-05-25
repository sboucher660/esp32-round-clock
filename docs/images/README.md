# Documentation screenshots

**240×240** crops from your phone photos (`assets/doc-photos/`).  
Circular display only — **transparent outside the dial** (no square matte in the PNG).

## Regenerate (recommended)

```bash
.venv/bin/python scripts/process_device_photos.py
```

Keeps real TFT fonts, spacing, and colours from the device.

## Optional: synthetic renders

```bash
.venv/bin/python scripts/render_doc_screenshots.py
```

Approximates firmware layout when you have no photos; will not match the camera shot pixel-for-pixel.

| File | Screen |
|------|--------|
| `clock.png` | Clock |
| `weather.png` | Weather |
| `spotify.png` | Spotify |
| `network.png` | Network |
| `notification-alert.png` | Mac notification overlay |
