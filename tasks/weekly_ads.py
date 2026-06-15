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
from integrations.kroger.promotions import find_sales_for_upcs, find_sales_for_items
from integrations.telegram import send as telegram_send

KROGER_LOCATION_ID = os.getenv("KROGER_LOCATION_ID", "")
KROGER_ZIP = os.getenv("KROGER_ZIP", "")


def get_known_items() -> tuple[list[str], list[str]]:
    """Returns (upcs, names_without_upc)."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT normalized_name, upc FROM purchase_history WHERE store='kroger'"
    ).fetchall()
    conn.close()
    upcs = [r["upc"] for r in rows if r["upc"]]
    names_no_upc = [r["normalized_name"] for r in rows if not r["upc"]]
    return upcs, names_no_upc


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
    upcs, names_no_upc = get_known_items()

    if not upcs and not names_no_upc:
        print("No purchase history found. Run scripts/scrape_kroger_history.py first.")
        return

    sales = []

    if upcs:
        print(f"Checking {len(upcs)} known UPCs for sales...")
        sales.extend(find_sales_for_upcs(upcs, location_id))

    if names_no_upc:
        print(f"Text-searching {len(names_no_upc)} items without UPCs...")
        sales.extend(find_sales_for_items(names_no_upc, location_id))

    # Sort all sales by savings pct descending
    sales.sort(key=lambda s: s.savings_pct() or 0, reverse=True)

    new_sales = [s for s in sales if not already_sent(s.name.lower(), week_of)]

    if not new_sales:
        print("No new sales this week.")
        return

    lines = [f"🛒 Kroger Sales — week of {week_of}\n"]
    for sale in new_sales:
        lines.append(sale.format_line())
        record_sent(sale.name.lower(), sale.sale_price, sale.regular_price or 0, week_of)

    message = "\n".join(lines)
    print(message)
    telegram_send(message)


if __name__ == "__main__":
    run()
