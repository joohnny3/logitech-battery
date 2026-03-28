"""HID++ 2.0 battery reader for Logitech devices.

Communicates with Logitech devices using hidapi to query battery status
through the HID++ 2.0 protocol.

Supports two connection types:
  - USB Receiver (Lightspeed/Unifying/Bolt): dual-channel, device_index=0x01
  - Bluetooth direct: single-channel, device_index=0xFF

Reference: Solaar project (pwr-Solaar/Solaar) - lib/logitech_receiver/hidpp20.py
"""
from __future__ import annotations

import logging
import struct
import time
from datetime import datetime

from app.models.battery_status import BatteryStatus, BatteryStatusType, ChargingState
from app.services.connection import DeviceConnection, discover_connections

logger = logging.getLogger(__name__)

# HID++ 2.0 feature IDs
FEATURE_ROOT = 0x0000
FEATURE_FEATURE_SET = 0x0001
FEATURE_BATTERY_STATUS = 0x1000
FEATURE_BATTERY_VOLTAGE = 0x1001
FEATURE_UNIFIED_BATTERY = 0x1004
FEATURE_DEVICE_NAME = 0x0005

# HID++ report IDs
REPORT_ID_SHORT = 0x10  # 7 bytes
REPORT_ID_LONG = 0x11   # 20 bytes

# Software ID (arbitrary 4-bit value to tag our requests)
SOFTWARE_ID = 0x0A


class HidppError(Exception):
    pass


def _match_device_index(resp_devnum: int, expected: int) -> bool:
    """Check if response device number matches expected.

    Bluetooth devices may reply with 0x00 when we sent 0xFF (or vice versa).
    """
    return resp_devnum == expected or resp_devnum == (expected ^ 0xFF)


def _build_long_request(device_index: int, feature_index: int, function: int, *params) -> bytes:
    """Build a HID++ long report (20 bytes, report ID 0x11)."""
    fn_sw = ((function & 0x0F) << 4) | (SOFTWARE_ID & 0x0F)
    packet = bytes([REPORT_ID_LONG, device_index, feature_index, fn_sw] + list(params))
    return packet.ljust(20, b"\x00")


def _send_request(conn: DeviceConnection, feature_index: int,
                  function: int, *params, timeout_ms: int = 3000) -> bytes | None:
    """Send a HID++ request on the long channel and read the response."""
    device_index = conn.device_index
    request = _build_long_request(device_index, feature_index, function, *params)
    conn.send_long(request)

    fn_sw = ((function & 0x0F) << 4) | (SOFTWARE_ID & 0x0F)
    deadline = time.monotonic() + timeout_ms / 1000.0

    while time.monotonic() < deadline:
        resp = conn.read(timeout_ms=500)
        if not resp:
            continue

        if len(resp) < 4:
            continue

        report_id = resp[0]
        if report_id not in (REPORT_ID_SHORT, REPORT_ID_LONG):
            continue

        resp_devnum = resp[1]

        # HID++ 1.0 error (sub_id = 0x8F on short report)
        if report_id == REPORT_ID_SHORT and resp[2] == 0x8F and _match_device_index(resp_devnum, device_index):
            error_code = resp[4] if len(resp) > 4 else 0xFF
            logger.debug("HID++ 1.0 error: reg=0x%02x err=0x%02x (ignoring)", resp[3], error_code)
            continue

        # HID++ 2.0 error (feature_index=0xFF on the response)
        if resp[2] == 0xFF and _match_device_index(resp_devnum, device_index):
            error_code = resp[5] if len(resp) > 5 else 0xFF
            logger.warning("HID++ 2.0 error: feature=0x%02x error=0x%02x", resp[3], error_code)
            return None

        # Match our request: same device_index, feature_index, function
        if (_match_device_index(resp_devnum, device_index) and
                resp[2] == feature_index and
                (resp[3] & 0xF0) == (fn_sw & 0xF0)):
            return resp[4:]  # Return payload only

        # Not our response — could be a notification; skip it
        logger.debug("Skipping unmatched response: %s", resp.hex())

    logger.warning("HID++ request timed out: feature_index=0x%02x function=0x%02x", feature_index, function)
    return None


def _get_feature_index(conn: DeviceConnection, feature_id: int) -> tuple[int, int] | None:
    """Query ROOT feature (index 0x00) to discover the index of a given feature ID.

    Returns (feature_index, feature_version) or None if not supported.
    """
    feature_hi = (feature_id >> 8) & 0xFF
    feature_lo = feature_id & 0xFF
    response = _send_request(conn, 0x00, 0x00, feature_hi, feature_lo)
    if response and len(response) >= 1:
        index = response[0]
        if index == 0:
            logger.debug("Feature 0x%04x not supported on device", feature_id)
            return None
        version = response[2] if len(response) >= 3 else 0
        logger.debug("Feature 0x%04x -> index 0x%02x version %d", feature_id, index, version)
        return index, version
    return None


def _get_device_name(conn: DeviceConnection) -> str | None:
    """Query DEVICE_NAME feature to get human-readable name."""
    result = _get_feature_index(conn, FEATURE_DEVICE_NAME)
    if result is None:
        return None
    name_idx, _ = result

    # Function 0x00: getDeviceNameCount
    response = _send_request(conn, name_idx, 0x00)
    if not response:
        return None
    name_length = response[0]

    # Function 0x01: getDeviceName (offset parameter)
    name = b""
    while len(name) < name_length:
        resp = _send_request(conn, name_idx, 0x01, len(name))
        if not resp:
            break
        name += resp[:name_length - len(name)]

    return name.decode("utf-8", errors="replace") if name else None


def _read_unified_battery(conn: DeviceConnection, feature_index: int,
                          version: int = 0) -> tuple[int | None, bool, str]:
    """Read battery via UNIFIED_BATTERY (0x1004) feature.

    Version >= 5 swaps the function order:
      v0-v4: fn 0 = get_status, fn 1 = get_capabilities
      v5+:   fn 0 = get_capabilities, fn 1 = get_status

    Response (get_status): [charge_percent, level_bitmask, status_byte, ...]
    level_bitmask: 8=Full, 4=Good, 2=Low, 1=Critical
    status_byte: 0=Discharging, 1=Recharging, 2=AlmostFull, 3=Full
    """
    status_fn = 0x01 if version >= 5 else 0x00
    response = _send_request(conn, feature_index, status_fn)
    if response and len(response) >= 3:
        discharge, level, status_byte = struct.unpack("!BBB", response[:3])
        # level is a bitmask: 8=Full, 4=Good, 2=Low, 1=Critical
        level_flags = []
        if level & 8: level_flags.append("Full")
        if level & 4: level_flags.append("Good")
        if level & 2: level_flags.append("Low")
        if level & 1: level_flags.append("Critical")
        level_name = "+".join(level_flags) if level_flags else f"Unknown({level})"
        status_names = {0: "Discharging", 1: "Recharging", 2: "Almost Full", 3: "Full"}
        status_name = status_names.get(status_byte, f"Unknown({status_byte})")
        raw = f"charge={discharge}% level={level_name} status={status_name}"
        logger.info("UNIFIED_BATTERY: %s", raw)
        if status_byte == 3:
            charging_state = ChargingState.FULL
        elif status_byte in (1, 2):
            charging_state = ChargingState.CHARGING
        else:
            charging_state = ChargingState.DISCHARGING
        return discharge if discharge > 0 else None, charging_state, raw
    return None, ChargingState.DISCHARGING, "No response from UNIFIED_BATTERY"


def _read_battery_status(conn: DeviceConnection, feature_index: int) -> tuple[int | None, bool, str]:
    """Read battery via BATTERY_STATUS (0x1000) feature.

    Response format: [charge_percent, next_level_percent, status_byte]
    status_byte: 0=Discharging, 1=Recharging, 2=ChargeInFinalStage, 3=ChargeComplete
    """
    response = _send_request(conn, feature_index, 0x00)
    if response and len(response) >= 3:
        discharge, next_level, status_byte = struct.unpack("!BBB", response[:3])
        raw = f"charge={discharge}% next={next_level}% status={status_byte}"
        logger.info("BATTERY_STATUS: %s", raw)
        if status_byte == 3:
            charging_state = ChargingState.FULL
        elif status_byte in (1, 2):
            charging_state = ChargingState.CHARGING
        else:
            charging_state = ChargingState.DISCHARGING
        return discharge if discharge > 0 else None, charging_state, raw
    return None, ChargingState.DISCHARGING, "No response from BATTERY_STATUS"


def _read_battery_voltage(conn: DeviceConnection, feature_index: int) -> tuple[int | None, bool, str]:
    """Read battery via BATTERY_VOLTAGE (0x1001) feature.

    Response format: [voltage_hi, voltage_lo, flags]
    flags bit 7: charging
    """
    response = _send_request(conn, feature_index, 0x00)
    if response and len(response) >= 3:
        voltage, flags = struct.unpack(">HB", response[:3])
        charge = _estimate_battery_percent(voltage)
        charging_state = ChargingState.CHARGING if (flags & 0x80) else ChargingState.DISCHARGING
        raw = f"voltage={voltage}mV estimated={charge}% flags=0x{flags:02x}"
        logger.info("BATTERY_VOLTAGE: %s", raw)
        return charge, charging_state, raw
    return None, ChargingState.DISCHARGING, "No response from BATTERY_VOLTAGE"


def _estimate_battery_percent(millivolts: int) -> int:
    """Estimate battery percentage from voltage (linear interpolation)."""
    table = [
        (4186, 100), (4067, 90), (3989, 80), (3922, 70), (3859, 60),
        (3811, 50), (3778, 40), (3751, 30), (3717, 20), (3671, 10),
        (3646, 5), (3579, 2), (3500, 0),
    ]
    if millivolts >= table[0][0]:
        return 100
    if millivolts <= table[-1][0]:
        return 0
    for i in range(len(table) - 1):
        v_hi, p_hi = table[i]
        v_lo, p_lo = table[i + 1]
        if v_lo <= millivolts <= v_hi:
            return round(p_lo + (p_hi - p_lo) * (millivolts - v_lo) / (v_hi - v_lo))
    return 0


# Battery features to try, in priority order
_BATTERY_FEATURES = [
    FEATURE_UNIFIED_BATTERY,
    FEATURE_BATTERY_STATUS,
    FEATURE_BATTERY_VOLTAGE,
]

# Reader functions per feature (signature: conn, feature_index, version)
_BATTERY_READERS = {
    FEATURE_UNIFIED_BATTERY: _read_unified_battery,
    FEATURE_BATTERY_STATUS: lambda c, f, v: _read_battery_status(c, f),
    FEATURE_BATTERY_VOLTAGE: lambda c, f, v: _read_battery_voltage(c, f),
}


def read_battery(conn: DeviceConnection | None = None) -> BatteryStatus:
    """Read battery status from a Logitech device.

    Args:
        conn: A DeviceConnection to use. If None, auto-discover the first available.

    Returns:
        BatteryStatus with the current battery information.
    """
    now = datetime.now()

    # Auto-discover if no connection provided
    if conn is None:
        connections = discover_connections()
        if not connections:
            logger.warning("找不到 Logitech HID++ 裝置")
            return BatteryStatus(
                device_name="No Device",
                status=BatteryStatusType.UNAVAILABLE,
                raw_text="No Logitech HID++ device found",
                updated_at=now,
            )
        # Try each discovered connection until one succeeds
        for c in connections:
            try:
                result = _read_battery_from_connection(c)
                if result.status == BatteryStatusType.SUCCESS:
                    return result
            except OSError as exc:
                logger.debug("Connection failed (%s): %s", c.connection_type, exc)
                continue
            finally:
                c.close()
        # All connections failed — return last result or unavailable
        return BatteryStatus(
            device_name="No Device",
            status=BatteryStatusType.UNAVAILABLE,
            raw_text="All connections failed",
            updated_at=now,
        )

    try:
        return _read_battery_from_connection(conn)
    finally:
        conn.close()


def _read_battery_from_connection(conn: DeviceConnection) -> BatteryStatus:
    """Read battery from an already-opened connection."""
    now = datetime.now()
    try:
        conn.prepare()

        device_name = _get_device_name(conn) or "Logitech Device"
        logger.info("Connected via %s (device_index=0x%02x): %s",
                     conn.connection_type, conn.device_index, device_name)

        for feature_id in _BATTERY_FEATURES:
            result = _get_feature_index(conn, feature_id)
            if result is not None:
                feature_index, version = result
                reader_fn = _BATTERY_READERS[feature_id]
                level, charging_state, raw = reader_fn(conn, feature_index, version)
                return BatteryStatus(
                    device_name=device_name,
                    level=level,
                    charging=charging_state != ChargingState.DISCHARGING,
                    charging_state=charging_state,
                    raw_text=raw,
                    updated_at=now,
                    status=BatteryStatusType.SUCCESS if level is not None else BatteryStatusType.UNAVAILABLE,
                )

        logger.warning("裝置 %s 不支援任何已知的電量功能", device_name)
        return BatteryStatus(
            device_name=device_name,
            status=BatteryStatusType.UNAVAILABLE,
            raw_text="No supported battery feature found",
            updated_at=now,
        )
    except OSError as exc:
        logger.error("HID 通訊失敗: %s", exc)
        return BatteryStatus(
            device_name="Error",
            status=BatteryStatusType.ERROR,
            raw_text=str(exc),
            updated_at=now,
        )
