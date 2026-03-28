"""Tests for config module."""
import json
import tempfile
from pathlib import Path

import pytest

from app.config import AppConfig


class TestAppConfig:
    def test_load_defaults_when_no_file(self, tmp_path):
        config = AppConfig.load(tmp_path / "nonexistent.json")
        assert config.refresh_seconds == 60
        assert config.low_battery_threshold == 20
        assert config.enable_low_battery_notification is True
        assert config.device_name_keywords == ["Logitech"]

    def test_load_from_valid_file(self, tmp_path):
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps({
            "refresh_seconds": 120,
            "low_battery_threshold": 30,
            "enable_low_battery_notification": False,
            "device_name_keywords": ["MX", "Master"],
        }), encoding="utf-8")
        config = AppConfig.load(cfg_file)
        assert config.refresh_seconds == 120
        assert config.low_battery_threshold == 30
        assert config.enable_low_battery_notification is False
        assert config.device_name_keywords == ["MX", "Master"]

    def test_load_invalid_json_uses_defaults(self, tmp_path):
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text("{bad json", encoding="utf-8")
        config = AppConfig.load(cfg_file)
        assert config.refresh_seconds == 60

    def test_validate_refresh_seconds_too_low(self, tmp_path):
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps({"refresh_seconds": 0}), encoding="utf-8")
        config = AppConfig.load(cfg_file)
        assert config.refresh_seconds == 60  # falls back to default

    def test_validate_threshold_out_of_range(self, tmp_path):
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps({"low_battery_threshold": 200}), encoding="utf-8")
        config = AppConfig.load(cfg_file)
        assert config.low_battery_threshold == 20  # falls back to default

    def test_validate_threshold_negative(self, tmp_path):
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps({"low_battery_threshold": -5}), encoding="utf-8")
        config = AppConfig.load(cfg_file)
        assert config.low_battery_threshold == 20

    def test_partial_config_uses_defaults_for_missing(self, tmp_path):
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps({"refresh_seconds": 30}), encoding="utf-8")
        config = AppConfig.load(cfg_file)
        assert config.refresh_seconds == 30
        assert config.low_battery_threshold == 20
        assert config.enable_low_battery_notification is True
