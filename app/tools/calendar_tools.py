"""Google Calendar tools.

Authentication uses a service account that the user has shared their calendar
with, which avoids an interactive OAuth consent flow on a headless service.
"""
import logging

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .. import config, timeparse
from . import register

log = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
MAX_LIST_RESULTS = 25
_service = None


def _calendar():
    global _service
    if _service is None:
        credentials = service_account.Credentials.from_service_account_info(
            config.SERVICE_ACCOUNT_INFO, scopes=SCOPES
        )
        _service = build("calendar", "v3", credentials=credentials, cache_discovery=False)
    return _service


def _describe(event: dict) -> dict:
    start = event.get("start", {})
    end = event.get("end", {})
    return {
        "id": event.get("id"),
        "title": event.get("summary", "(no title)"),
        "start": start.get("dateTime") or start.get("date"),
        "end": end.get("dateTime") or end.get("date"),
        "location": event.get("location"),
        "all_day": "date" in start,
    }


def _explain(error: HttpError) -> str:
    if error.resp.status == 404:
        return "Calendar not found. Check CALENDAR_ID and that it is shared with the service account."
    if error.resp.status == 403:
        return "Permission denied. The service account needs 'Make changes to events'."
    return f"Calendar API error {error.resp.status}"


@register(
    name="create_calendar_event",
    description=(
        "Create an event on the user's calendar. Times must be ISO 8601 in the "
        "user's local timezone, for example 2026-08-20T14:30:00."
    ),
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Short event title"},
            "start": {"type": "string", "description": "ISO 8601 start datetime"},
            "end": {"type": "string", "description": "ISO 8601 end datetime; defaults to one hour"},
            "description": {"type": "string"},
            "location": {"type": "string"},
        },
        "required": ["title", "start"],
    },
)
def create_calendar_event(
    chat_id: int,
    title: str,
    start: str,
    end: str | None = None,
    description: str | None = None,
    location: str | None = None,
) -> dict:
    if not title.strip():
        raise ValueError("Event title cannot be empty")
    starts_at = timeparse.parse_local(start)
    ends_at = timeparse.resolve_end(starts_at, end)

    body = {
        "summary": title.strip(),
        "start": {"dateTime": timeparse.to_iso(starts_at), "timeZone": config.TIMEZONE_NAME},
        "end": {"dateTime": timeparse.to_iso(ends_at), "timeZone": config.TIMEZONE_NAME},
    }
    if description:
        body["description"] = description
    if location:
        body["location"] = location

    try:
        created = _calendar().events().insert(calendarId=config.CALENDAR_ID, body=body).execute()
    except HttpError as exc:
        return {"error": _explain(exc)}

    return {
        "created": True,
        "event": _describe(created),
        "human_time": timeparse.to_text(starts_at),
    }


@register(
    name="list_calendar_events",
    description=(
        "List calendar events in a time range. Both bounds are ISO 8601 local "
        "datetimes. Defaults to the next seven days."
    ),
    parameters={
        "type": "object",
        "properties": {
            "start": {"type": "string", "description": "ISO 8601 range start"},
            "end": {"type": "string", "description": "ISO 8601 range end"},
            "max_results": {"type": "integer", "description": "1 to 25"},
        },
        "required": [],
    },
)
def list_calendar_events(
    chat_id: int,
    start: str | None = None,
    end: str | None = None,
    max_results: int = 10,
) -> dict:
    from datetime import timedelta

    range_start = timeparse.parse_local(start) if start else timeparse.now_local()
    range_end = timeparse.parse_local(end) if end else range_start + timedelta(days=7)
    if range_end <= range_start:
        raise ValueError("Range end must be after range start")

    limit = max(1, min(int(max_results), MAX_LIST_RESULTS))
    try:
        response = (
            _calendar()
            .events()
            .list(
                calendarId=config.CALENDAR_ID,
                timeMin=timeparse.to_iso(range_start),
                timeMax=timeparse.to_iso(range_end),
                singleEvents=True,
                orderBy="startTime",
                maxResults=limit,
            )
            .execute()
        )
    except HttpError as exc:
        return {"error": _explain(exc)}

    events = [_describe(item) for item in response.get("items", [])]
    return {"count": len(events), "events": events}


@register(
    name="update_calendar_event",
    description=(
        "Change an existing event. Get its id from list_calendar_events first. "
        "Only the fields you pass are changed; the rest stay as they are."
    ),
    parameters={
        "type": "object",
        "properties": {
            "event_id": {"type": "string", "description": "Event id from list_calendar_events"},
            "title": {"type": "string"},
            "start": {"type": "string", "description": "New ISO 8601 start"},
            "end": {"type": "string", "description": "New ISO 8601 end"},
            "location": {"type": "string"},
            "description": {"type": "string"},
        },
        "required": ["event_id"],
    },
)
def update_calendar_event(
    chat_id: int,
    event_id: str,
    title: str | None = None,
    start: str | None = None,
    end: str | None = None,
    location: str | None = None,
    description: str | None = None,
) -> dict:
    if not event_id.strip():
        raise ValueError("event_id cannot be empty")

    patch: dict = {}
    if title and title.strip():
        patch["summary"] = title.strip()
    if location is not None:
        patch["location"] = location
    if description is not None:
        patch["description"] = description

    # Moving only the start would leave a backwards or oddly long event, so the
    # original duration is kept unless a new end is given.
    if start:
        starts_at = timeparse.parse_local(start)
        patch["start"] = {"dateTime": timeparse.to_iso(starts_at), "timeZone": config.TIMEZONE_NAME}
        if end:
            ends_at = timeparse.resolve_end(starts_at, end)
        else:
            try:
                current = _calendar().events().get(calendarId=config.CALENDAR_ID, eventId=event_id).execute()
                old_start = timeparse.parse_local(current["start"]["dateTime"])
                old_end = timeparse.parse_local(current["end"]["dateTime"])
                ends_at = starts_at + (old_end - old_start)
            except (HttpError, KeyError, ValueError):
                ends_at = timeparse.resolve_end(starts_at, None)
        patch["end"] = {"dateTime": timeparse.to_iso(ends_at), "timeZone": config.TIMEZONE_NAME}
    elif end:
        patch["end"] = {
            "dateTime": timeparse.to_iso(timeparse.parse_local(end)),
            "timeZone": config.TIMEZONE_NAME,
        }

    if not patch:
        raise ValueError("Nothing to change. Pass a title, time, location or description.")

    try:
        updated = (
            _calendar()
            .events()
            .patch(calendarId=config.CALENDAR_ID, eventId=event_id, body=patch)
            .execute()
        )
    except HttpError as exc:
        if exc.resp.status in (404, 410):
            return {"error": "That event no longer exists. List events again to get a current id."}
        return {"error": _explain(exc)}

    return {"updated": True, "event": _describe(updated)}


@register(
    name="delete_calendar_event",
    description=(
        "Delete an event. Get its id from list_calendar_events first. Confirm "
        "with the user which event before calling this."
    ),
    parameters={
        "type": "object",
        "properties": {"event_id": {"type": "string"}},
        "required": ["event_id"],
    },
)
def delete_calendar_event(chat_id: int, event_id: str) -> dict:
    if not event_id.strip():
        raise ValueError("event_id cannot be empty")
    try:
        _calendar().events().delete(calendarId=config.CALENDAR_ID, eventId=event_id).execute()
    except HttpError as exc:
        if exc.resp.status in (404, 410):
            return {"deleted": False, "error": "That event was already gone."}
        return {"error": _explain(exc)}
    return {"deleted": True}
