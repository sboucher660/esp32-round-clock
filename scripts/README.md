# Scripts

## Mac USB control + hotkeys (current)

| Script | Purpose |
|--------|---------|
| `install_usb_daemon.sh` | **Main install** — USB daemon + **ESP32 Clock.app** hotkeys (no Karabiner) |
| `stop-hotkeys.sh` | Free USB port (stop daemon + hotkeys before `pio upload`) |
| `cleanup_mac_install.sh` | Remove old helpers before reinstall |
| `hotkey_listener.py` | Global ⌘⇧ arrow keys → USB daemon |
| `send-page.sh` / `send-rotate.sh` | Shell wrappers |
| `send_page.py` / `usb_daemon.py` / `esp_port.py` | Python backend |
| `com.esp32-round-clock.usb-daemon.plist` | USB LaunchAgent template |
| `com.esp32-round-clock.hotkeys.plist` | Hotkey app LaunchAgent template |
| `open-accessibility-binary.sh` | Reveal app for Accessibility settings |

Installed copy:

`~/Library/Application Support/esp32-round-clock/`

Hotkey app:

`~/Applications/ESP32 Clock.app`

## Notifications (Wi-Fi)

| Script | Purpose |
|--------|---------|
| `install_notification_forward.sh` | Mac → clock alerts |
| `notification_forward.py` | POST `/notify` |
| `forward-notification.sh` | Apple Shortcuts hook |

## Firmware / assets

| Script | Purpose |
|--------|---------|
| `spotify_get_refresh_token.py` | Spotify OAuth → `secrets.h` |
| `png_to_logo_h.py` | Boot splash → `include/apple_logo.h` |
| `process_device_photos.py` | README screenshots from phone photos |
| `render_doc_screenshots.py` | Synthetic screenshot fallback |

## Optional fallbacks

| Script | Notes |
|--------|-------|
| `karabiner-esp32-clock.json` | Karabiner rules if hotkey app is blocked |
| `karabiner-*.zsh` | Karabiner `shell_command` targets |
| `install_karabiner_setup.sh` | Karabiner-only install (no hotkey app) |
| `SHORTCUTS-SETUP.md` | Apple Shortcuts manual setup |
| `mac_page_control.py` | Legacy listener (own serial port) |
| `install_mac_page_daemon.sh` | Redirects to `install_usb_daemon.sh` |
