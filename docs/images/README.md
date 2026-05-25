# Documentation screenshots

PNG previews of each screen (240×240, e-ink palette). Shown in the [README](../../README.md) and docs.

## Regenerate

```bash
.venv/bin/python scripts/render_doc_screenshots.py
```

Uses your `assets/apple_logo.png` on the boot splash frame. Layout matches firmware typography and colors; replace any file here with a **photo of your clock** if you prefer real device shots (keep the same filenames).

| File | Screen |
|------|--------|
| `boot-splash.png` | Boot logo |
| `clock.png` | Clock |
| `weather.png` | Weather |
| `spotify.png` | Spotify |
| `network.png` | Network |
| `notification-alert.png` | Mac notification overlay |
