"""Tests for BatteryStatus model."""
from datetime import datetime, timezone

from app.models.battery_status import BatteryStatus, BatteryStatusType, ChargingState
from app.time_utils import TAIWAN_TZ


class TestBatteryStatus:
    def test_default_values(self):
        s = BatteryStatus()
        assert s.device_name == "Unknown"
        assert s.level is None
        assert s.status == BatteryStatusType.UNAVAILABLE

    def test_success_display(self):
        s = BatteryStatus(device_name="G Pro", level=80, status=BatteryStatusType.SUCCESS)
        assert "80%" in s.display_text
        assert "G Pro" in s.display_text

    def test_error_display(self):
        s = BatteryStatus(device_name="G Pro", status=BatteryStatusType.ERROR)
        assert "讀取失敗" in s.display_text

    def test_unavailable_display(self):
        s = BatteryStatus(device_name="G Pro", status=BatteryStatusType.UNAVAILABLE)
        assert "無法取得電量" in s.display_text

    def test_tooltip_contains_time(self):
        now = datetime.now()
        s = BatteryStatus(device_name="G Pro", level=50, status=BatteryStatusType.SUCCESS, updated_at=now)
        assert now.strftime("%H:%M:%S") in s.tooltip

    def test_default_updated_at_uses_taiwan_timezone(self):
        s = BatteryStatus()
        assert s.updated_at.tzinfo == TAIWAN_TZ
        assert s.updated_at.utcoffset().total_seconds() == 8 * 60 * 60

    def test_tooltip_converts_utc_time_to_taiwan(self):
        utc_time = datetime(2026, 4, 1, 4, 5, 6, tzinfo=timezone.utc)
        s = BatteryStatus(device_name="G Pro", level=50, status=BatteryStatusType.SUCCESS, updated_at=utc_time)
        assert "12:05:06" in s.tooltip

    def test_charging_display(self):
        s = BatteryStatus(device_name="G Pro", level=80, charging=True,
                          charging_state=ChargingState.CHARGING, status=BatteryStatusType.SUCCESS)
        assert "80%" in s.display_text
        assert "充電中" in s.display_text

    def test_not_charging_display(self):
        s = BatteryStatus(device_name="G Pro", level=80, charging=False, status=BatteryStatusType.SUCCESS)
        assert "80%" in s.display_text
        assert "充電" not in s.display_text

    def test_charging_default_false(self):
        s = BatteryStatus()
        assert s.charging is False
        assert s.charging_state == ChargingState.DISCHARGING

    def test_full_display(self):
        s = BatteryStatus(device_name="G Pro", level=100, charging=True,
                          charging_state=ChargingState.FULL, status=BatteryStatusType.SUCCESS)
        assert "100%" in s.display_text
        assert "已充滿" in s.display_text
        assert "充電中" not in s.display_text

    def test_charging_state_enum(self):
        assert ChargingState.DISCHARGING.value == "discharging"
        assert ChargingState.CHARGING.value == "charging"
        assert ChargingState.FULL.value == "full"
