# Install guide

ESP32-C3 round display clock: firmware + optional Mac USB hotkeys (Karabiner).

## Requirements

| Component | Install |
|-----------|---------|
| **PlatformIO** | `brew install platformio` |
| **Python 3** | macOS built-in or Homebrew |
| **Karabiner-Elements** | [karabiner-elements.pqrs.org](https://karabiner-elements.pqrs.org/) (Mac hotkeys only) |
| **Board** | ESP32-2424S012 family (1.28" round GC9A01, ESP32-C3) |

## 1. Clone and configure firmware

```bash
git clone git@github.com:sboucher660/esp32-round-clock.git
cd esp32-round-clock
cp include/secrets.h.example include/secrets.h
```

Edit `include/secrets.h`:

- `WIFI_SSID` / `WIFI_PASS`
- Optional: Spotify credentials (see [README](../README.md#spotify-optional-screen-3))

Edit `include/config.h` if needed:

- `TIMEZONE` — POSIX TZ string
- `WEATHER_LAT` / `WEATHER_LON`
- `DISPLAY_ROTATION` — default orientation (0–3)

### Optional boot splash (Apple logo)

```bash
python3 -m venv .venv
.venv/bin/pip install pillow
.venv/bin/python scripts/png_to_logo_h.py assets/apple_logo.jpg --size 240
```

Generates `include/apple_logo.h` (gitignored).

## 2. Build and flash

1. Disconnect Bluetooth headphones that expose a serial port.
2. Plug the board with a **data** USB-C cable.
3. Find the port:

```bash
pio device list
# e.g. /dev/cu.usbmodem11401
```

4. Flash:

```bash
pio run -e esp32c3_round -t upload
# or: pio run -e esp32c3_round -t upload --upload-port /dev/cu.usbmodemXXXX
```

If upload fails: hold **BOOT**, tap **RESET**, release **BOOT**, retry.

## 3. On-device use

- **BOOT button** (back): tap to cycle Clock → Weather → Spotify → Network.
- Do **not** hold BOOT (enters flash mode).

## 4. Mac USB hotkeys (optional)

Instant control over USB via a **LaunchAgent daemon**. Nothing installed in `$HOME` root — only:

- `~/Library/Application Support/esp32-round-clock/`
- `~/Library/LaunchAgents/com.esp32-round-clock.usb-daemon.plist`

### Install

```bash
./scripts/install_usb_daemon.sh
```

### Commands

```bash
~/Library/Application\ Support/esp32-round-clock/send-page.sh next
~/Library/Application\ Support/esp32-round-clock/send-page.sh prev
~/Library/Application\ Support/esp32-round-clock/send-rotate.sh right
~/Library/Application\ Support/esp32-round-clock/send-rotate.sh left
```

### Karabiner

Import `scripts/karabiner-esp32-clock.json` in **Karabiner-Elements → Complex Modifications**.

| Shortcut | Action |
|----------|--------|
| ⌘⇧→ | Next page |
| ⌘⇧← | Previous page |
| ⌘⇧↑ | Rotate right (90°) |
| ⌘⇧↓ | Rotate left (90°) |

Enable **Input Monitoring** for Karabiner in System Settings.

See [MAC-CONTROL.md](MAC-CONTROL.md) for troubleshooting.

### Before re-flashing firmware

```bash
./scripts/stop-hotkeys.sh
pio run -e esp32c3_round -t upload
./scripts/install_usb_daemon.sh
```

### Cleanup old installs

If you previously used the Accessibility hotkey app or Wi-Fi scripts:

```bash
./scripts/cleanup_mac_install.sh
./scripts/install_usb_daemon.sh
```

## 5. 3D printed case (optional)

See [case/README.md](../case/README.md). Print `case/stl/mini-mac-body.stl` and `case/stl/mini-mac-back.stl`.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Blank display | Try `DISPLAY_ROTATION` 0–3 in `config.h`, reflash |
| Wi-Fi failed | 2.4 GHz network, check `secrets.h` |
| Upload port busy | `./scripts/stop-hotkeys.sh` |
| Mac hotkey does nothing | Reboot clock; `send-page.sh --restart-daemon next`; check `usb-daemon.log` |
| Karabiner no effect | Input Monitoring on; rules enabled |
| Page works in Terminal, not Karabiner | Fix `shell_command` path to Application Support scripts |
