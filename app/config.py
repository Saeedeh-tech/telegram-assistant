"""Configuration loaded from environment variables."""
import json
import os
from zoneinfo import ZoneInfo


class ConfigError(RuntimeError):
    """Raised at startup when a required setting is missing or malformed."""


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def _int_set(name: str) -> frozenset[int]:
    raw = _required(name)
    try:
        return frozenset(int(part) for part in raw.split(",") if part.strip())
    except ValueError as exc:
        raise ConfigError(f"{name} must be comma-separated integers") from exc


TELEGRAM_BOT_TOKEN = _required("TELEGRAM_BOT_TOKEN")
TELEGRAM_WEBHOOK_SECRET = _required("TELEGRAM_WEBHOOK_SECRET")
ALLOWED_TELEGRAM_USER_IDS = _int_set("ALLOWED_TELEGRAM_USER_IDS")

GEMINI_API_KEY = _required("GEMINI_API_KEY")
# Free tier as of Aug 2026. Fallbacks if this one changes: gemini-3.6-flash,
# gemini-3.5-flash-lite, gemini-2.5-flash. Check the pricing page for "Free Tier".
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")

CALENDAR_ID = _required("CALENDAR_ID")
SERVICE_ACCOUNT_INFO = json.loads(_required("SERVICE_ACCOUNT_JSON"))

TASKS_SECRET = _required("TASKS_SECRET")

TIMEZONE_NAME = os.environ.get("TIMEZONE", "Australia/Perth")
LOCAL_TZ = ZoneInfo(TIMEZONE_NAME)

MAX_TOOL_STEPS = int(os.environ.get("MAX_TOOL_STEPS", "6"))
MAX_HISTORY_TURNS = int(os.environ.get("MAX_HISTORY_TURNS", "20"))
DATABASE_URL = _required("DATABASE_URL")
