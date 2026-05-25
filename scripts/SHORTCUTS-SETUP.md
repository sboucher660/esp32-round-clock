# Page hotkeys via Apple Shortcuts (fallback)

**Default:** run `./scripts/install_usb_daemon.sh` — hotkeys work via **ESP32 Clock.app** (one-time Accessibility).

Use this guide only if the built-in hotkey app is blocked or you prefer Shortcuts.

## 1. Test USB first

In Terminal:

```bash
~/Library/Application\ Support/esp32-round-clock/send-page.sh next
~/Library/Application\ Support/esp32-round-clock/send-page.sh prev
```

The clock display should change page each time. If not, USB/port is the problem — not hotkeys.

### Display rotation (90° steps)

```bash
~/Library/Application\ Support/esp32-round-clock/send-rotate.sh right
~/Library/Application\ Support/esp32-round-clock/send-rotate.sh left
```

Rotation is saved on the device (survives reboot). Requires firmware with `/rotate/right` and `/rotate/left` HTTP endpoints (flash after pulling latest `main.cpp`).

## 2. Shortcut “Clock Next”

1. Open **Shortcuts** app
2. **File → New Shortcut**
3. Add action **Run Shell Script**
4. Script:

```bash
"$HOME/Library/Application Support/esp32-round-clock/send-page.sh" next
```

5. Shell: **/bin/zsh**
6. Name the shortcut **Clock Next**
7. Click shortcut **ⓘ** (info) → **Add Keyboard Shortcut**
8. Press **⌘⇧→** (Command + Shift + Right Arrow)

## 3. Shortcut “Clock Prev”

Same steps, script:

```bash
"$HOME/Library/Application Support/esp32-round-clock/send-page.sh" prev
```

Keyboard shortcut: **⌘⇧←**

## 4. Allow Shortcuts automation

If macOS asks to allow Shortcuts to run scripts, click **Allow**.

Shortcuts runs with its own permissions — no need to find `.venv`.

## Stop the old background app (optional)

```bash
./scripts/uninstall_mac_page_daemon.sh
launchctl bootout gui/$(id -u) ~/Applications/ESP32\ Clock\ Hotkeys.app 2>/dev/null || true
```

You can use Shortcuts only.

## Karabiner-Elements (recommended if Shortcuts hotkeys fail)

1. Install [Karabiner-Elements](https://karabiner-elements.pqrs.org/)
2. **System Settings → Privacy & Security → Input Monitoring** — enable **karabiner_grabber** (and **karabiner_observer** if listed)
3. Open **Karabiner-Elements → Complex Modifications → Add rule → Import more rules from the Internet** — or **Import from file**:
   - `scripts/karabiner-esp32-clock.json` in this repo
4. Enable both rules (**Cmd+Shift+Right** = next, **Cmd+Shift+Left** = prev)
5. Stop the background hotkey app so USB stays free:

```bash
./scripts/stop-hotkeys.sh
```

Karabiner runs the same `send-page.sh` as Shortcuts — no Accessibility needed.

### After reboot (Karabiner)

1. Run once (or after macOS updates):

```bash
cd ~/Documents/esp32-round-clock
chmod +x scripts/install_karabiner_setup.sh
./scripts/install_karabiner_setup.sh
```

2. **Karabiner-Elements → Settings** — turn on **start at login** (or add Karabiner in **System Settings → General → Login Items**).

3. **System Settings → Privacy & Security → Input Monitoring** — **Karabiner-Elements** / **karabiner_grabber** must be ON (macOS sometimes turns this off after updates).

4. In each complex-modification rule, set **shell_command** to the installed scripts (full paths printed by the installer), e.g.  
   `~/Library/Application Support/esp32-round-clock/karabiner-next.zsh`

5. Plug in the clock (USB), then test in Terminal:

```bash
~/Library/Application\ Support/esp32-round-clock/karabiner-next.zsh
```

6. If you previously installed **ESP32 Clock Hotkeys** (`install_mac_page_daemon.sh`), remove it so it does not grab USB at login:

```bash
./scripts/uninstall_mac_page_daemon.sh
```
