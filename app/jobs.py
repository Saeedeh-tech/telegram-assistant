"""Which scheduled messages are due right now.

Driven by the reminder sweep, so no extra cron job is needed. Each job claims
its slot in the database, which makes a 30-minute sweep safe: only the first
call after the chosen hour sends anything.
"""
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from . import brief, config, store, telegram

log = logging.getLogger(__name__)

SUNDAY = 6

# How late a job may still fire. Without this, a first deploy in the evening
# would send that morning's brief at 9pm. Wide enough to absorb a few missed
# sweeps, narrow enough that a stale message never arrives.
CATCHUP_HOURS = 3


@dataclass(frozen=True)
class Job:
    name: str
    hour: int | None
    on_date: Callable[[datetime], bool]
    compose: Callable[[int], str | None]


def _jobs() -> list[Job]:
    always = lambda _: True
    return [
        Job("morning", config.MORNING_HOUR, always, brief.build),
        Job("evening", config.EVENING_HOUR, always, brief.build_tomorrow),
        Job("rain", config.RAIN_ALERT_HOUR, always, brief.rain_warning),
        Job("weekly", config.WEEKLY_SUMMARY_HOUR,
            lambda now: now.weekday() == SUNDAY, brief.build_week),
        Job("monthly", config.MONTHLY_SUMMARY_HOUR,
            lambda now: now.day == 1, brief.build_last_month),
    ]


def _send(job: Job) -> int:
    sent = 0
    for chat_id in config.ALLOWED_TELEGRAM_USER_IDS:
        try:
            message = job.compose(chat_id)
        except Exception:
            log.exception("Could not build the %s message", job.name)
            continue
        # None means the job ran and decided there was nothing worth saying.
        if not message:
            continue
        try:
            telegram.send_message(chat_id, message)
            sent += 1
        except telegram.TelegramError:
            log.exception("Could not deliver the %s message to %s", job.name, chat_id)
    return sent


def run_due(now: datetime) -> dict[str, int]:
    """Send whatever is due. Returns a count per job that fired."""
    fired: dict[str, int] = {}
    for job in _jobs():
        if job.hour is None or not job.on_date(now):
            continue
        if not job.hour <= now.hour < job.hour + CATCHUP_HOURS:
            continue
        if not store.claim_job(job.name, now.date()):
            continue
        log.info("Running scheduled job %s", job.name)
        fired[job.name] = _send(job)
    return fired
