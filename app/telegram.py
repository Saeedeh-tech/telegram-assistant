"""Thin Telegram Bot API client."""
import logging
import time

import requests

from . import config

log = logging.getLogger(__name__)

API_ROOT = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"
MAX_MESSAGE_CHARS = 4096
RETRY_DELAYS_SECONDS = (1, 2, 4)
REQUEST_TIMEOUT_SECONDS = 20


class TelegramError(RuntimeError):
    pass


def _call(method: str, payload: dict) -> dict:
    """POST to the Bot API, retrying transient failures and honouring 429."""
    last_error: Exception | None = None
    for attempt, delay in enumerate((0, *RETRY_DELAYS_SECONDS)):
        if delay:
            time.sleep(delay)
        try:
            response = requests.post(
                f"{API_ROOT}/{method}", json=payload, timeout=REQUEST_TIMEOUT_SECONDS
            )
            if response.status_code == 429:
                retry_after = response.json().get("parameters", {}).get("retry_after", 5)
                time.sleep(min(retry_after, 30))
                last_error = TelegramError(f"{method} rate limited")
                continue
            response.raise_for_status()
            return response.json().get("result", {})
        except requests.RequestException as exc:
            last_error = exc
            log.warning("%s failed (attempt %d): %s", method, attempt + 1, exc)
    raise TelegramError(f"{method} failed after retries") from last_error


def _split(text: str) -> list[str]:
    """Break long text on line boundaries so Telegram accepts each chunk."""
    if len(text) <= MAX_MESSAGE_CHARS:
        return [text]
    chunks, current = [], ""
    for line in text.splitlines(keepends=True):
        while len(line) > MAX_MESSAGE_CHARS:
            chunks.append(line[:MAX_MESSAGE_CHARS])
            line = line[MAX_MESSAGE_CHARS:]
        if len(current) + len(line) > MAX_MESSAGE_CHARS:
            chunks.append(current)
            current = ""
        current += line
    if current:
        chunks.append(current)
    return chunks


def send_message(chat_id: int, text: str) -> None:
    if not text.strip():
        return
    for chunk in _split(text):
        _call("sendMessage", {"chat_id": chat_id, "text": chunk})


def send_typing(chat_id: int) -> None:
    """Best effort indicator; never block the reply on it."""
    try:
        _call("sendChatAction", {"chat_id": chat_id, "action": "typing"})
    except TelegramError:
        log.debug("Typing indicator failed for chat %s", chat_id)
