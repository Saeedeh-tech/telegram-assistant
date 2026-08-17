"""Google API clients built from the one service account.

Calendar and Sheets both need credentials, so the building and caching lives
here rather than being repeated in each tool module.
"""
import logging
import threading

from google.oauth2 import service_account
from googleapiclient.discovery import build

from . import config

log = logging.getLogger(__name__)

CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events"
SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"

_services: dict[tuple[str, str], object] = {}
_lock = threading.Lock()


def service(api: str, version: str, scope: str):
    """Return a cached Google API client, building it on first use."""
    key = (api, version)
    with _lock:
        if key not in _services:
            credentials = service_account.Credentials.from_service_account_info(
                config.SERVICE_ACCOUNT_INFO, scopes=[scope]
            )
            _services[key] = build(api, version, credentials=credentials, cache_discovery=False)
            log.info("Built Google %s %s client", api, version)
        return _services[key]


def calendar():
    return service("calendar", "v3", CALENDAR_SCOPE)


def sheets():
    return service("sheets", "v4", SHEETS_SCOPE)
