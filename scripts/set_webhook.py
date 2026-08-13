"""Register the Telegram webhook.

Usage:
    python scripts/set_webhook.py https://your-service.run.app
Reads TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_SECRET from the environment.
"""
import os
import sys

import requests


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET")
    if not token or not secret:
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_SECRET first.")
        return 1

    url = f"{sys.argv[1].rstrip('/')}/telegram/webhook"
    response = requests.post(
        f"https://api.telegram.org/bot{token}/setWebhook",
        json={
            "url": url,
            "secret_token": secret,
            "allowed_updates": ["message"],
            "drop_pending_updates": True,
        },
        timeout=20,
    )
    payload = response.json()
    if not payload.get("ok"):
        print(f"Failed: {payload.get('description')}")
        return 1

    print(f"Webhook set to {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
