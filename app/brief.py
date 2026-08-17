"""Text for the scheduled messages.

Nothing here calls Gemini: the calendar, database and weather are read
directly, so scheduled jobs cost nothing against the AI quota.
"""
import logging
from datetime import timedelta

from . import config, store, timeparse
from .tools import calendar_tools, expenses, weather

log = logging.getLogger(__name__)


def _events_between(chat_id: int, start, end) -> list[dict]:
    result = calendar_tools.list_calendar_events(
        chat_id=chat_id,
        start=timeparse.to_iso(start),
        end=timeparse.to_iso(end),
        max_results=25,
    )
    if "error" in result:
        raise RuntimeError(result["error"])
    return result["events"]


def _midnight(offset_days: int = 0):
    base = timeparse.now_local().replace(hour=0, minute=0, second=0, microsecond=0)
    return base + timedelta(days=offset_days)


def _clock(event: dict) -> str:
    if event["all_day"]:
        return "all day"
    return timeparse.parse_local(event["start"]).strftime("%H:%M")


def _format_event(event: dict) -> str:
    where = f"  ({event['location']})" if event.get("location") else ""
    return f"  {_clock(event)}  {event['title']}{where}"


def _day_view(chat_id: int, offset_days: int, heading: str) -> str:
    """One day of events, plus that day's reminders."""
    start = _midnight(offset_days)
    end = start + timedelta(days=1)
    lines = [f"{heading} — {start.strftime('%A %d %B')}", ""]

    try:
        events = _events_between(chat_id, start, end)
        lines.append("Calendar:")
        lines.extend([_format_event(e) for e in events] or ["  nothing scheduled"])
    except Exception as exc:
        log.exception("Calendar unavailable for the brief")
        lines.append(f"Calendar: unavailable ({type(exc).__name__})")

    try:
        due = [
            r for r in store.list_pending_reminders(chat_id)
            if start <= timeparse.parse_local(r["due_at"].isoformat()) < end
        ]
        if due:
            lines += ["", "Reminders:"]
            lines += [
                f"  {timeparse.parse_local(r['due_at'].isoformat()).strftime('%H:%M')}  {r['text']}"
                for r in due
            ]
    except Exception as exc:
        log.exception("Reminders unavailable for the brief")
        lines.append(f"Reminders: unavailable ({type(exc).__name__})")

    return "\n".join(lines)


def build(chat_id: int) -> str:
    """Today. Used by /morning."""
    return _day_view(chat_id, 0, "Today")


def build_tomorrow(chat_id: int) -> str:
    return _day_view(chat_id, 1, "Tomorrow")


def build_week(chat_id: int) -> str:
    start = _midnight(1)
    lines = ["The week ahead", ""]
    try:
        events = _events_between(chat_id, start, start + timedelta(days=7))
    except Exception as exc:
        return "\n".join(lines + [f"Calendar unavailable ({type(exc).__name__})"])

    if not events:
        return "\n".join(lines + ["  nothing scheduled"])

    current_day = None
    for event in events:
        day = (event["start"] or "")[:10]
        if day != current_day:
            current_day = day
            lines += ["", timeparse.parse_local(f"{day}T00:00:00").strftime("%A %d %B")]
        lines.append(_format_event(event))
    return "\n".join(lines)


def build_last_month(chat_id: int) -> str | None:
    """Last month's spending. None when expense logging is switched off."""
    if not config.EXPENSES_SPREADSHEET_ID:
        return None
    last_month = (timeparse.now_local().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")

    summary = expenses.expense_summary(chat_id=chat_id, month=last_month)
    if "error" in summary:
        return f"Spending for {last_month}: unavailable ({summary['error']})"
    if not summary["entries"]:
        return f"Spending for {last_month}: nothing logged."

    lines = [f"Spending for {last_month}", "", f"Total: {summary['total']}", ""]
    lines += [f"  {name}: {amount}" for name, amount in summary["by_category"].items()]
    return "\n".join(lines)


def rain_warning(chat_id: int) -> str | None:
    """A warning only when rain is likely. None means stay quiet."""
    forecast = weather.get_weather(chat_id=chat_id, days=1)
    if "error" in forecast:
        log.warning("Rain check failed: %s", forecast["error"])
        return None

    days = forecast.get("forecast") or []
    if not days:
        return None
    today = days[0]
    chance = today.get("rain_chance_percent") or 0
    if chance < config.RAIN_ALERT_PERCENT:
        return None

    return (
        f"Rain likely today in {forecast['location']}: {chance}% chance, "
        f"about {today.get('rain_mm', 0)} mm. {today['condition'].capitalize()}, "
        f"{today['low_c']} to {today['high_c']}C. Take an umbrella."
    )
