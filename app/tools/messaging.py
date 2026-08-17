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

def _load_contacts() -> tuple[dict[str, int], str]:
    """Parse TELEGRAM_CONTACTS, returning the contacts and a status line.

    A bad value must not stop the whole bot from starting, so problems are
    reported through /diag instead of raising at import time.
    """
    raw = os.environ.get("TELEGRAM_CONTACTS", "").strip()
    if not raw or raw == "{}":
        return {}, "none configured"

    # Render sometimes keeps the surrounding quotes, giving a JSON string
    # that itself contains JSON.
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, str):
            parsed = json.loads(parsed)
    except json.JSONDecodeError as exc:
        return {}, f"not valid JSON ({exc.msg}). Expected {{\"name\":123456789}}"

    if not isinstance(parsed, dict):
        return {}, f"expected an object, got {type(parsed).__name__}"

    contacts, bad = {}, []
    for name, chat_id in parsed.items():
        try:
            # Normalise unicode dashes, which copy-paste often introduces.
            contacts[name.casefold().strip()] = int(str(chat_id).strip().replace("\u2212", "-").replace("\u2013", "-"))
        except (ValueError, TypeError):
            bad.append(f"{name}={chat_id!r}")

    status = f"{len(contacts)} loaded: {', '.join(sorted(contacts)) or 'none'}"
    if bad:
        status += f" | not a number: {', '.join(bad)}"
    return contacts, status


CONTACTS, CONTACTS_STATUS = _load_contacts()
log.info("Telegram contacts: %s", CONTACTS_STATUS)


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
        reason = str(exc)
        if "chat not found" in reason.lower():
            return {
                "error": (
                    f"{contact} has never messaged this bot, so Telegram will not "
                    "let it write to them. Ask them to open the bot and press Start, "
                    "then try again."
                )
            }
        if "blocked" in reason.lower():
            return {"error": f"{contact} has blocked this bot."}
        return {"error": f"Could not deliver the message: {reason}"}

    log.info("Sent message to contact %s", contact)
    return {"sent": True, "contact": contact}
