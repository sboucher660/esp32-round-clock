# ESP32-2424S012 — back of board, free GPIO

View with the **round PCB facing you**, **USB-C at the bottom** (same as your photo).

Open the diagram: **[board-back-gpio.svg](board-back-gpio.svg)** (Preview on Mac: double-click).

## Easiest place to add a page button

### **P1 — 4-pin white header (bottom-left)**

| Pin | Label | ESP32 GPIO | Use |
|-----|--------|------------|-----|
| 1 | GND | — | Switch leg |
| 2 | 3.3V | — | Power (do not short to GND) |
| 3 | TX | **GPIO 21** | **Button input** (or serial TX) |
| 4 | RX | **GPIO 20** | **Button input** (or serial RX) |

**Wiring:** momentary switch between **GPIO 21** (pin 3) and **GND** (pin 1). Same idea as BOOT: active LOW with `INPUT_PULLUP` in code.

If you still flash over USB, you can use GPIO 21 and keep USB debug; GPIO 20/21 are only “busy” when you use them as UART.

### **S1 pads (upper-left, near ESP module)**

Schematic **S1** → **GPIO 8** with a 10k pull-up. Often **empty solder pads** (no switch fitted). Solder a tact switch or two wires there for an external page button.

On your unit, the **right-edge** switch is **not** this — that one goes to the **battery PMIC** (power key).

## Also free on **no-touch** (N) boards only

| GPIO | Where | Notes |
|------|--------|--------|
| **1** | Near touch/I2C area | Touch reset — unused on N |
| **4** | I2C SDA pads | Unused on N |
| **5** | I2C SCL pads | Unused on N |

Do **not** use these on the **touch** (C) variant — they go to the CST816.

## Already used (don’t use)

| GPIO | Function |
|------|----------|
| 2 | Display DC |
| 3 | Backlight |
| 6 | SPI clock |
| 7 | SPI data |
| 9 | BOOT button (pages in firmware) |
| 10 | Display chip select |
| 18 / 19 | USB |

## Not GPIO

| Control | Role |
|---------|------|
| **RST** (left) | Hard reset |
| **Side button** (right edge) | Battery **power** key → charger IC |
| **BAT+** (right) | 3.7 V LiPo |

## Suggested external button

1. Solder a small wire from **P1 pin 3 (GPIO 21)** and **P1 pin 1 (GND)** to a tact switch.
2. Tell firmware `BUTTON_PIN 21` (or a second pin alongside BOOT).
