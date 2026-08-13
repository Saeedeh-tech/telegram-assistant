# Telegram assistant

A personal chatbot you talk to inside Telegram on your iPhone. It can create and
read Google Calendar events, save notes, set reminders, and send Telegram
messages to people you approve.

There is no iOS app to build. Telegram is the interface, so you skip Xcode, the
App Store, and the Apple developer account.

## Architecture

```
Telegram app (iPhone)
        |  message
        v
Telegram servers  --- webhook (HTTPS + secret header) --->  Render web service
                                                                  |
                                            +---------------------+------------------+
                                            |                     |                  |
                                            v                     v                  v
                                     Gemini API           Neon Postgres       Google Calendar API
                                  (chooses a tool)      (history, notes,     (service account with
                                                         reminders)          shared calendar access)
                                            |
                                            v
                                     reply back to Telegram

GitHub Actions --- every 30 min ---> /tasks/due-reminders ---> Telegram message
```

Everything above is on a permanent free tier. No credit card is required at any
step.

### How a message flows

1. Telegram POSTs the update to `/telegram/webhook`.
2. `security.py` checks the secret header and that the sender is on the allowlist.
3. `store.claim_update()` rejects redeliveries, so each update runs once.
4. `agent.py` loads chat history, calls Gemini with all tool schemas attached,
   and loops: run the tools Gemini asks for, feed results back, repeat until
   Gemini returns plain text or the step limit is reached.
5. The reply goes back to Telegram and the turn is saved to Firestore.

### Modules

| File | Responsibility |
| --- | --- |
| `app/main.py` | Flask routes, slash commands, always answers Telegram with 200 |
| `app/config.py` | Reads and validates every setting at startup |
| `app/security.py` | Webhook secret and scheduler secret, user allowlist |
| `app/agent.py` | Gemini tool-calling loop, retries, step limit |
| `app/store.py` | Postgres: history, notes, reminders, deduplication |
| `app/telegram.py` | Bot API client, retries, 4096 character splitting |
| `app/timeparse.py` | Shared local time parsing, used by calendar and reminders |
| `app/tools/__init__.py` | Tool registry: one decorator defines schema and handler |
| `app/tools/calendar_tools.py` | `create_calendar_event`, `list_calendar_events` |
| `app/tools/notes.py` | Notes and reminders |
| `app/tools/messaging.py` | Sending messages to approved contacts |

### Two design decisions worth knowing

**Calendar goes through Google, not iCloud.** A server cannot write to an iCloud
calendar. Instead the bot writes to your Google Calendar, and you add that Google
account under iOS Settings → Apps → Calendar → Accounts. Events then appear in
the normal iOS Calendar app within about a minute.

**Reminders arrive in Telegram, not iOS Reminders.** iOS Reminders is also closed
to servers. Reminders are stored in Postgres and a GitHub Actions timer delivers
them as Telegram messages. This is arguably better, because the notification
arrives in the app you are already using.

**The reminder timer runs every 30 minutes, on purpose.** Neon's free database
sleeps after 5 minutes of inactivity, and only sleeping keeps it inside the 100
compute-hours a month allowance. A 5-minute timer would keep it permanently awake
and use roughly 186 hours, which suspends the database. For the same reason
`/healthz` does not touch the database unless you ask it to with `?deep=1`.

### Adding a tool

Write one function. The decorator handles registration, schema generation and
error wrapping.

```python
@register(
    name="my_tool",
    description="What it does, written for the model to read.",
    parameters={"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]},
)
def my_tool(chat_id: int, x: str) -> dict:
    return {"result": x.upper()}
```

Import it in `app/tools/__init__.py`. Nothing else changes.

## Setup

See **SETUP.md** for the full walkthrough, written for a first-time setup.

## Cost

| Service | Free allowance | Card needed |
| --- | --- | --- |
| Telegram Bot API | unlimited | no |
| Render web service | 750 hours/month, sleeps when idle | no |
| Neon Postgres | 0.5 GB, 100 compute-hours/month | no |
| GitHub Actions | free for private repos | no |
| Gemini API | free tier, daily request cap | no |
| Google Calendar API | free, no billing needed | no |

The realistic limit is the Gemini daily request cap, not anything else.

## Known limits

- Text messages only. Voice notes and photos are politely refused.
- Reminders arrive on a 30 minute sweep, so delivery can be up to 30 minutes
  late. See the note above about why it is not shorter.
- The first message after a quiet period takes 30 to 60 seconds while the free
  host wakes up. After that it is fast until it goes idle again.
- Note search is a case-insensitive substring match in Postgres.
- Conversation history keeps the last 20 turns; `/reset` clears it.
- Anything that must run on the phone itself, such as an iCloud-only calendar or
  a Siri trigger, needs the Apple Shortcuts app calling this service instead.

## Local testing

Windows PowerShell:

```powershell
pip install -r requirements.txt
Copy-Item .env.example .env          # fill in real values first
Get-Content .env | Where-Object { $_ -match '^\s*[^#].*=' } | ForEach-Object {
    $name, $value = $_ -split '=', 2
    [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim())
}
flask --app app.main run --port 8080
```

macOS or Linux:

```bash
pip install -r requirements.txt
cp .env.example .env
set -a && source .env && set +a
flask --app app.main run --port 8080
```

Then open `http://localhost:8080/healthz?deep=1` in a browser.

Use `ngrok http 8080` and point `scripts/set_webhook.py` at the ngrok URL to test
against real Telegram traffic.

## Deploying somewhere else

The app is a plain Flask service with a Dockerfile and no host-specific code. It
runs unchanged on Cloud Run, Fly.io or any container host. Only `DATABASE_URL`
and the reminder timer would need repointing.
