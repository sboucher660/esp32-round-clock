# Scripts

## Mac USB control (current)

| Script | Purpose |
|--------|---------|
| `install_usb_daemon.sh` | **Main install** — LaunchAgent + copy scripts to Application Support |
| `stop-hotkeys.sh` | Free USB port (stop daemon before `pio upload`) |
| `cleanup_mac_install.sh` | Remove old hotkey app, bridge, Wi-Fi helpers |
| `send-page.sh` | Next/prev page (USB, instant) |
| `send-rotate.sh` | Rotate display 90° left/right |
| `send_page.py` | Python backend (called by shell wrappers) |
| `usb_daemon.py` | Persistent USB serial daemon |
| `esp_port.py` | Auto-detect `/dev/cu.usbmodem*` |
| `install_notification_forward.sh` | Mac → clock alerts (Wi-Fi; optional log watcher) |
| `notification_forward.py` | POST `/notify`; `test` / `send` / `watch` |
| `forward-notification.sh` | Shell hook for Apple Shortcuts automations |
| `karabiner-esp32-clock.json` | Karabiner complex modifications (import) |
| `karabiner-*.zsh` | Optional wrappers for Karabiner `shell_command` |
| `com.esp32-round-clock.usb-daemon.plist` | LaunchAgent template |

Installed copy lives at:

`~/Library/Application Support/esp32-round-clock/`

## Firmware / assets

| Script | Purpose |
|--------|---------|
| `spotify_get_refresh_token.py` | One-time Spotify OAuth → `secrets.h` lines |
| `png_to_logo_h.py` | Boot splash image → `include/apple_logo.h` |
| `render_doc_screenshots.py` | **Docs screenshots** — straight renders for README |
| `process_device_photos.py` | Optional: crop/deskew phone photos |

## Legacy (not needed for current setup)

| Script | Notes |
|--------|-------|
| `install_mac_page_daemon.sh` | Old Accessibility hotkey app |
| `uninstall_mac_page_daemon.sh` | Removes old LaunchAgent |
| `mac_page_control.py` | pynput global hotkeys |
| `install_karabiner_setup.sh` | Superseded by `install_usb_daemon.sh` |
| `SHORTCUTS-SETUP.md` | Apple Shortcuts fallback |
| `run_mac_page_control.sh` | Manual old hotkey runner |

Use `cleanup_mac_install.sh` if any of these were installed earlier.
