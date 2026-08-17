"""Gemini agent loop: turn a chat message into tool calls and a reply."""
import logging
import time

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from . import config, store, timeparse, tools

log = logging.getLogger(__name__)

RETRY_DELAYS_SECONDS = (1, 2, 4)
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
FALLBACK_REPLY = "Sorry, I could not finish that. Please try again."

_client: genai.Client | None = None


def gemini() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


def _system_instruction() -> str:
    return (
        "You are a personal assistant reachable through Telegram. "
        f"The user's timezone is {config.TIMEZONE_NAME}. "
        f"The current local time is {timeparse.to_iso(timeparse.now_local())}. "
        "Resolve relative times such as 'tomorrow at 3pm' against that time and "
        "always pass ISO 8601 local datetimes to tools.\n\n"
        "Use tools when the user asks you to do something. Never claim an action "
        "succeeded unless the tool result says so. Before sending a message to "
        "another person, show the user the exact wording and wait for them to "
        "agree. Reply in plain text without Markdown formatting, and keep replies "
        "short, using simple words and short sentences."
    )


def _tool_groups(with_search: bool) -> list[types.Tool]:
    groups = [types.Tool(function_declarations=tools.function_declarations())]
    if with_search:
        groups.append(types.Tool(google_search=types.GoogleSearch()))
    return groups


def _generation_config(with_search: bool = True) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        system_instruction=_system_instruction(),
        tools=_tool_groups(with_search),
        # Tools run here so results can be validated and logged.
        # maximum_remote_calls=None stops the SDK warning about an unused limit.
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            disable=True, maximum_remote_calls=None
        ),
        thinking_config=types.ThinkingConfig(thinking_level=config.THINKING_LEVEL),
    )


def _to_contents(history: list[dict]) -> list[types.Content]:
    return [
        types.Content(role=turn["role"], parts=[types.Part(text=turn["text"])])
        for turn in history
        if turn.get("text")
    ]


SIGNATURE_HINT = (
    "The model rejected the tool conversation (thought_signature). "
    "Try a different Gemini 3 flash model in GEMINI_MODEL. "
    "Send /diag to list the models your key can use."
)


# Some models refuse web search and custom tools in the same request. The first
# rejection turns search off for this process rather than failing the message.
_search_enabled = config.ENABLE_WEB_SEARCH
SEARCH_REJECTED = ("google_search", "search tool", "multiple tools", "tool_config")


def _search_was_rejected(exc: Exception) -> bool:
    message = str(exc).lower()
    return _search_enabled and any(term in message for term in SEARCH_REJECTED)


QUOTA_HINT = (
    "Gemini refused with a rate limit. This is usually the per-minute cap, so "
    "waiting a minute normally fixes it. Check ai.dev/rate-limit: if the daily "
    "number is near its limit instead, switch GEMINI_MODEL in Render, because "
    "each model has its own separate quota."
)


def _retry_after_seconds(exc) -> float | None:
    """Seconds Google asks us to wait, or None when it gives no such advice.

    A per-minute limit comes with RetryInfo. A daily limit does not, and
    retrying it only burns more of the quota, so the two must be told apart.
    """
    payload = getattr(exc, "details", None)
    if not isinstance(payload, dict):
        return None
    for detail in payload.get("error", {}).get("details", []):
        if str(detail.get("@type", "")).endswith("RetryInfo"):
            raw = str(detail.get("retryDelay", "")).rstrip("s")
            try:
                return float(raw)
            except ValueError:
                return None
    return None


def _generate(contents: list[types.Content]):
    """Call Gemini, retrying rate limits and transient server errors."""
    global _search_enabled
    last_error: Exception | None = None
    for delay in (0, *RETRY_DELAYS_SECONDS):
        if delay:
            time.sleep(delay)
        try:
            return gemini().models.generate_content(
                model=config.GEMINI_MODEL,
                contents=contents,
                config=_generation_config(_search_enabled),
            )
        except genai_errors.APIError as exc:
            if _search_was_rejected(exc):
                log.warning("Model rejected web search with custom tools; disabling search")
                _search_enabled = False
                continue
            if "thought_signature" in str(exc):
                raise RuntimeError(SIGNATURE_HINT) from exc

            if getattr(exc, "code", None) == 429:
                wait = _retry_after_seconds(exc)
                if wait is None:
                    raise RuntimeError(QUOTA_HINT) from exc
                log.warning("Rate limited, waiting %ss as instructed", wait)
                time.sleep(min(wait, 30))
                continue

            if getattr(exc, "code", None) not in RETRYABLE_STATUS:
                raise
            last_error = exc
            log.warning("Gemini call retryable error: %s", exc)
    raise RuntimeError("Gemini unavailable after retries") from last_error


def _signed_content(content: types.Content) -> types.Content:
    """Trim the model turn to the parts that can legally be sent back.

    Gemini 3 signs only the first function call when it asks for several at
    once, but then rejects the unsigned ones on the next request. Dropping them
    turns parallel calls into sequential ones: the model simply asks again.
    """
    kept, seen_call = [], False
    for part in content.parts or []:
        if part.function_call:
            if seen_call and not part.thought_signature:
                log.info("Deferring unsigned call %s to the next step", part.function_call.name)
                break
            seen_call = True
        kept.append(part)
    return types.Content(role=content.role or "model", parts=kept)


def _reply_text(response) -> str:
    if not response.candidates:
        return "I could not answer that one."
    parts = response.candidates[0].content.parts or []
    return "".join(part.text for part in parts if getattr(part, "text", None)).strip()


def _function_calls(response) -> list:
    if not response.candidates:
        return []
    parts = response.candidates[0].content.parts or []
    return [part.function_call for part in parts if getattr(part, "function_call", None)]


VOICE_NUDGE = "This is a voice message. Do what it asks."


def handle_message(
    chat_id: int, user_text: str, audio: tuple[bytes, str] | None = None
) -> str:
    """Run the tool loop for one message and return the reply text.

    `audio` is (bytes, mime_type). Gemini reads audio directly, so a voice note
    needs no separate transcription service.
    """
    contents = _to_contents(store.load_history(chat_id))

    parts = []
    if audio:
        data, mime_type = audio
        parts.append(types.Part.from_bytes(data=data, mime_type=mime_type))
        parts.append(types.Part(text=user_text.strip() or VOICE_NUDGE))
    else:
        parts.append(types.Part(text=user_text))
    contents.append(types.Content(role="user", parts=parts))

    # Audio is not replayed on later turns, so history records a stand-in.
    history_text = user_text.strip() or ("[voice message]" if audio else user_text)

    reply = FALLBACK_REPLY
    for step in range(config.MAX_TOOL_STEPS):
        response = _generate(contents)
        calls = _function_calls(response)
        if not calls:
            reply = _reply_text(response) or FALLBACK_REPLY
            break

        model_turn = _signed_content(response.candidates[0].content)
        contents.append(model_turn)
        calls = [p.function_call for p in model_turn.parts if p.function_call]
        results = []
        for call in calls:
            arguments = dict(call.args or {})
            log.info("Step %d calling tool %s", step + 1, call.name)
            result = tools.run(call.name, chat_id, arguments)
            results.append(
                types.Part.from_function_response(name=call.name, response=result)
            )
        contents.append(types.Content(role="user", parts=results))
    else:
        log.warning("Tool loop hit the %d step limit", config.MAX_TOOL_STEPS)
        reply = "That needed too many steps. Could you break it into smaller requests?"

    store.append_history(chat_id, history_text, reply)
    return reply
