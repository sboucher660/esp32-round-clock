# Mini Mac case for your round clock

One classic **Macintosh-style shell** for the **ESP32-2424S012** (1.28″ round display, ~38 × 37 mm board).

Inspired by [Thingiverse 6791318](https://www.thingiverse.com/thing:6791318) — **no keyboard, no mouse**. That download uses a **0.96″ OLED**; this case is rebuilt for **your** round screen.

---

## How it sits (this is the important part)

```
        YOU LOOK HERE
             ↓
      ┌──────────────┐
      │  round glass │  ← front of case
      │              │
      │    chin      │
      └──────┬───────┘
             │ USB cable
          desk surface
```

| Direction | What |
|-----------|------|
| **Front** | Round display hole |
| **Back** | Open — slide the board in here, then attach the back plate |
| **Bottom** | USB-C slot (cable goes down to the desk) |
| **Back-right hole** | BOOT button (optional) |

---

## Print these two files

| File | What it is |
|------|------------|
| `stl/mini-mac-body.stl` | Main shell |
| `stl/mini-mac-back.stl` | Rear cover (glue on) |

Generate:

```bash
cd /Users/seb/Documents/esp32-round-clock/case
./export-stl.sh
```

Preview in OpenSCAD: open `mini-mac.scad`, leave `part = "preview"`, press F5.

**Print orientation:** put the **back** of the Mac flat on the build plate (the side you slide the board into faces **up**).

**Filament:** beige or cream PLA.

---

## Assembly (4 steps)

1. Slide the ESP32 module **into the back opening**, screen first, until the round glass sits in the front ring.
2. Plug **USB-C from below** through the bottom slot.
3. Glue or tape **`mini-mac-back`** on the rear.
4. Use **⌘⇧← / ⌘⇧→** on the Mac for pages (or the BOOT hole).

---

## If fit is tight

Edit `mini-mac.scad` → increase `clearance` (try `0.7`).

Other files in this folder (`mcm-desk.scad`, `macintosh-desk.scad`) are old attempts — **ignore them**; only print **mini-mac-***.

---

## Board reference

[docs/board-back-gpio.md](../docs/board-back-gpio.md)
