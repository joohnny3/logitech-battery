"""Tests for Notifier."""
from unittest.mock import patch, MagicMock

from app.models.battery_status import BatteryStatus, BatteryStatusType
from app.notifier import Notifier


class TestNotifier:
    def test_no_notification_above_threshold(self):
        n = Notifier(threshold=20)
        status = BatteryStatus(level=50, status=BatteryStatusType.SUCCESS)
        with patch.object(n, "_send_notification") as mock:
            n.check_and_notify(status)
            mock.assert_not_called()

    def test_notification_at_threshold(self):
        n = Notifier(threshold=20)
        status = BatteryStatus(level=20, status=BatteryStatusType.SUCCESS, device_name="Mouse")
        with patch.object(n, "_send_notification") as mock:
            n.check_and_notify(status)
            mock.assert_called_once()

    def test_notification_below_threshold(self):
        n = Notifier(threshold=20)
        status = BatteryStatus(level=10, status=BatteryStatusType.SUCCESS, device_name="Mouse")
        with patch.object(n, "_send_notification") as mock:
            n.check_and_notify(status)
            mock.assert_called_once()

    def test_no_repeat_same_bracket(self):
        n = Notifier(threshold=20)
        status = BatteryStatus(level=18, status=BatteryStatusType.SUCCESS, device_name="Mouse")
        with patch.object(n, "_send_notification") as mock:
            n.check_and_notify(status)
            n.check_and_notify(status)  # same level, should not repeat
            assert mock.call_count == 1

    def test_repeat_when_lower_bracket(self):
        n = Notifier(threshold=20)
        with patch.object(n, "_send_notification") as mock:
            n.check_and_notify(BatteryStatus(level=18, status=BatteryStatusType.SUCCESS, device_name="Mouse"))
            n.check_and_notify(BatteryStatus(level=8, status=BatteryStatusType.SUCCESS, device_name="Mouse"))
            assert mock.call_count == 2

    def test_disabled_notifier(self):
        n = Notifier(threshold=20, enabled=False)
        status = BatteryStatus(level=5, status=BatteryStatusType.SUCCESS, device_name="Mouse")
        with patch.object(n, "_send_notification") as mock:
            n.check_and_notify(status)
            mock.assert_not_called()

    def test_no_notification_on_unavailable(self):
        n = Notifier(threshold=20)
        status = BatteryStatus(level=None, status=BatteryStatusType.UNAVAILABLE)
        with patch.object(n, "_send_notification") as mock:
            n.check_and_notify(status)
            mock.assert_not_called()

    def test_reset_after_charge(self):
        n = Notifier(threshold=20)
        with patch.object(n, "_send_notification") as mock:
            # Drop below threshold
            n.check_and_notify(BatteryStatus(level=15, status=BatteryStatusType.SUCCESS, device_name="Mouse"))
            assert mock.call_count == 1
            # Charge back up
            n.check_and_notify(BatteryStatus(level=80, status=BatteryStatusType.SUCCESS, device_name="Mouse"))
            # Drop again - should notify again
            n.check_and_notify(BatteryStatus(level=15, status=BatteryStatusType.SUCCESS, device_name="Mouse"))
            assert mock.call_count == 2
