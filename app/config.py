import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "config.json"

_DEFAULTS = {
    "refresh_seconds": 60,
    "low_battery_threshold": 20,
    "enable_low_battery_notification": True,
    "device_name_keywords": ["Logitech"],
}


@dataclass
class AppConfig:
    refresh_seconds: int = _DEFAULTS["refresh_seconds"]
    low_battery_threshold: int = _DEFAULTS["low_battery_threshold"]
    enable_low_battery_notification: bool = _DEFAULTS["enable_low_battery_notification"]
    device_name_keywords: list[str] = field(default_factory=lambda: list(_DEFAULTS["device_name_keywords"]))

    @classmethod
    def load(cls, path: Path | None = None) -> "AppConfig":
        path = path or _DEFAULT_CONFIG_PATH
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            logger.warning("無法讀取設定檔 %s，使用預設值: %s", path, exc)
            return cls()

        config = cls(
            refresh_seconds=raw.get("refresh_seconds", _DEFAULTS["refresh_seconds"]),
            low_battery_threshold=raw.get("low_battery_threshold", _DEFAULTS["low_battery_threshold"]),
            enable_low_battery_notification=raw.get("enable_low_battery_notification", _DEFAULTS["enable_low_battery_notification"]),
            device_name_keywords=raw.get("device_name_keywords", list(_DEFAULTS["device_name_keywords"])),
        )
        config._validate()
        return config

    def _validate(self) -> None:
        if self.refresh_seconds < 1:
            logger.warning("refresh_seconds=%s 不合法，使用預設值", self.refresh_seconds)
            self.refresh_seconds = _DEFAULTS["refresh_seconds"]

        if not 1 <= self.low_battery_threshold <= 100:
            logger.warning("low_battery_threshold=%s 不合法，使用預設值", self.low_battery_threshold)
            self.low_battery_threshold = _DEFAULTS["low_battery_threshold"]

        if not isinstance(self.device_name_keywords, list):
            logger.warning("device_name_keywords 格式不正確，使用預設值")
            self.device_name_keywords = list(_DEFAULTS["device_name_keywords"])
