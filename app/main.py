"""Flask entrypoint: Telegram webhook, reminder delivery, health check."""
import logging
import os

from flask import Flask, jsonify, request

from . import agent, security, store, telegram

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
log = logging.getLogger(__name__)

app = Flask(__name__)

HELP_TEXT = (
    "I can help with your calendar, notes, reminders and Telegram messages.\n\n"
    "Try:\n"
    "  Book dentist Tuesday 9am\n"
    "  What is on this week?\n"
    "  Remind me to call mum at 6pm\n"
    "  Note: parking bay 42\n\n"
    "/reset clears our conversation history."
)


def _extract_message(update: dict) -> tuple[int, int, str] | None:
    """Return (chat_id, user_id, text), or None for updates we do not handle."""
    message = update.get("message")
    if not isinstance(message, dict):
        return None
    chat_id = message.get("chat", {}).get("id")
    user_id = message.get("from", {}).get("id")
    text = (message.get("text") or "").strip()
    if chat_id is None or user_id is None:
        return None
    return chat_id, user_id, text


def _handle_command(chat_id: int, text: str) -> bool:
    """Handle slash commands. Returns True when the message was a command."""
    command = text.split()[0].split("@")[0].lower()
    if command in ("/start", "/help"):
        telegram.send_message(chat_id, HELP_TEXT)
        return True
    if command == "/reset":
        store.clear_history(chat_id)
        telegram.send_message(chat_id, "History cleared.")
        return True
    return False


@app.post("/telegram/webhook")
def telegram_webhook():
    if not security.is_telegram_request(request.headers):
        return jsonify(error="forbidden"), 403

    update = request.get_json(silent=True) or {}
    update_id = update.get("update_id")

    # Telegram redelivers on timeout, so 200 is returned even on failure and
    # every update is processed at most once.
    if update_id is not None and not store.claim_update(update_id):
        return jsonify(status="duplicate"), 200

    extracted = _extract_message(update)
    if extracted is None:
        return jsonify(status="ignored"), 200

    chat_id, user_id, text = extracted
    if not security.is_allowed_user(user_id):
        return jsonify(status="unauthorised"), 200

    if not text:
        telegram.send_message(chat_id, "I can only read text messages for now.")
        return jsonify(status="unsupported"), 200

    try:
        if text.startswith("/") and _handle_command(chat_id, text):
            return jsonify(status="command"), 200
        telegram.send_typing(chat_id)
        telegram.send_message(chat_id, agent.handle_message(chat_id, text))
    except Exception:
        log.exception("Failed to handle update %s", update_id)
        try:
            telegram.send_message(chat_id, "Something went wrong on my side. Please try again.")
        except telegram.TelegramError:
            log.exception("Could not deliver the error notice")

    return jsonify(status="ok"), 200


@app.post("/tasks/due-reminders")
def due_reminders():
    """Called by Cloud Scheduler; delivers reminders that have come due."""
    if not security.is_scheduler_request(request.headers):
        return jsonify(error="forbidden"), 403

    store.purge_old_updates()
    delivered, failed = 0, 0
    for reminder in store.claim_due_reminders():
        try:
            telegram.send_message(reminder["chat_id"], f"Reminder: {reminder['text']}")
            delivered += 1
        except telegram.TelegramError:
            failed += 1
            log.exception("Could not deliver reminder %s", reminder["id"])

    return jsonify(delivered=delivered, failed=failed), 200


@app.get("/healthz")
def healthz():
    """Shallow by default.

    Render pings this endpoint often. Touching the database here would keep the
    database awake all month and use up the free compute allowance, so the deep
    check is opt in: /healthz?deep=1
    """
    if request.args.get("deep") != "1":
        return jsonify(status="ok"), 200
    if not store.check_connection():
        return jsonify(status="ok", database="unreachable"), 503
    return jsonify(status="ok", database="ok"), 200
