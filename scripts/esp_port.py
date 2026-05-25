#!/usr/bin/env python3
"""Find the ESP32 round-clock USB serial port on macOS (auto-detect, refresh stale port.txt)."""

from __future__ import annotations

import glob
import os

ESPRESSIF_VID = 0x303A
DEFAULT_CONFIG = os.path.expanduser(
    "~/Library/Application Support/esp32-round-clock/port.txt"
)


def _to_cu(device: str) -> str:
    if device.startswith("/dev/tty."):
        return "/dev/cu." + device[len("/dev/tty.") :]
    return device


def discover_ports() -> list[str]:
    """Return existing /dev/cu.* ports for Espressif USB (stable sort)."""
    seen: set[str] = set()
    ports: list[str] = []

    # Fast path: glob is much quicker than pyserial list_ports on macOS.
    for path in sorted(glob.glob("/dev/cu.usbmodem*")):
        if os.path.exists(path):
            seen.add(path)
            ports.append(path)

    if ports:
        return ports

    try:
        import serial.tools.list_ports

        for info in serial.tools.list_ports.comports():
            if not info.device:
                continue
            if info.vid != ESPRESSIF_VID:
                desc = (info.description or "").lower()
                mfr = (info.manufacturer or "").lower()
                if not (
                    "esp" in desc
                    or "espressif" in mfr
                    or "jtag" in desc
                    or "usbmodem" in (info.device or "")
                ):
                    continue
            cu = _to_cu(info.device)
            if cu.startswith("/dev/") and os.path.exists(cu) and cu not in seen:
                seen.add(cu)
                ports.append(cu)
    except ImportError:
        pass

    return ports


def read_saved_port(config_path: str = DEFAULT_CONFIG) -> str | None:
    if not os.path.isfile(config_path):
        return None
    try:
        with open(config_path, encoding="utf-8") as f:
            line = f.readline().strip()
    except OSError:
        return None
    if line.startswith("/dev/") and os.path.exists(line):
        return line
    return None


def save_port(port: str, config_path: str = DEFAULT_CONFIG) -> None:
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(port + "\n")


def find_port(
    explicit: str | None = None,
    *,
    config_path: str = DEFAULT_CONFIG,
    save: bool = True,
) -> str | None:
    """
    Pick the clock USB port: explicit > saved port.txt if present > auto-scan.
    Updates port.txt when the saved path is missing or no longer present.
    """
    if explicit:
        cu = _to_cu(explicit)
        if os.path.exists(cu):
            if save:
                save_port(cu, config_path)
            return cu
        return None

    saved = read_saved_port(config_path)
    if saved:
        return saved

    discovered = discover_ports()
    if not discovered:
        return None

    port = discovered[-1] if len(discovered) > 1 else discovered[0]
    if save:
        save_port(port, config_path)
    return port
