# Mac page / rotation hotkeys (USB)

## How it works

| Piece | Location |
|--------|-----------|
| **LaunchAgent** (daemon at login) | `~/Library/LaunchAgents/com.esp32-round-clock.usb-daemon.plist` |
| **Daemon + scripts** | `~/Library/Application Support/esp32-round-clock/` |
| **Source / install** | `~/Documents/esp32-round-clock/scripts/` (git repo) |

Nothing is installed in `$HOME` root. This follows normal macOS app layout (like many CLI tools).

The daemon keeps USB serial **open** so each hotkey is instant (~0.1s). Karabiner runs the shell wrappers.

## Commands

```bash
~/Library/Application\ Support/esp32-round-clock/send-page.sh next
~/Library/Application\ Support/esp32-round-clock/send-page.sh prev
~/Library/Application\ Support/esp32-round-clock/send-rotate.sh right
~/Library/Application\ Support/esp32-round-clock/send-rotate.sh left
```

## Install / reinstall

```bash
cd ~/Documents/esp32-round-clock
./scripts/install_usb_daemon.sh
```

## Cleanup old installs (Wi‑Fi hotkeys, bridge, Accessibility app)

```bash
./scripts/cleanup_mac_install.sh
```

## Before `pio upload`

USB is exclusive — stop the daemon first:

```bash
./scripts/stop-hotkeys.sh
pio run -e esp32c3_round -t upload
./scripts/install_usb_daemon.sh
```

## Karabiner

Import `scripts/karabiner-esp32-clock.json` (Complex Modifications → Import) or add rules in the JSON editor:

| Shortcut | Command |
|----------|---------|
| ⌘⇧→ | `send-page.sh next` |
| ⌘⇧← | `send-page.sh prev` |
| ⌘⇧↑ | `send-rotate.sh r` |
| ⌘⇧↓ | `send-rotate.sh l` |

Example `shell_command`:

```text
/bin/zsh "$HOME/Library/Application Support/esp32-round-clock/send-rotate.sh" r
```
