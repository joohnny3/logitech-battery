"""Tests for connection module."""
from unittest.mock import patch, MagicMock

from app.services.connection import (
    discover_connections,
    ReceiverConnection,
    BluetoothConnection,
    _is_bluetooth_pid,
    _is_receiver_pid,
)


def _make_hid_device(pid=0xC54D, product="USB Receiver", usage_page=0xFF00,
                     usage=0x0001, iface=2, bus_id=0x03):
    return {
        "vendor_id": 0x046D,
        "product_id": pid,
        "product_string": product,
        "usage_page": usage_page,
        "usage": usage,
        "interface_number": iface,
        "path": f"\\\\?\\hid#path_{pid:04x}_{usage:04x}".encode(),
        "serial_number": "",
        "release_number": 0,
        "manufacturer_string": "Logitech",
    }


class TestPidRanges:
    def test_receiver_pid(self):
        assert _is_receiver_pid(0xC54D) is True
        assert _is_receiver_pid(0xC539) is True
        assert _is_receiver_pid(0xC548) is True
        assert _is_receiver_pid(0xB012) is False

    def test_bluetooth_pid(self):
        assert _is_bluetooth_pid(0xB012) is True
        assert _is_bluetooth_pid(0xB023) is True
        assert _is_bluetooth_pid(0xB35B) is True
        assert _is_bluetooth_pid(0xC54D) is False
        assert _is_bluetooth_pid(0xB011) is False


class TestDiscoverConnections:
    @patch("app.services.connection.hid.enumerate")
    def test_no_devices(self, mock_enum):
        mock_enum.return_value = []
        conns = discover_connections()
        assert conns == []

    @patch("app.services.connection.hid.enumerate")
    def test_finds_receiver_pair(self, mock_enum):
        mock_enum.return_value = [
            _make_hid_device(pid=0xC54D, usage_page=0xFF00, usage=0x0001),
            _make_hid_device(pid=0xC54D, usage_page=0xFF00, usage=0x0002),
        ]
        with patch.object(ReceiverConnection, "__init__", return_value=None):
            conns = discover_connections()
            assert len(conns) == 1
            assert isinstance(conns[0], ReceiverConnection)

    @patch("app.services.connection.hid.enumerate")
    def test_finds_bluetooth_device(self, mock_enum):
        mock_enum.return_value = [
            _make_hid_device(pid=0xB023, product="MX Master 3", usage_page=0x0001, usage=0x0002),
        ]
        with patch.object(BluetoothConnection, "__init__", return_value=None):
            conns = discover_connections()
            assert len(conns) == 1
            assert isinstance(conns[0], BluetoothConnection)

    @patch("app.services.connection.hid.enumerate")
    def test_finds_both_types(self, mock_enum):
        mock_enum.return_value = [
            _make_hid_device(pid=0xC54D, usage_page=0xFF00, usage=0x0001),
            _make_hid_device(pid=0xC54D, usage_page=0xFF00, usage=0x0002),
            _make_hid_device(pid=0xB023, product="MX Master 3", usage_page=0x0001, usage=0x0002),
        ]
        with patch.object(ReceiverConnection, "__init__", return_value=None), \
             patch.object(BluetoothConnection, "__init__", return_value=None):
            conns = discover_connections()
            assert len(conns) == 2
            # Receivers come first
            assert isinstance(conns[0], ReceiverConnection)
            assert isinstance(conns[1], BluetoothConnection)

    @patch("app.services.connection.hid.enumerate")
    def test_ignores_non_logitech_pids(self, mock_enum):
        mock_enum.return_value = [
            _make_hid_device(pid=0x1234, usage_page=0xFF00, usage=0x0001),
        ]
        conns = discover_connections()
        assert conns == []

    @patch("app.services.connection.hid.enumerate")
    def test_receiver_single_interface_fallback(self, mock_enum):
        # Only short channel found
        mock_enum.return_value = [
            _make_hid_device(pid=0xC54D, usage_page=0xFF00, usage=0x0001),
        ]
        with patch.object(ReceiverConnection, "__init__", return_value=None):
            conns = discover_connections()
            assert len(conns) == 1


class TestReceiverConnection:
    def test_connection_type(self):
        with patch.object(ReceiverConnection, "__init__", return_value=None):
            conn = ReceiverConnection.__new__(ReceiverConnection)
            conn._device_index = 0x01
            assert conn.connection_type == "receiver"
            assert conn.device_index == 0x01


class TestBluetoothConnection:
    def test_connection_type(self):
        with patch.object(BluetoothConnection, "__init__", return_value=None):
            conn = BluetoothConnection.__new__(BluetoothConnection)
            assert conn.connection_type == "bluetooth"
            assert conn.device_index == 0xFF


class TestMatchDeviceIndex:
    def test_import_and_use(self):
        from app.services.battery_reader import _match_device_index
        # Exact match
        assert _match_device_index(0x01, 0x01) is True
        # BT: device replies 0x00 for 0xFF
        assert _match_device_index(0x00, 0xFF) is True
        assert _match_device_index(0xFF, 0x00) is True
        # No match
        assert _match_device_index(0x02, 0x01) is False
