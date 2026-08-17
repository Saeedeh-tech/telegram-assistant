"""Notes and reminders.

Reminders are delivered as Telegram messages by the scheduler endpoint rather
than written to iOS Reminders, which no server can reach.
"""
from .. import store, timeparse
from . import register

MAX_NOTE_CHARS = 2000


@register(
    name="save_note",
    description="Save a short note for the user to look up later.",
    parameters={
        "type": "object",
        "properties": {"text": {"type": "string", "description": "Note content"}},
        "required": ["text"],
    },
)
def save_note(chat_id: int, text: str) -> dict:
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("Note text cannot be empty")
    if len(cleaned) > MAX_NOTE_CHARS:
        raise ValueError(f"Note is too long; keep it under {MAX_NOTE_CHARS} characters")
    return {"saved": True, "note_id": store.add_note(chat_id, cleaned)}


@register(
    name="search_notes",
    description="Find saved notes containing a word or phrase. Empty query returns recent notes.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Word or phrase to look for"},
            "limit": {"type": "integer", "description": "1 to 20"},
        },
        "required": [],
    },
)
def search_notes(chat_id: int, query: str = "", limit: int = 10) -> dict:
    capped = max(1, min(int(limit), 20))
    results = store.search_notes(chat_id, query, capped)
    return {
        "count": len(results),
        "notes": [
            {
                "id": note["id"],
                "text": note["text"],
                "created": timeparse.to_text(note["created_at"]),
            }
            for note in results
        ],
    }


@register(
    name="delete_note",
    description="Delete a saved note by its id. Get the id from search_notes first.",
    parameters={
        "type": "object",
        "properties": {"note_id": {"type": "string"}},
        "required": ["note_id"],
    },
)
def delete_note(chat_id: int, note_id: str) -> dict:
    if store.delete_note(note_id, chat_id):
        return {"deleted": True}
    return {"error": "No note with that id belongs to this chat"}


@register(
    name="set_reminder",
    description=(
        "Schedule a reminder message. `due_at` is an ISO 8601 local datetime and "
        "must be in the future. Set `repeat` for something that happens again, "
        "such as bin night or rent."
    ),
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "What to remind the user about"},
            "due_at": {"type": "string", "description": "ISO 8601 local datetime of the first one"},
            "repeat": {
                "type": "string",
                "enum": list(timeparse.REPEAT_RULES),
                "description": "How often it repeats. Leave out for a one-off.",
            },
        },
        "required": ["text", "due_at"],
    },
)
def set_reminder(chat_id: int, text: str, due_at: str, repeat: str | None = None) -> dict:
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("Reminder text cannot be empty")
    due = timeparse.parse_local(due_at)
    if due <= timeparse.now_local():
        raise ValueError("Reminder time must be in the future")

    rule = (repeat or "").strip().lower() or None
    if rule and rule not in timeparse.REPEAT_RULES:
        raise ValueError(f"repeat must be one of: {', '.join(timeparse.REPEAT_RULES)}")

    reminder_id = store.add_reminder(chat_id, cleaned, due, rule)
    return {
        "scheduled": True,
        "reminder_id": reminder_id,
        "due": timeparse.to_text(due),
        "repeats": rule or "once",
    }


@register(
    name="cancel_reminder",
    description="Cancel a pending reminder. Get its id from list_reminders first.",
    parameters={
        "type": "object",
        "properties": {"reminder_id": {"type": "string"}},
        "required": ["reminder_id"],
    },
)
def cancel_reminder(chat_id: int, reminder_id: str) -> dict:
    if store.cancel_reminder(reminder_id, chat_id):
        return {"cancelled": True}
    return {"error": "No pending reminder with that id belongs to this chat"}


@register(
    name="reschedule_reminder",
    description=(
        "Move a pending reminder to a new time. Get its id from list_reminders "
        "first. `due_at` is an ISO 8601 local datetime in the future."
    ),
    parameters={
        "type": "object",
        "properties": {
            "reminder_id": {"type": "string"},
            "due_at": {"type": "string", "description": "New ISO 8601 local datetime"},
        },
        "required": ["reminder_id", "due_at"],
    },
)
def reschedule_reminder(chat_id: int, reminder_id: str, due_at: str) -> dict:
    due = timeparse.parse_local(due_at)
    if due <= timeparse.now_local():
        raise ValueError("The new time must be in the future")
    if store.reschedule_reminder(reminder_id, chat_id, due):
        return {"rescheduled": True, "due": timeparse.to_text(due)}
    return {"error": "No pending reminder with that id belongs to this chat"}


@register(
    name="list_reminders",
    description="List reminders that have not been delivered yet.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def list_reminders(chat_id: int) -> dict:
    pending = store.list_pending_reminders(chat_id)
    return {
        "count": len(pending),
        "reminders": [
            {
                "id": item["id"],
                "text": item["text"],
                "due": timeparse.to_text(item["due_at"]),
                "repeats": item.get("repeat_rule") or "once",
            }
            for item in pending
        ],
    }
