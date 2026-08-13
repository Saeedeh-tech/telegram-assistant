"""Local time helpers shared by the calendar and reminder tools."""
from datetime import datetime, timedelta

from . import config

DEFAULT_EVENT_MINUTES = 60


def now_local() -> datetime:
    return datetime.now(config.LOCAL_TZ)


def parse_local(value: str) -> datetime:
    """Parse an ISO 8601 string, treating a missing offset as local time."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Expected an ISO 8601 datetime string")
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"Could not read '{value}' as a datetime") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=config.LOCAL_TZ)
    return parsed.astimezone(config.LOCAL_TZ)


def resolve_end(start: datetime, end_value: str | None) -> datetime:
    """Fall back to a one hour event and reject end times before the start."""
    if not end_value:
        return start + timedelta(minutes=DEFAULT_EVENT_MINUTES)
    end = parse_local(end_value)
    if end <= start:
        raise ValueError("End time must be after the start time")
    return end


def to_iso(value: datetime) -> str:
    return value.astimezone(config.LOCAL_TZ).isoformat()


def to_text(value: datetime) -> str:
    return value.astimezone(config.LOCAL_TZ).strftime("%a %d %b %Y, %H:%M")
