"""Request authentication for the webhook and the scheduler endpoint."""
import hmac
import logging

from . import config

log = logging.getLogger(__name__)

TELEGRAM_SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"
TASKS_SECRET_HEADER = "X-Tasks-Secret"


def _matches(supplied: str | None, expected: str) -> bool:
    """Constant-time compare that tolerates a missing header."""
    return bool(supplied) and hmac.compare_digest(supplied, expected)


def is_telegram_request(headers) -> bool:
    return _matches(headers.get(TELEGRAM_SECRET_HEADER), config.TELEGRAM_WEBHOOK_SECRET)


def is_scheduler_request(headers) -> bool:
    return _matches(headers.get(TASKS_SECRET_HEADER), config.TASKS_SECRET)


def is_allowed_user(user_id: int | None) -> bool:
    allowed = user_id in config.ALLOWED_TELEGRAM_USER_IDS
    if not allowed:
        log.warning("Rejected message from unlisted Telegram user %s", user_id)
    return allowed
