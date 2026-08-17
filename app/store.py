"""Postgres persistence: chat history, notes, reminders, update deduplication.

Every function keeps the same name and signature as the Firestore version, so
the agent, the tools and the routes did not change when the database was swapped.
"""
import json
import logging
from datetime import datetime, timedelta, timezone

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from . import config, timeparse

log = logging.getLogger(__name__)

SEEN_UPDATE_RETENTION = timedelta(days=1)

SCHEMA = """
CREATE TABLE IF NOT EXISTS seen_updates (
    update_id BIGINT PRIMARY KEY,
    seen_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS conversations (
    chat_id    BIGINT PRIMARY KEY,
    turns      JSONB NOT NULL DEFAULT '[]'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS notes (
    id         BIGSERIAL PRIMARY KEY,
    chat_id    BIGINT NOT NULL,
    text       TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS notes_by_chat ON notes (chat_id, created_at DESC);
CREATE TABLE IF NOT EXISTS reminders (
    id      BIGSERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    text    TEXT NOT NULL,
    due_at  TIMESTAMPTZ NOT NULL,
    sent    BOOLEAN NOT NULL DEFAULT FALSE,
    sent_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS reminders_pending ON reminders (due_at) WHERE NOT sent;
-- Added after the first release, so existing tables are upgraded in place.
ALTER TABLE reminders ADD COLUMN IF NOT EXISTS repeat_rule TEXT;
ALTER TABLE reminders ADD COLUMN IF NOT EXISTS repeat_anchor TIMESTAMPTZ;
CREATE TABLE IF NOT EXISTS job_runs (
    job      TEXT NOT NULL,
    run_date DATE NOT NULL,
    ran_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (job, run_date)
);
"""

# min_size 0 lets the database scale to zero while the bot is idle, which is
# what keeps the free compute allowance from running out.
_pool = ConnectionPool(
    conninfo=config.DATABASE_URL,
    min_size=0,
    max_size=3,
    kwargs={"row_factory": dict_row},
    open=False,
)
_schema_ready = False


def _connection():
    """Open the pool and create the tables on first use."""
    global _schema_ready
    if not _schema_ready:
        _pool.open()
        with _pool.connection() as conn:
            conn.execute(SCHEMA)
        _schema_ready = True
        log.info("Database schema is ready")
    return _pool.connection()


def _as_int(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def claim_update(update_id: int) -> bool:
    """Return True the first time an update_id is seen.

    Telegram redelivers updates when a webhook is slow, so each one must be
    processed at most once.
    """
    with _connection() as conn:
        row = conn.execute(
            "INSERT INTO seen_updates (update_id) VALUES (%s)"
            " ON CONFLICT DO NOTHING RETURNING update_id",
            (update_id,),
        ).fetchone()
    if row is None:
        log.info("Ignoring duplicate update %s", update_id)
    return row is not None


def purge_old_updates() -> int:
    """Delete deduplication rows past the retention window."""
    cutoff = datetime.now(timezone.utc) - SEEN_UPDATE_RETENTION
    with _connection() as conn:
        return conn.execute("DELETE FROM seen_updates WHERE seen_at < %s", (cutoff,)).rowcount


def claim_job(job: str, run_date) -> bool:
    """Return True only for the first caller of this job on this date.

    The sweep runs every 30 minutes, so each scheduled job must claim its slot
    before sending anything.
    """
    with _connection() as conn:
        row = conn.execute(
            "INSERT INTO job_runs (job, run_date) VALUES (%s, %s)"
            " ON CONFLICT DO NOTHING RETURNING job",
            (job, run_date),
        ).fetchone()
    return row is not None


def load_history(chat_id: int) -> list[dict]:
    with _connection() as conn:
        row = conn.execute(
            "SELECT turns FROM conversations WHERE chat_id = %s", (chat_id,)
        ).fetchone()
    return row["turns"] if row else []


def append_history(chat_id: int, user_text: str, model_text: str) -> None:
    """Store the visible turn only; tool call details are not replayed."""
    turns = load_history(chat_id)
    turns.append({"role": "user", "text": user_text})
    turns.append({"role": "model", "text": model_text})
    trimmed = turns[-config.MAX_HISTORY_TURNS * 2 :]
    with _connection() as conn:
        conn.execute(
            "INSERT INTO conversations (chat_id, turns) VALUES (%s, %s)"
            " ON CONFLICT (chat_id) DO UPDATE"
            " SET turns = EXCLUDED.turns, updated_at = now()",
            (chat_id, json.dumps(trimmed)),
        )


def clear_history(chat_id: int) -> None:
    with _connection() as conn:
        conn.execute("DELETE FROM conversations WHERE chat_id = %s", (chat_id,))


def add_note(chat_id: int, text: str) -> str:
    with _connection() as conn:
        row = conn.execute(
            "INSERT INTO notes (chat_id, text) VALUES (%s, %s) RETURNING id", (chat_id, text)
        ).fetchone()
    return str(row["id"])


def search_notes(chat_id: int, query: str, limit: int = 10) -> list[dict]:
    """Case-insensitive substring search. An empty query returns recent notes."""
    pattern = f"%{query.strip()}%"
    with _connection() as conn:
        rows = conn.execute(
            "SELECT id, text, created_at FROM notes"
            " WHERE chat_id = %s AND text ILIKE %s"
            " ORDER BY created_at DESC LIMIT %s",
            (chat_id, pattern, limit),
        ).fetchall()
    return [
        {"id": str(row["id"]), "text": row["text"], "created_at": row["created_at"]}
        for row in rows
    ]


def delete_note(note_id: str, chat_id: int) -> bool:
    """Delete only if the note belongs to this chat."""
    numeric_id = _as_int(note_id)
    if numeric_id is None:
        return False
    with _connection() as conn:
        deleted = conn.execute(
            "DELETE FROM notes WHERE id = %s AND chat_id = %s", (numeric_id, chat_id)
        ).rowcount
    return deleted > 0


def add_reminder(
    chat_id: int,
    text: str,
    due_at: datetime,
    repeat_rule: str | None = None,
    repeat_anchor: datetime | None = None,
) -> str:
    with _connection() as conn:
        row = conn.execute(
            "INSERT INTO reminders (chat_id, text, due_at, repeat_rule, repeat_anchor)"
            " VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (chat_id, text, due_at, repeat_rule, repeat_anchor or due_at),
        ).fetchone()
    return str(row["id"])


def cancel_reminder(reminder_id: str, chat_id: int) -> bool:
    """Delete a reminder, but only if it belongs to this chat."""
    numeric_id = _as_int(reminder_id)
    if numeric_id is None:
        return False
    with _connection() as conn:
        removed = conn.execute(
            "DELETE FROM reminders WHERE id = %s AND chat_id = %s AND NOT sent",
            (numeric_id, chat_id),
        ).rowcount
    return removed > 0


def reschedule_reminder(reminder_id: str, chat_id: int, due_at: datetime) -> bool:
    """Move a pending reminder. The repeat anchor moves with it."""
    numeric_id = _as_int(reminder_id)
    if numeric_id is None:
        return False
    with _connection() as conn:
        changed = conn.execute(
            "UPDATE reminders SET due_at = %s, repeat_anchor = %s"
            " WHERE id = %s AND chat_id = %s AND NOT sent",
            (due_at, due_at, numeric_id, chat_id),
        ).rowcount
    return changed > 0


def list_pending_reminders(chat_id: int, limit: int = 20) -> list[dict]:
    with _connection() as conn:
        rows = conn.execute(
            "SELECT id, text, due_at, repeat_rule FROM reminders"
            " WHERE chat_id = %s AND NOT sent ORDER BY due_at LIMIT %s",
            (chat_id, limit),
        ).fetchall()
    return [
        {
            "id": str(row["id"]),
            "text": row["text"],
            "due_at": row["due_at"],
            "repeat_rule": row["repeat_rule"],
        }
        for row in rows
    ]


def claim_due_reminders(limit: int = 50) -> list[dict]:
    """Mark due reminders as sent and return them, in one atomic statement.

    Marking before delivery means a failed send loses one reminder rather than
    retrying forever and flooding the chat. SKIP LOCKED stops two overlapping
    sweeps from claiming the same row.
    """
    with _connection() as conn:
        rows = conn.execute(
            "UPDATE reminders SET sent = TRUE, sent_at = now() WHERE id IN ("
            "  SELECT id FROM reminders WHERE NOT sent AND due_at <= now()"
            "  ORDER BY due_at LIMIT %s FOR UPDATE SKIP LOCKED"
            ") RETURNING id, chat_id, text, due_at, repeat_rule, repeat_anchor",
            (limit,),
        ).fetchall()

    claimed = []
    for row in rows:
        claimed.append(
            {"id": str(row["id"]), "chat_id": row["chat_id"], "text": row["text"],
             "due_at": row["due_at"]}
        )
        # A repeating reminder books its next occurrence as this one goes out.
        if row["repeat_rule"]:
            following = timeparse.next_occurrence(
                row["due_at"], row["repeat_rule"], anchor=row["repeat_anchor"]
            )
            if following:
                add_reminder(row["chat_id"], row["text"], following,
                             row["repeat_rule"], row["repeat_anchor"] or row["due_at"])
            else:
                log.warning("Unknown repeat rule %r, not rescheduled", row["repeat_rule"])
    return claimed


def check_connection() -> bool:
    """Used by the health endpoint to prove the database is reachable."""
    try:
        with _connection() as conn:
            conn.execute("SELECT 1")
        return True
    except psycopg.Error:
        log.exception("Database health check failed")
        return False
