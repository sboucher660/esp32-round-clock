# Boot logo image

Drop your boot splash image here (PNG or JPG), then run:

```bash
python3 -m venv .venv && .venv/bin/pip install pillow   # once
.venv/bin/python scripts/png_to_logo_h.py assets/apple_logo.jpg --size 240
pio run -t upload
```

- Full-screen 240×240 splash (center-cropped square from your image)
- Colors are mapped to the e-ink palette used on the clock screens
- Output: `include/apple_logo.h` (gitignored — generated locally)

You can also attach the image in Cursor chat and ask the agent to convert it for you.
