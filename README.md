# ESP32 Round Clock

Firmware and Mac helpers for the **ESP32-C3 1.28" round GC9A01** board (ESP32-2424S012 family, no touch).

## Features

| Screen | Content |
|--------|---------|
| **Clock** | NTP time, local timezone |
| **Weather** | Open-Meteo (no API key) |
| **Spotify** | Now playing (optional) |
| **Network** | Wi-Fi RSSI, LAN / public IP |

- **BOOT button (GPIO 9):** tap to change page (do not hold — flash mode)
- **Mac hotkeys (optional):** instant USB control via Karabiner + LaunchAgent daemon
- **Display rotation:** 90° steps, saved on device
- **3D case:** Mini Mac–style enclosure ([case/README.md](case/README.md))

## Quick start

**Full guide:** [docs/INSTALL.md](docs/INSTALL.md)

```bash
git clone git@github.com:sboucher660/esp32-round-clock.git
cd esp32-round-clock
cp include/secrets.h.example include/secrets.h
# edit secrets.h (Wi-Fi, optional Spotify)
pio run -e esp32c3_round -t upload
```

On the device: tap **BOOT** to cycle screens.

### Mac hotkeys (Karabiner)

```bash
./scripts/install_usb_daemon.sh
```

Import `scripts/karabiner-esp32-clock.json` in Karabiner. Default bindings:

| Shortcut | Action |
|----------|--------|
| ⌘⇧→ | Next page |
| ⌘⇧← | Previous page |
| ⌘⇧↑ | Rotate right |
| ⌘⇧↓ | Rotate left |

Details: [docs/MAC-CONTROL.md](docs/MAC-CONTROL.md) · [scripts/README.md](scripts/README.md)

## Configuration

| File | Purpose |
|------|---------|
| `include/secrets.h` | Wi-Fi, Spotify (from `secrets.h.example`) |
| `include/config.h` | Timezone, weather coordinates, GPIO, refresh intervals |

## Hardware

| Function | GPIO |
|----------|------|
| SPI SCLK | 6 |
| SPI MOSI | 7 |
| TFT DC | 2 |
| TFT CS | 10 |
| Backlight | 3 |
| Page button | 9 (BOOT, active LOW) |

Side tact switch on many boards is a **battery power key**, not usable for pages. See [docs/board-back-gpio.md](docs/board-back-gpio.md).

## Project layout

```
esp32-round-clock/
├── src/main.cpp          # Firmware
├── include/              # config.h, secrets template
├── scripts/              # Mac USB daemon, Karabiner, Spotify auth
├── case/                 # OpenSCAD + STL for 3D print
├── docs/                 # Install, Mac control, GPIO diagram
└── platformio.ini
```

## Spotify (optional)

1. [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) — redirect URI `http://127.0.0.1:8888/callback`
2. `python3 scripts/spotify_get_refresh_token.py`
3. Paste output into `secrets.h`, rebuild, flash

## License

Private repository — all rights reserved unless otherwise noted.
