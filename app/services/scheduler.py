"""Background scheduler for periodic battery updates."""
from __future__ import annotations

import logging
import threading
from typing import Callable

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(self, interval_seconds: int, callback: Callable[[], None]):
        self._interval = interval_seconds
        self._callback = callback
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("排程啟動: 每 %d 秒更新", self._interval)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("排程已停止")

    def trigger_now(self) -> None:
        """Trigger an immediate update in a background thread."""
        threading.Thread(target=self._safe_callback, daemon=True).start()

    def _run(self) -> None:
        # Initial update on start
        self._safe_callback()
        while not self._stop_event.wait(timeout=self._interval):
            self._safe_callback()

    def _safe_callback(self) -> None:
        try:
            self._callback()
        except Exception:
            logger.exception("排程回呼執行失敗")
