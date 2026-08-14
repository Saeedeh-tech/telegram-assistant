"""Self-checks for the /diag command.

Each check returns a short line the user can act on, so a broken setup can be
diagnosed from the chat instead of from the server logs.
"""
import logging

from . import config, store

log = logging.getLogger(__name__)

OK = "OK"
FAILED = "FAILED"


def _short(error: Exception, limit: int = 160) -> str:
    text = str(error).replace("\n", " ").strip()
    return f"{type(error).__name__}: {text[:limit]}"


def check_database() -> str:
    try:
        return OK if store.check_connection() else f"{FAILED} — cannot reach the database"
    except Exception as exc:
        return f"{FAILED} — {_short(exc)}"


def check_gemini() -> str:
    """Smallest possible call, to prove the key and the model name both work."""
    from . import agent

    try:
        response = agent.gemini().models.generate_content(
            model=config.GEMINI_MODEL, contents="Reply with the single word: ready"
        )
        reply = (response.text or "").strip()
        return f"{OK} — model {config.GEMINI_MODEL} replied '{reply[:30]}'"
    except Exception as exc:
        return f"{FAILED} — {_short(exc)}"


def check_calendar() -> str:
    from .tools import calendar_tools

    try:
        result = calendar_tools.list_calendar_events(chat_id=0, max_results=1)
    except Exception as exc:
        return f"{FAILED} — {_short(exc)}"
    if "error" in result:
        return f"{FAILED} — {result['error']}"
    return f"{OK} — calendar {config.CALENDAR_ID} is readable"


def list_models(limit: int = 25) -> str:
    """Show which models this API key can actually use."""
    from . import agent

    try:
        names = []
        for model in agent.gemini().models.list():
            actions = getattr(model, "supported_actions", None) or []
            if actions and "generateContent" not in actions:
                continue
            names.append((model.name or "").removeprefix("models/"))
        flash = [n for n in names if "flash" in n and "image" not in n and "tts" not in n]
        return "Models your key can use:\n" + "\n".join(f"  {n}" for n in sorted(flash)[:limit])
    except Exception as exc:
        return f"{FAILED} — {_short(exc)}"


def check_contacts() -> str:
    from .tools import messaging

    return messaging.CONTACTS_STATUS


def run_all() -> str:
    lines = [
        "Self check:",
        "",
        f"Database:  {check_database()}",
        f"Gemini:    {check_gemini()}",
        f"Calendar:  {check_calendar()}",
        f"Contacts:  {check_contacts()}",
        "",
        f"Timezone:  {config.TIMEZONE_NAME}",
        "",
        list_models(),
    ]
    return "\n".join(lines)
