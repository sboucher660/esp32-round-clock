# Documentation screenshots

Straight **240×240** renders that match the on-device UI (e-ink palette, firmware layout).  
These are generated — not phone photos — so text stays level in the README.

## Regenerate

```bash
.venv/bin/python scripts/render_doc_screenshots.py
```

Content matches the author's clock (e.g. Monday 25 May, Teams alert test, Bauhaus track). Edit the strings in that script if your display differs.

## Optional: photos from the physical device

```bash
.venv/bin/python scripts/process_device_photos.py
```

Phone shots are harder to keep perfectly straight; prefer `render_doc_screenshots.py` for GitHub docs.

| File | Screen |
|------|--------|
| `clock.png` | Clock |
| `weather.png` | Weather |
| `spotify.png` | Spotify |
| `network.png` | Network |
| `notification-alert.png` | Mac notification overlay |
