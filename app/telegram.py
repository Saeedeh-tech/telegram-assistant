"""Thin Telegram Bot API client."""
import logging
import time

import requests

from . import config

log = logging.getLogger(__name__)

API_ROOT = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"
FILE_ROOT = f"https://api.telegram.org/file/bot{config.TELEGRAM_BOT_TOKEN}"
MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024
MAX_MESSAGE_CHARS = 4096
RETRY_DELAYS_SECONDS = (1, 2, 4)
REQUEST_TIMEOUT_SECONDS = 20


class TelegramError(RuntimeError):
    pass


def _call(method: str, payload: dict) -> dict:
    """POST to the Bot API.

    4xx answers are permanent, so only 429 and 5xx are retried. Telegram's own
    `description` is surfaced because it names the real problem. The URL is
    never logged: it contains the bot token, and requests puts the full URL
    into its exception text.
    """
    last_detail = "no response from Telegram"
    for attempt, delay in enumerate((0, *RETRY_DELAYS_SECONDS)):
        if delay:
            time.sleep(delay)
        try:
            response = requests.post(
                f"{API_ROOT}/{method}", json=payload, timeout=REQUEST_TIMEOUT_SECONDS
            )
        except requests.RequestException as exc:
            last_detail = f"network error ({type(exc).__name__})"
            log.warning("%s attempt %d: %s", method, attempt + 1, last_detail)
            continue

        try:
            body = response.json()
        except ValueError:
            body = {}

        if response.ok:
            return body.get("result", {})

        last_detail = body.get("description") or f"HTTP {response.status_code}"

        if response.status_code == 429:
            wait = body.get("parameters", {}).get("retry_after", 5)
            log.warning("%s rate limited, waiting %ss", method, wait)
            time.sleep(min(wait, 30))
            continue

        if response.status_code < 500:
            log.warning("%s rejected by Telegram: %s", method, last_detail)
            raise TelegramError(f"{method}: {last_detail}")

        log.warning("%s attempt %d: %s", method, attempt + 1, last_detail)

    raise TelegramError(f"{method}: {last_detail}")


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


def download_file(file_id: str) -> bytes:
    """Fetch an uploaded file, such as a voice note.

    Only the status code is logged: the download URL contains the bot token.
    """
    info = _call("getFile", {"file_id": file_id})
    remote_path = info.get("file_path")
    if not remote_path:
        raise TelegramError("getFile returned no file_path")

    size = info.get("file_size", 0)
    if size > MAX_DOWNLOAD_BYTES:
        raise TelegramError(f"file is {size // 1024 // 1024} MB, too large to fetch")

    try:
        response = requests.get(
            f"{FILE_ROOT}/{remote_path}", timeout=REQUEST_TIMEOUT_SECONDS
        )
    except requests.RequestException as exc:
        raise TelegramError(f"download failed ({type(exc).__name__})") from None
    if not response.ok:
        raise TelegramError(f"download failed (HTTP {response.status_code})")
    return response.content
