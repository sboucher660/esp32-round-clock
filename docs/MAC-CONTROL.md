# Mac page / rotation hotkeys (USB)

## How it works

| Piece | Location |
|--------|-----------|
| **USB daemon** | `~/Library/LaunchAgents/com.esp32-round-clock.usb-daemon.plist` |
| **Hotkeys** | `~/Applications/ESP32 Clock.app` + `com.esp32-round-clock.hotkeys.plist` |
| **Scripts** | `~/Library/Application Support/esp32-round-clock/` |

Install once:

```bash
cd ~/Documents/esp32-round-clock
./scripts/install_usb_daemon.sh
```

| Shortcut | Action |
|----------|--------|
| ⌘⇧→ | Next page |
| ⌘⇧← | Previous page |
| ⌘⇧↑ | Rotate display right |
| ⌘⇧↓ | Rotate display left |

The USB daemon keeps serial **open** for instant commands (~0.1s). The hotkey app sends commands over a local Unix socket.

Mac notification overlays use Wi-Fi — see [NOTIFICATIONS.md](NOTIFICATIONS.md).

## One-time: Accessibility

1. **System Settings → Privacy & Security → Accessibility**
2. Enable **ESP32 Clock**
3. `open -a 'ESP32 Clock'`

Test (15s key log):

```bash
~/Library/Application\ Support/esp32-round-clock/.venv/bin/python3 \
  ~/Library/Application\ Support/esp32-round-clock/hotkey_listener.py --test-keys
```

Log: `~/Library/Application Support/esp32-round-clock/hotkey-events.log`

## Shell commands

```bash
~/Library/Application\ Support/esp32-round-clock/send-page.sh next
~/Library/Application\ Support/esp32-round-clock/send-page.sh prev
~/Library/Application\ Support/esp32-round-clock/send-rotate.sh right
~/Library/Application\ Support/esp32-round-clock/send-rotate.sh left
```

## Before `pio upload`

```bash
./scripts/stop-hotkeys.sh
pio run -e esp32c3_round -t upload
./scripts/install_usb_daemon.sh
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Hotkey does nothing | Accessibility ON for **ESP32 Clock**; `open -a 'ESP32 Clock'` |
| Works in Terminal, not hotkeys | Check `hotkey-events.log`; `send-page.sh --restart-daemon next` |
| Upload port busy | `./scripts/stop-hotkeys.sh` |
