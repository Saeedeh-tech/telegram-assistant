"""Expense logging in a Google Sheet.

Uses the same service account as the calendar: share the sheet with that email
and no new credentials are needed. Rows are Date, Amount, Category, Note.
"""
import logging
from collections import defaultdict

from googleapiclient.errors import HttpError

from .. import config, google_auth, timeparse
from . import register

log = logging.getLogger(__name__)

HEADERS = ["Date", "Amount", "Category", "Note"]
MAX_ROWS_SCANNED = 5000
DISABLED = {
    "error": "Expense logging is off. Set EXPENSES_SPREADSHEET_ID to switch it on."
}


def _range(cells: str) -> str:
    return f"{config.EXPENSES_SHEET_NAME}!{cells}"


def _explain(error: HttpError) -> str:
    if error.resp.status == 404:
        return "Spreadsheet not found. Check EXPENSES_SPREADSHEET_ID."
    if error.resp.status == 403:
        return "Permission denied. Share the sheet with the service account as Editor."
    if error.resp.status == 400:
        return f"Sheet '{config.EXPENSES_SHEET_NAME}' not found. Check the tab name."
    return f"Sheets API error {error.resp.status}"


def _rows() -> list[list[str]]:
    result = (
        google_auth.sheets()
        .spreadsheets()
        .values()
        .get(spreadsheetId=config.EXPENSES_SPREADSHEET_ID, range=_range(f"A1:D{MAX_ROWS_SCANNED}"))
        .execute()
    )
    values = result.get("values", [])
    # Skip a header row if one is present.
    return values[1:] if values and values[0][:1] == HEADERS[:1] else values


@register(
    name="log_expense",
    description=(
        "Record one spend in the expense sheet. Amount is a number without a "
        "currency symbol. Category is a short word such as groceries or fuel."
    ),
    parameters={
        "type": "object",
        "properties": {
            "amount": {"type": "number", "description": "How much was spent"},
            "category": {"type": "string", "description": "Short category word"},
            "note": {"type": "string", "description": "Optional detail"},
            "date": {"type": "string", "description": "ISO date; defaults to today"},
        },
        "required": ["amount", "category"],
    },
)
def log_expense(
    chat_id: int,
    amount: float,
    category: str,
    note: str | None = None,
    date: str | None = None,
) -> dict:
    if not config.EXPENSES_SPREADSHEET_ID:
        return DISABLED
    value = float(amount)
    if value <= 0:
        raise ValueError("Amount must be greater than zero")
    if not category.strip():
        raise ValueError("Category cannot be empty")

    when = timeparse.parse_local(date) if date else timeparse.now_local()
    row = [when.strftime("%Y-%m-%d"), value, category.strip().lower(), (note or "").strip()]

    try:
        google_auth.sheets().spreadsheets().values().append(
            spreadsheetId=config.EXPENSES_SPREADSHEET_ID,
            range=_range("A:D"),
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]},
        ).execute()
    except HttpError as exc:
        return {"error": _explain(exc)}

    return {"logged": True, "amount": value, "category": row[2], "date": row[0]}


@register(
    name="expense_summary",
    description=(
        "Total spending by category over a period. `month` is YYYY-MM, or leave "
        "it out for the current month."
    ),
    parameters={
        "type": "object",
        "properties": {
            "month": {"type": "string", "description": "YYYY-MM, for example 2026-08"},
            "category": {"type": "string", "description": "Limit to one category"},
        },
        "required": [],
    },
)
def expense_summary(chat_id: int, month: str | None = None, category: str | None = None) -> dict:
    if not config.EXPENSES_SPREADSHEET_ID:
        return DISABLED

    prefix = (month or timeparse.now_local().strftime("%Y-%m")).strip()
    wanted = category.strip().lower() if category else None

    try:
        rows = _rows()
    except HttpError as exc:
        return {"error": _explain(exc)}

    totals, count, skipped = defaultdict(float), 0, 0
    for row in rows:
        if len(row) < 3 or not str(row[0]).startswith(prefix):
            continue
        try:
            value = float(str(row[1]).replace("$", "").replace(",", "").strip())
        except ValueError:
            skipped += 1
            continue
        name = str(row[2]).strip().lower()
        if wanted and name != wanted:
            continue
        totals[name] += value
        count += 1

    result = {
        "period": prefix,
        "entries": count,
        "total": round(sum(totals.values()), 2),
        "by_category": {k: round(v, 2) for k, v in sorted(totals.items(), key=lambda kv: -kv[1])},
    }
    if skipped:
        result["rows_skipped"] = skipped
    return result
