# Scripts

## Mac USB control + hotkeys

| Script | Purpose |
|--------|---------|
| `install_usb_daemon.sh` | **Install** — USB daemon + `ESP32 Clock.app` (⌘⇧ arrows) |
| `stop-hotkeys.sh` | Stop daemon + hotkeys before `pio upload` |
| `cleanup_mac_install.sh` | Reset Mac install before reinstall |
| `hotkey_listener.py` | Global hotkeys → USB daemon |
| `send-page.sh` / `send-rotate.sh` | Shell wrappers |
| `send_page.py` / `usb_daemon.py` / `esp_port.py` | Python backend |
| `open-accessibility-binary.sh` | Reveal app for Accessibility settings |
| `com.esp32-round-clock.*.plist` | LaunchAgent templates |

Installed:

- `~/Library/Application Support/esp32-round-clock/`
- `~/Applications/ESP32 Clock.app`

## Notifications (Wi-Fi)

| Script | Purpose |
|--------|---------|
| `install_notification_forward.sh` | Mac → clock alerts |
| `notification_forward.py` | POST `/notify` |
| `forward-notification.sh` | Shortcuts automation hook |

## Firmware / assets

| Script | Purpose |
|--------|---------|
| `spotify_get_refresh_token.py` | Spotify OAuth → `secrets.h` |
| `png_to_logo_h.py` | Boot splash → `include/apple_logo.h` |
| `process_device_photos.py` | README screenshots from phone photos |
| `render_doc_screenshots.py` | Synthetic screenshot fallback |
