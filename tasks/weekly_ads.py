"""
Weekly sale alert task — run every Wednesday.

Pulls purchase history from DB, finds Kroger sales on those items,
and prints a formatted blast for Arcus to send via Telegram.

Run:
  uv run tasks/weekly_ads.py
"""

import os
from datetime import date
from core.db import get_conn, init_db
from integrations.kroger.promotions import find_sales_for_items

KROGER_LOCATION_ID = os.getenv("KROGER_LOCATION_ID", "")
KROGER_ZIP = os.getenv("KROGER_ZIP", "")


def get_known_items() -> list[str]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT normalized_name FROM purchase_history WHERE store='kroger'"
    ).fetchall()
    conn.close()
    return [row["normalized_name"] for row in rows]


def already_sent(item_name: str, week_of: str) -> bool:
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM sale_alerts_sent WHERE store='kroger' AND item_name=? AND week_of=?",
        (item_name, week_of),
    ).fetchone()
    conn.close()
    return row is not None


def record_sent(item_name: str, sale_price: float, regular_price: float, week_of: str):
    conn = get_conn()
    conn.execute(
        """INSERT INTO sale_alerts_sent (store, item_name, sale_price, regular_price, week_of)
           VALUES ('kroger', ?, ?, ?, ?)""",
        (item_name, sale_price, regular_price, week_of),
    )
    conn.commit()
    conn.close()


def resolve_location_id() -> str:
    if KROGER_LOCATION_ID:
        return KROGER_LOCATION_ID
    if KROGER_ZIP:
        from integrations.kroger.client import KrogerClient
        store = KrogerClient().find_store(KROGER_ZIP)
        if store:
            return store["locationId"]
    raise ValueError("Set KROGER_LOCATION_ID or KROGER_ZIP in .env")


def run():
    init_db()
    week_of = str(date.today())
    location_id = resolve_location_id()
    items = get_known_items()

    if not items:
        print("No purchase history found. Run scripts/seed_kroger_history.py first.")
        return

    sales = find_sales_for_items(items, location_id)
    new_sales = [
        s for s in sales if not already_sent(s.name.lower(), week_of)
    ]

    if not new_sales:
        print("No new sales this week.")
        return

    lines = [f"Kroger Sales — week of {week_of}\n"]
    for sale in new_sales:
        lines.append(sale.format_line())
        record_sent(sale.name.lower(), sale.sale_price, sale.regular_price or 0, week_of)

    blast = "\n".join(lines)
    print(blast)


if __name__ == "__main__":
    run()
