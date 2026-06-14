"""
Syncs recurring bills from DB to a dedicated Google Calendar.

Run after adding/updating bills:
  uv run tasks/sync_bills_to_calendar.py
"""

from core.db import get_conn, init_db
from integrations.google.calendar import get_service, get_or_create_calendar, upsert_bill_event


def get_bills() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT name, amount, due_day FROM recurring_bills WHERE active=1"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def run():
    init_db()
    bills = get_bills()

    if not bills:
        print("No recurring bills in DB. Add some first.")
        return

    print("Connecting to Google Calendar...")
    service = get_service()
    calendar_id = get_or_create_calendar(service)
    print(f"Using calendar ID: {calendar_id}")

    for bill in bills:
        result = upsert_bill_event(service, calendar_id, bill)
        print(f"  {result}: {bill['name']} (${bill['amount']:.2f}, due day {bill['due_day']})")

    print(f"\nDone. {len(bills)} bills synced to calendar.")


if __name__ == "__main__":
    run()
