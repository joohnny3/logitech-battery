import json
import logging
from datetime import datetime
from pathlib import Path

from app.logger import _ELK_LOG_FILE_NAME, _EcsJsonFormatter, setup_elk_logging
from app.time_utils import TAIWAN_TZ


class TestEcsJsonFormatter:
    def test_format_uses_ecs_fields_and_taiwan_time(self):
        formatter = _EcsJsonFormatter(service_name="mouse-battery", environment="development")
        record = logging.LogRecord(
            name="app.bootstrap",
            level=logging.INFO,
            pathname=str(Path("app") / "bootstrap.py"),
            lineno=42,
            msg="電量更新: PRO X 2: 88%",
            args=(),
            exc_info=None,
            func="main",
        )
        record.created = datetime(2026, 4, 1, 5, 12, 58, tzinfo=TAIWAN_TZ).timestamp()
        record.process = 1234
        record.processName = "pythonw.exe"
        record.threadName = "MainThread"

        payload = json.loads(formatter.format(record))

        assert payload["@timestamp"] == "2026-04-01T05:12:58.000+08:00"
        assert payload["message"] == "電量更新: PRO X 2: 88%"
        assert payload["event"]["dataset"] == "mouse-battery"
        assert payload["log"]["level"] == "info"
        assert payload["log"]["logger"] == "app.bootstrap"
        assert payload["log"]["origin"]["file"]["name"] == "bootstrap.py"
        assert payload["log"]["origin"]["file"]["line"] == 42
        assert payload["log"]["origin"]["function"] == "main"
        assert payload["service"]["name"] == "mouse-battery"
        assert payload["service"]["environment"] == "development"
        assert payload["process"]["pid"] == 1234
        assert payload["process"]["name"] == "pythonw.exe"
        assert payload["process"]["thread"]["name"] == "MainThread"
        assert payload["host"]["name"]


class TestSetupElkLogging:
    def test_setup_elk_logging_writes_to_ndjson_file(self, tmp_path):
        root = logging.getLogger()
        original_handlers = list(root.handlers)
        original_level = root.level
        added_handlers = []

        try:
            root.setLevel(logging.INFO)
            setup_elk_logging(str(tmp_path), service_name="mouse-battery", environment="test")
            added_handlers = [handler for handler in root.handlers if handler not in original_handlers]

            assert len(added_handlers) == 1
            assert Path(added_handlers[0].baseFilename).name == _ELK_LOG_FILE_NAME

            logging.getLogger("tests.logger").info("hello ecs")
            added_handlers[0].flush()

            lines = (tmp_path / _ELK_LOG_FILE_NAME).read_text(encoding="utf-8").strip().splitlines()
            assert len(lines) >= 1

            payload = json.loads(lines[-1])
            assert payload["message"] == "hello ecs"
            assert payload["service"]["name"] == "mouse-battery"
            assert payload["service"]["environment"] == "test"
        finally:
            for handler in added_handlers:
                root.removeHandler(handler)
                handler.close()
            root.setLevel(original_level)