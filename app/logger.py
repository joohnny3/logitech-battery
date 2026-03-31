import json as _json
import logging
import os
import socket
import sys
import time
from datetime import datetime, timedelta
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any

from app.time_utils import TAIWAN_TZ

_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_ELK_LOG_FILE_NAME = "mouse-battery.ndjson"


class _TaiwanTimeFormatter(logging.Formatter):
    """Format all log timestamps in Taiwan time (UTC+8)."""

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        ts = datetime.fromtimestamp(record.created, tz=TAIWAN_TZ)
        if datefmt:
            return ts.strftime(datefmt)
        return ts.isoformat(timespec="milliseconds")


class _TaiwanDailyFileHandler(TimedRotatingFileHandler):
    """Rotate the plain-text app log at Taiwan midnight."""

    def computeRollover(self, currentTime: int) -> int:
        current_dt = datetime.fromtimestamp(currentTime, tz=TAIWAN_TZ)
        next_midnight = (current_dt + timedelta(days=1)).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        return int(next_midnight.timestamp())

    def doRollover(self) -> None:
        if self.stream:
            self.stream.close()
            self.stream = None

        completed_day = datetime.fromtimestamp(self.rolloverAt, tz=TAIWAN_TZ) - timedelta(days=1)
        rotated_path = self.rotation_filename(
            f"{self.baseFilename}.{completed_day.strftime(self.suffix)}"
        )

        if os.path.exists(rotated_path):
            os.remove(rotated_path)
        if os.path.exists(self.baseFilename):
            self.rotate(self.baseFilename, rotated_path)

        if not self.delay:
            self.stream = self._open()

        self.rolloverAt = self.computeRollover(int(time.time()))

        if self.backupCount > 0:
            for old_log in self.getFilesToDelete():
                os.remove(old_log)


class _EcsJsonFormatter(logging.Formatter):
    """Produce one ECS-shaped JSON object per line in Taiwan time."""

    def __init__(self, service_name: str, environment: str) -> None:
        super().__init__()
        self._service_name = service_name
        self._environment = environment
        self._host_name = socket.gethostname()

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=TAIWAN_TZ)
        entry: dict[str, Any] = {
            "@timestamp": ts.isoformat(timespec="milliseconds"),
            "message": record.getMessage(),
            "event": {
                "dataset": self._service_name,
            },
            "host": {
                "name": self._host_name,
            },
            "log": {
                "level": record.levelname.lower(),
                "logger": record.name,
                "origin": {
                    "file": {
                        "name": Path(record.pathname).name,
                        "line": record.lineno,
                    },
                    "function": record.funcName,
                },
            },
            "process": {
                "pid": record.process,
                "name": record.processName,
                "thread": {
                    "name": record.threadName,
                },
            },
            "service": {
                "name": self._service_name,
                "environment": self._environment,
            },
        }
        if record.exc_info and record.exc_info[0] is not None:
            exc_type, exc_value, _ = record.exc_info
            entry["error"] = {
                "type": exc_type.__name__,
                "message": str(exc_value),
                "stack_trace": self.formatException(record.exc_info),
            }
        return _json.dumps(entry, ensure_ascii=False)


def setup_logging(level: int = logging.INFO) -> None:
    _LOG_DIR.mkdir(exist_ok=True)

    fmt = _TaiwanTimeFormatter(
        "[%(asctime)s] %(levelname)-7s %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = _TaiwanDailyFileHandler(
        _LOG_DIR / "app.log", when="midnight", backupCount=30, encoding="utf-8",
    )
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setFormatter(fmt)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(file_handler)
    root.addHandler(console_handler)


def setup_elk_logging(
    elk_log_path: str,
    service_name: str = "mouse-battery",
    environment: str = "development",
) -> None:
    """Add a JSON file handler that writes NDJSON to the ELK collected-logs directory."""
    log_dir = Path(elk_log_path)
    log_dir.mkdir(parents=True, exist_ok=True)
    elk_file = log_dir / _ELK_LOG_FILE_NAME

    elk_handler = logging.FileHandler(elk_file, encoding="utf-8")
    elk_handler.setFormatter(_EcsJsonFormatter(service_name, environment))

    logging.getLogger().addHandler(elk_handler)
    logging.getLogger(__name__).info("ELK JSON logging enabled → %s", elk_file)
