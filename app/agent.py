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


def _gemini() -> genai.Client:
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


def _generation_config() -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        system_instruction=_system_instruction(),
        tools=[types.Tool(function_declarations=tools.function_declarations())],
        # Tools are executed here so results can be validated and logged.
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )


def _to_contents(history: list[dict]) -> list[types.Content]:
    return [
        types.Content(role=turn["role"], parts=[types.Part(text=turn["text"])])
        for turn in history
        if turn.get("text")
    ]


def _generate(contents: list[types.Content]):
    """Call Gemini, retrying rate limits and transient server errors."""
    last_error: Exception | None = None
    for delay in (0, *RETRY_DELAYS_SECONDS):
        if delay:
            time.sleep(delay)
        try:
            return _gemini().models.generate_content(
                model=config.GEMINI_MODEL, contents=contents, config=_generation_config()
            )
        except genai_errors.APIError as exc:
            if getattr(exc, "code", None) not in RETRYABLE_STATUS:
                raise
            last_error = exc
            log.warning("Gemini call retryable error: %s", exc)
    raise RuntimeError("Gemini unavailable after retries") from last_error


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


def handle_message(chat_id: int, user_text: str) -> str:
    """Run the tool loop for one user message and return the reply text."""
    contents = _to_contents(store.load_history(chat_id))
    contents.append(types.Content(role="user", parts=[types.Part(text=user_text)]))

    reply = FALLBACK_REPLY
    for step in range(config.MAX_TOOL_STEPS):
        response = _generate(contents)
        calls = _function_calls(response)
        if not calls:
            reply = _reply_text(response) or FALLBACK_REPLY
            break

        contents.append(response.candidates[0].content)
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

    store.append_history(chat_id, user_text, reply)
    return reply
