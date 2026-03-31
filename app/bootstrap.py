"""Bootstrap: initialize and wire up all components."""
from __future__ import annotations

import logging

from app.config import AppConfig
from app.logger import setup_logging, setup_elk_logging
from app.notifier import Notifier
from app.services.battery_reader import read_battery
from app.services.scheduler import Scheduler
from app.tray_app import TrayApp

logger = logging.getLogger(__name__)


class Application:
    def __init__(self) -> None:
        setup_logging()
        logger.info("=== Mouse Battery Monitor 啟動 ===")

        self._config = AppConfig.load()
        logger.info("設定: refresh=%ds, threshold=%d%%, keywords=%s",
                     self._config.refresh_seconds,
                     self._config.low_battery_threshold,
                     self._config.device_name_keywords)

        if self._config.elk_log_path:
            setup_elk_logging(
                elk_log_path=self._config.elk_log_path,
                service_name=self._config.elk_service_name,
                environment=self._config.elk_environment,
            )

        self._notifier = Notifier(
            threshold=self._config.low_battery_threshold,
            enabled=self._config.enable_low_battery_notification,
        )
        self._tray = TrayApp(on_refresh=self._do_update, on_quit=self._do_quit)
        self._scheduler = Scheduler(
            interval_seconds=self._config.refresh_seconds,
            callback=self._do_update,
        )

    def run(self) -> None:
        self._scheduler.start()
        # tray.run() blocks — must be on main thread (Windows requirement)
        self._tray.run()

    def _do_update(self) -> None:
        status = read_battery()
        self._tray.update(status)
        self._notifier.check_and_notify(status)
        logger.info("電量更新: %s", status.display_text)

    def _do_quit(self) -> None:
        logger.info("正在關閉...")
        self._scheduler.stop()
        self._tray.stop()
