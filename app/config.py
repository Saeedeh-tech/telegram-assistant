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
# gemini-2.5-* is closed to new API keys, so a Gemini 3 model is required.
# Send /diag in the chat to list the models your own key can use.
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.7-flash")
# Gemini 3 rejects a tool conversation unless each function call carries a
# thought_signature, and signatures only exist when the model actually thinks.
# Forcing a level above "minimal" keeps them present.
THINKING_LEVEL = os.environ.get("THINKING_LEVEL", "low")

CALENDAR_ID = _required("CALENDAR_ID")
SERVICE_ACCOUNT_INFO = json.loads(_required("SERVICE_ACCOUNT_JSON"))

TASKS_SECRET = _required("TASKS_SECRET")

TIMEZONE_NAME = os.environ.get("TIMEZONE", "Australia/Perth")
LOCAL_TZ = ZoneInfo(TIMEZONE_NAME)

def _optional_hour(name: str, default: str) -> int | None:
    """An hour 0-23, or None when set to off or left blank.

    Accepts the shapes people actually type: 7, 07, 7am, 2pm, 07:00.
    """
    raw = os.environ.get(name, default).strip().lower().replace(" ", "")
    if raw in ("", "off", "none", "false"):
        return None

    suffix = ""
    for marker in ("am", "pm"):
        if raw.endswith(marker):
            suffix, raw = marker, raw[: -len(marker)]
            break
    raw = raw.split(":")[0]

    try:
        hour = int(raw)
    except ValueError:
        raise ConfigError(
            f"{name} is set to '{os.environ.get(name)}'. It must be an hour "
            f"0-23 such as 7, or 'off' to disable."
        ) from None

    if suffix == "pm" and hour < 12:
        hour += 12
    elif suffix == "am" and hour == 12:
        hour = 0

    if not 0 <= hour <= 23:
        raise ConfigError(
            f"{name} is set to '{os.environ.get(name)}', which is not an hour "
            f"between 0 and 23."
        )
    return hour


MORNING_HOUR = _optional_hour("MORNING_HOUR", "7")

# Audio costs far more tokens than text, so long notes are refused politely.
MAX_VOICE_SECONDS = int(os.environ.get("MAX_VOICE_SECONDS", "120"))

# Extra calendars the bot may read but never write, such as a holiday feed.
EXTRA_CALENDAR_IDS = tuple(
    c.strip() for c in os.environ.get("EXTRA_CALENDAR_IDS", "").split(",") if c.strip()
)

ENABLE_WEB_SEARCH = os.environ.get("ENABLE_WEB_SEARCH", "true").strip().lower() not in (
    "false", "off", "0", "no"
)

DEFAULT_WEATHER_LOCATION = os.environ.get("DEFAULT_WEATHER_LOCATION", "Perth, Australia")

# Blank disables expense logging.
EXPENSES_SPREADSHEET_ID = os.environ.get("EXPENSES_SPREADSHEET_ID", "").strip()
EXPENSES_SHEET_NAME = os.environ.get("EXPENSES_SHEET_NAME", "Expenses")

MAX_TOOL_STEPS = int(os.environ.get("MAX_TOOL_STEPS", "6"))
MAX_HISTORY_TURNS = int(os.environ.get("MAX_HISTORY_TURNS", "20"))
DATABASE_URL = _required("DATABASE_URL")
