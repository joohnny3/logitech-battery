"""Tests for BatteryStatus model."""
from datetime import datetime

from app.models.battery_status import BatteryStatus, BatteryStatusType, ChargingState


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
