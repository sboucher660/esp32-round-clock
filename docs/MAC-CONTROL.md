# Mac page / rotation hotkeys (USB)

## How it works

| Piece | Location |
|--------|-----------|
| **USB daemon** (serial at login) | `~/Library/LaunchAgents/com.esp32-round-clock.usb-daemon.plist` |
| **Hotkeys** (global shortcuts) | `~/Applications/ESP32 Clock.app` + `com.esp32-round-clock.hotkeys.plist` |
| **Scripts + venv** | `~/Library/Application Support/esp32-round-clock/` |
| **Install** | `./scripts/install_usb_daemon.sh` |

No Karabiner or Shortcuts setup required. One install registers:

| Shortcut | Action |
|----------|--------|
| ⌘⇧→ | Next page |
| ⌘⇧← | Previous page |
| ⌘⇧↑ | Rotate display right |
| ⌘⇧↓ | Rotate display left |

The USB daemon keeps serial **open** so each keypress is instant (~0.1s). The hotkey app sends commands over a local Unix socket.

Live Mac notifications (15s alert overlay) use Wi-Fi, not USB. See [NOTIFICATIONS.md](NOTIFICATIONS.md).

## Install

```bash
cd ~/Documents/esp32-round-clock
./scripts/install_usb_daemon.sh
```

Then **once per Mac**:

1. **System Settings → Privacy & Security → Accessibility**
2. Enable **ESP32 Clock**
3. Run: `open -a 'ESP32 Clock'`

Test keys (15s log):

```bash
~/Library/Application\ Support/esp32-round-clock/.venv/bin/python3 \
  ~/Library/Application\ Support/esp32-round-clock/hotkey_listener.py --test-keys
```

Check `~/Library/Application Support/esp32-round-clock/hotkey-events.log`.

## Manual commands (no hotkeys)

```bash
~/Library/Application\ Support/esp32-round-clock/send-page.sh next
~/Library/Application\ Support/esp32-round-clock/send-page.sh prev
~/Library/Application\ Support/esp32-round-clock/send-rotate.sh right
~/Library/Application\ Support/esp32-round-clock/send-rotate.sh left
```

## Before `pio upload`

USB is exclusive — stop services first:

```bash
./scripts/stop-hotkeys.sh
pio run -e esp32c3_round -t upload
./scripts/install_usb_daemon.sh
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Hotkey does nothing | Accessibility ON for **ESP32 Clock**; `open -a 'ESP32 Clock'` |
| Page works in Terminal, not hotkeys | Same as above; check `hotkey-events.log` |
| Upload port busy | `./scripts/stop-hotkeys.sh` |
| Daemon stale | `send-page.sh --restart-daemon next` |

## Optional: Karabiner / Shortcuts

If Accessibility is blocked on a managed Mac, use [SHORTCUTS-SETUP.md](../scripts/SHORTCUTS-SETUP.md) or import `scripts/karabiner-esp32-clock.json` in Karabiner-Elements.
