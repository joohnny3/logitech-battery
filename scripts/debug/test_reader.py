"""Quick test: read battery from actual device."""
import logging
import sys

sys.path.insert(0, ".")

from app.logger import setup_logging
from app.services.battery_reader import read_battery

setup_logging(logging.DEBUG)

print("\n=== Reading battery (auto-detect dual channel) ===")
status = read_battery()
print(f"Device: {status.device_name}")
print(f"Level: {status.level}")
print(f"Status: {status.status}")
print(f"Raw: {status.raw_text}")
print(f"Display: {status.display_text}")
print(f"Tooltip: {status.tooltip}")
