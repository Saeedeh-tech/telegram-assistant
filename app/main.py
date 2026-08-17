"""Flask entrypoint: Telegram webhook, reminder delivery, health check."""
import logging
import os

from flask import Flask, jsonify, request

from . import agent, brief, config, diagnostics, jobs, security, store, telegram, timeparse

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
    "/reset clears our conversation history.\n"
    "/diag checks that my services are working.\n"
    "/chatid shows the ID of this chat, for adding groups.\n"
    "/morning today, /tomorrow, /week ahead."
)


def _extract_message(update: dict) -> tuple[int, int, str, dict | None] | None:
    """Return (chat_id, user_id, text, voice), or None for updates we skip.

    `voice` covers both voice notes and forwarded audio; `text` carries any
    caption, which the user may use to add instructions to a recording.
    """
    message = update.get("message")
    if not isinstance(message, dict):
        return None
    chat_id = message.get("chat", {}).get("id")
    user_id = message.get("from", {}).get("id")
    if chat_id is None or user_id is None:
        return None

    text = (message.get("text") or message.get("caption") or "").strip()
    voice = message.get("voice") or message.get("audio")
    return chat_id, user_id, text, (voice if isinstance(voice, dict) else None)


def _transcribable(chat_id: int, voice: dict) -> tuple[bytes, str] | None:
    """Download a voice note, or explain why it cannot be used."""
    seconds = voice.get("duration", 0)
    if seconds > config.MAX_VOICE_SECONDS:
        telegram.send_message(
            chat_id,
            f"That recording is {seconds} seconds. Please keep voice messages "
            f"under {config.MAX_VOICE_SECONDS} seconds.",
        )
        return None
    file_id = voice.get("file_id")
    if not file_id:
        return None
    return telegram.download_file(file_id), voice.get("mime_type") or "audio/ogg"


def _handle_command(chat_id: int, text: str) -> bool:
    """Handle slash commands. Returns True when the message was a command."""
    command = text.split()[0].split("@")[0].lower()
    if command in ("/start", "/help"):
        telegram.send_message(chat_id, HELP_TEXT)
        return True
    if command == "/morning":
        telegram.send_message(chat_id, brief.build(chat_id))
        return True
    if command == "/tomorrow":
        telegram.send_message(chat_id, brief.build_tomorrow(chat_id))
        return True
    if command == "/week":
        telegram.send_message(chat_id, brief.build_week(chat_id))
        return True
    if command == "/chatid":
        # Group IDs are negative and cannot be looked up any other way while a
        # webhook is active, so the bot reports the id of wherever it is asked.
        telegram.send_message(chat_id, f"Chat ID: {chat_id}")
        return True
    if command == "/reset":
        store.clear_history(chat_id)
        telegram.send_message(chat_id, "History cleared.")
        return True
    if command == "/diag":
        telegram.send_message(chat_id, diagnostics.run_all())
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

    chat_id, user_id, text, voice = extracted
    if not security.is_allowed_user(user_id):
        return jsonify(status="unauthorised"), 200

    # Everything below is wrapped: Telegram retries on any non-2xx reply, so a
    # failure here must still answer 200 rather than trigger a retry loop.
    try:
        if text.startswith("/") and _handle_command(chat_id, text):
            return jsonify(status="command"), 200

        audio = None
        if voice:
            telegram.send_typing(chat_id)
            audio = _transcribable(chat_id, voice)
            if audio is None:
                return jsonify(status="voice rejected"), 200
        elif not text:
            telegram.send_message(chat_id, "I can read text and voice messages.")
            return jsonify(status="unsupported"), 200

        telegram.send_typing(chat_id)
        telegram.send_message(chat_id, agent.handle_message(chat_id, text, audio=audio))
    except Exception as exc:
        log.exception("Failed to handle update %s", update_id)
        # Single known user, so the real reason is more useful than a vague line.
        detail = str(exc).replace("\n", " ").strip()[:300]
        try:
            telegram.send_message(
                chat_id,
                f"Something went wrong on my side.\n\n{type(exc).__name__}: {detail}"
                "\n\nSend /diag to see which service is failing.",
            )
        except telegram.TelegramError:
            log.exception("Could not deliver the error notice")

    return jsonify(status="ok"), 200


@app.post("/tasks/due-reminders")
def due_reminders():
    """Called by Cloud Scheduler; delivers reminders that have come due."""
    if not security.is_scheduler_request(request.headers):
        return jsonify(error="forbidden"), 403

    store.purge_old_updates()
    fired = jobs.run_due(timeparse.now_local())
    delivered, failed = 0, 0
    for reminder in store.claim_due_reminders():
        try:
            telegram.send_message(reminder["chat_id"], f"Reminder: {reminder['text']}")
            delivered += 1
        except telegram.TelegramError:
            failed += 1
            log.exception("Could not deliver reminder %s", reminder["id"])

    return jsonify(delivered=delivered, failed=failed, jobs=fired), 200


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
