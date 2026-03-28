"""Low battery notification module."""
from __future__ import annotations

import logging

from plyer import notification

from app.models.battery_status import BatteryStatus, BatteryStatusType

logger = logging.getLogger(__name__)


class Notifier:
    def __init__(self, threshold: int = 20, enabled: bool = True):
        self._threshold = threshold
        self._enabled = enabled
        self._last_notified_level: int | None = None

    def check_and_notify(self, status: BatteryStatus) -> None:
        if not self._enabled:
            return

        if status.status != BatteryStatusType.SUCCESS or status.level is None:
            return

        if status.level > self._threshold:
            # Battery is fine, reset notification state
            self._last_notified_level = None
            return

        # Avoid repeated notifications for the same level range
        # Only re-notify if level dropped to a lower 5% bracket
        bracket = status.level // 5
        if self._last_notified_level is not None:
            last_bracket = self._last_notified_level // 5
            if bracket >= last_bracket:
                return

        self._send_notification(status)
        self._last_notified_level = status.level

    def _send_notification(self, status: BatteryStatus) -> None:
        title = "滑鼠電量過低"
        message = f"{status.device_name} 電量剩餘 {status.level}%"
        logger.info("發送低電量通知: %s", message)
        try:
            notification.notify(
                title=title,
                message=message,
                app_name="Mouse Battery Monitor",
                timeout=10,
            )
        except Exception:
            logger.exception("發送通知失敗")
