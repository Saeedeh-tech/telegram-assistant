"""Daily brief: what is on today.

Sent by /morning on demand, and once each morning by the existing reminder
sweep, so no second scheduled job is needed.
"""
import logging
from datetime import timedelta

from . import config, store, telegram, timeparse
from .tools import calendar_tools

log = logging.getLogger(__name__)


def _todays_events(chat_id: int) -> list[dict]:
    start = timeparse.now_local().replace(hour=0, minute=0, second=0, microsecond=0)
    result = calendar_tools.list_calendar_events(
        chat_id=chat_id,
        start=timeparse.to_iso(start),
        end=timeparse.to_iso(start + timedelta(days=1)),
        max_results=25,
    )
    if "error" in result:
        raise RuntimeError(result["error"])
    return result["events"]


def _format_event(event: dict) -> str:
    if event["all_day"]:
        return f"  all day  {event['title']}"
    when = timeparse.parse_local(event["start"]).strftime("%H:%M")
    where = f"  ({event['location']})" if event.get("location") else ""
    return f"  {when}  {event['title']}{where}"


def build(chat_id: int) -> str:
    """Compose the brief. Never raises: a broken part is reported in place."""
    today = timeparse.now_local()
    lines = [today.strftime("%A %d %B"), ""]

    try:
        events = _todays_events(chat_id)
        lines.append("Calendar:")
        lines.extend([_format_event(e) for e in events] or ["  nothing scheduled"])
    except Exception as exc:
        log.exception("Could not read the calendar for the brief")
        lines.append(f"Calendar: unavailable ({type(exc).__name__})")

    try:
        end_of_day = today.replace(hour=23, minute=59, second=59)
        due = [
            r for r in store.list_pending_reminders(chat_id)
            if timeparse.parse_local(r["due_at"].isoformat()) <= end_of_day
        ]
        if due:
            lines += ["", "Reminders today:"]
            lines += [f"  {timeparse.parse_local(r['due_at'].isoformat()).strftime('%H:%M')}  {r['text']}" for r in due]
    except Exception as exc:
        log.exception("Could not read reminders for the brief")
        lines.append(f"Reminders: unavailable ({type(exc).__name__})")

    return "\n".join(lines)


def send_if_due() -> int:
    """Send the brief once, on or after the configured hour. Returns how many sent.

    Called from the reminder sweep. The database claim makes this safe to call
    every 30 minutes: only the first call of the day sends anything.
    """
    if config.MORNING_HOUR is None:
        return 0
    if timeparse.now_local().hour < config.MORNING_HOUR:
        return 0
    if not store.claim_daily_brief(timeparse.now_local().date()):
        return 0

    sent = 0
    for chat_id in config.ALLOWED_TELEGRAM_USER_IDS:
        try:
            telegram.send_message(chat_id, build(chat_id))
            sent += 1
        except telegram.TelegramError:
            log.exception("Could not deliver the morning brief to %s", chat_id)
    return sent
