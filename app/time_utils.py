from __future__ import annotations

from datetime import datetime, timedelta, timezone

TAIWAN_TZ = timezone(timedelta(hours=8), name="Asia/Taipei")


def taiwan_now() -> datetime:
    """Return the current time in Taiwan time (UTC+8)."""
    return datetime.now(TAIWAN_TZ)


def to_taiwan_time(value: datetime) -> datetime:
    """Convert a datetime to Taiwan time.

    Naive datetimes are treated as already being Taiwan local time.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=TAIWAN_TZ)
    return value.astimezone(TAIWAN_TZ)