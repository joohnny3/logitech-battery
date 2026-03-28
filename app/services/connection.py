"""HID connection abstractions for Logitech devices.

Provides two connection types:
- ReceiverConnection: For Lightspeed/Unifying/Bolt USB receivers (dual-channel)
- BluetoothConnection: For Bluetooth direct connections (single-channel)

Both expose a unified interface for sending HID++ requests and reading responses.
"""
from __future__ import annotations

import logging
import sys
import time
from typing import Protocol, runtime_checkable

import hid

logger = logging.getLogger(__name__)

LOGITECH_VID = 0x046D

# HID++ usage page for Logitech vendor-specific communication
HIDPP_USAGE_PAGE = 0xFF00

# Bluetooth PID ranges (from Solaar project)
_BT_PID_RANGES = [(0xB012, 0xB0FF), (0xB317, 0xB3FF)]

# Known Lightspeed/Unifying/Bolt receiver PID range
_RECEIVER_PID_MIN = 0xC500
_RECEIVER_PID_MAX = 0xC5FF


@runtime_checkable
class DeviceConnection(Protocol):
    """Protocol for HID++ device connections."""

    @property
    def connection_type(self) -> str: ...

    @property
    def device_index(self) -> int: ...

    def send_long(self, data: bytes) -> int: ...

    def read(self, timeout_ms: int = 500) -> bytes | None: ...

    def close(self) -> None: ...

    def prepare(self) -> None: ...


class ReceiverConnection:
    """Dual-channel connection to a Logitech USB receiver (Lightspeed/Unifying/Bolt)."""

    def __init__(self, short_path: bytes, long_path: bytes, device_index: int = 0x01):
        self._short = hid.device()
        self._long = hid.device()
        self._short.open_path(short_path)
        self._long.open_path(long_path)
        self._short.set_nonblocking(True)
        self._long.set_nonblocking(True)
        self._device_index = device_index

    @property
    def connection_type(self) -> str:
        return "receiver"

    @property
    def device_index(self) -> int:
        return self._device_index

    def send_long(self, data: bytes) -> int:
        return self._long.write(data)

    def read(self, timeout_ms: int = 500) -> bytes | None:
        # Poll long channel first (device responses come here)
        resp = self._long.read(64, timeout_ms=min(timeout_ms, 250))
        if resp:
            return bytes(resp)
        # Then poll short channel (receiver-level responses)
        resp = self._short.read(64, timeout_ms=min(timeout_ms, 250))
        if resp:
            return bytes(resp)
        return None

    def close(self) -> None:
        self._short.close()
        self._long.close()

    def prepare(self) -> None:
        """Drain pending messages and enable wireless notifications."""
        self._drain()
        self._enable_notifications()

    def _drain(self, timeout_sec: float = 0.5) -> None:
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            got_any = False
            for dev, label in [(self._short, "short"), (self._long, "long")]:
                r = dev.read(64, timeout_ms=50)
                if r:
                    got_any = True
                    logger.debug("Drain [%s]: %s", label, bytes(r).hex())
            if not got_any:
                break

    def _enable_notifications(self) -> None:
        req = bytes([0x10, 0xFF, 0x80, 0x00, 0x00, 0x09, 0x00])
        self._short.write(req)
        time.sleep(0.3)
        resp = self._short.read(64, timeout_ms=500)
        if resp:
            logger.debug("Enable notifications response: %s", bytes(resp).hex())
        self._drain(timeout_sec=3.0)


class BluetoothConnection:
    """Single-channel connection to a Bluetooth-connected Logitech device."""

    def __init__(self, device_path: bytes):
        self._dev = hid.device()
        self._dev.open_path(device_path)
        self._dev.set_nonblocking(True)

    @property
    def connection_type(self) -> str:
        return "bluetooth"

    @property
    def device_index(self) -> int:
        return 0xFF

    def send_long(self, data: bytes) -> int:
        return self._dev.write(data)

    def read(self, timeout_ms: int = 500) -> bytes | None:
        resp = self._dev.read(64, timeout_ms=timeout_ms)
        if resp:
            return bytes(resp)
        return None

    def close(self) -> None:
        self._dev.close()

    def prepare(self) -> None:
        # Bluetooth direct connections don't need receiver initialization
        pass


def _is_bluetooth_pid(pid: int) -> bool:
    return any(lo <= pid <= hi for lo, hi in _BT_PID_RANGES)


def _is_receiver_pid(pid: int) -> bool:
    return _RECEIVER_PID_MIN <= pid <= _RECEIVER_PID_MAX


def discover_connections(vid: int = LOGITECH_VID) -> list[DeviceConnection]:
    """Discover all available Logitech HID++ connections.

    Returns a list of DeviceConnection objects (receivers first, then Bluetooth).
    """
    all_devs = hid.enumerate(vid)
    connections: list[DeviceConnection] = []

    # --- 1. Find USB receivers (Lightspeed / Unifying / Bolt) ---
    # Group HID++ interfaces by product_id to find short+long pairs
    receiver_interfaces: dict[int, dict[int, bytes]] = {}  # pid -> {usage: path}
    for d in all_devs:
        pid = d["product_id"]
        if not _is_receiver_pid(pid):
            continue

        usage_page = d.get("usage_page", 0)
        usage = d.get("usage", 0)

        if usage_page == HIDPP_USAGE_PAGE and usage in (0x0001, 0x0002):
            receiver_interfaces.setdefault(pid, {})[usage] = d["path"]
        elif usage_page == 0 and sys.platform == "darwin":
            # macOS IOKit may not report usage_page; use interface_number
            iface = d.get("interface_number", -1)
            if iface in (0, 1, 2):
                # interface 0 or 1 = short, interface 2 = long (common mapping)
                mapped_usage = 0x0001 if iface <= 1 else 0x0002
                receiver_interfaces.setdefault(pid, {}).setdefault(mapped_usage, d["path"])

    for pid, usages in receiver_interfaces.items():
        short_path = usages.get(0x0001)
        long_path = usages.get(0x0002)
        if short_path and long_path:
            logger.info("Found receiver: PID=0x%04x (short+long)", pid)
            connections.append(ReceiverConnection(short_path, long_path))
        elif short_path or long_path:
            # Fallback: single interface, use for both
            path = short_path or long_path
            logger.info("Found receiver: PID=0x%04x (single interface fallback)", pid)
            connections.append(ReceiverConnection(path, path))

    # --- 2. Find Bluetooth direct-connected devices ---
    for d in all_devs:
        pid = d["product_id"]
        if not _is_bluetooth_pid(pid):
            continue
        logger.info("Found Bluetooth device: PID=0x%04x product=%s",
                     pid, d.get("product_string", ""))
        connections.append(BluetoothConnection(d["path"]))

    if not connections:
        logger.warning("找不到任何 Logitech HID++ 裝置")

    return connections
