from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class BatteryStatusType(Enum):
    SUCCESS = "success"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


class ChargingState(Enum):
    DISCHARGING = "discharging"
    CHARGING = "charging"
    FULL = "full"


@dataclass
class BatteryStatus:
    device_name: str = "Unknown"
    level: int | None = None
    charging: bool = False
    charging_state: ChargingState = ChargingState.DISCHARGING
    raw_text: str = ""
    updated_at: datetime = field(default_factory=datetime.now)
    status: BatteryStatusType = BatteryStatusType.UNAVAILABLE

    @property
    def display_text(self) -> str:
        if self.status == BatteryStatusType.SUCCESS and self.level is not None:
            if self.charging_state == ChargingState.FULL:
                charge_indicator = " ✓已充滿"
            elif self.charging_state == ChargingState.CHARGING:
                charge_indicator = " ⚡充電中"
            else:
                charge_indicator = ""
            return f"{self.device_name}: {self.level}%{charge_indicator}"
        if self.status == BatteryStatusType.ERROR:
            return f"{self.device_name}: 讀取失敗"
        return f"{self.device_name}: 無法取得電量"

    @property
    def tooltip(self) -> str:
        ts = self.updated_at.strftime("%H:%M:%S")
        return f"{self.display_text}\n更新時間: {ts}"
