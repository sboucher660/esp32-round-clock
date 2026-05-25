# Documentation screenshots

Real device photos (processed to 240×240: straight, cropped to the round display, background removed). Shown in the [README](../../README.md) and docs.

## Regenerate from your photos

1. Save phone photos anywhere, or use the paths baked into `process_device_photos.py`.
2. Run:

```bash
.venv/bin/pip install opencv-python-headless numpy pillow
.venv/bin/python scripts/process_device_photos.py
```

Optional: pass files in order `clock weather spotify network notification-alert`:

```bash
.venv/bin/python scripts/process_device_photos.py photo1.jpg photo2.jpg ...
```

| File | Screen |
|------|--------|
| `clock.png` | Clock |
| `weather.png` | Weather |
| `spotify.png` | Spotify |
| `network.png` | Network |
| `notification-alert.png` | Mac notification overlay |
