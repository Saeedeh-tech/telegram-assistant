"""Send Telegram messages to other chats.

A bot can only message chats it already shares with the recipient, so targets are
kept in an explicit contacts map. This doubles as a safety limit: the model can
only reach names the user has approved.
"""
import json
import logging
import os

from .. import telegram
from . import register

log = logging.getLogger(__name__)

# {"alex": 123456789, "team standup": -1001234567890}
CONTACTS: dict[str, int] = {
    name.casefold().strip(): int(chat_id)
    for name, chat_id in json.loads(os.environ.get("TELEGRAM_CONTACTS", "{}")).items()
}


@register(
    name="list_message_contacts",
    description="List the names this bot is allowed to send Telegram messages to.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def list_message_contacts(chat_id: int) -> dict:
    return {"contacts": sorted(CONTACTS)}


@register(
    name="send_telegram_message",
    description=(
        "Send a Telegram message to a known contact. Confirm the recipient and "
        "wording with the user before calling this."
    ),
    parameters={
        "type": "object",
        "properties": {
            "contact": {"type": "string", "description": "Contact name from list_message_contacts"},
            "text": {"type": "string", "description": "Message body to send"},
        },
        "required": ["contact", "text"],
    },
)
def send_telegram_message(chat_id: int, contact: str, text: str) -> dict:
    if not text.strip():
        raise ValueError("Message text cannot be empty")

    target = CONTACTS.get(contact.casefold().strip())
    if target is None:
        return {
            "error": f"'{contact}' is not a known contact",
            "known_contacts": sorted(CONTACTS),
        }

    try:
        telegram.send_message(target, text)
    except telegram.TelegramError as exc:
        return {"error": f"Could not deliver the message: {exc}"}

    log.info("Sent message to contact %s", contact)
    return {"sent": True, "contact": contact}
