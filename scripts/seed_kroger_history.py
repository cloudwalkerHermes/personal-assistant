"""
Seed purchase history from a CSV export of Kroger order history.

CSV format (copy from Kroger order history page, paste into kroger_orders.csv):
  item_name,date,price

Run:
  uv run scripts/seed_kroger_history.py kroger_orders.csv
"""

import csv
import sys
from core.db import get_conn, init_db


def normalize(name: str) -> str:
    return name.lower().strip()


def seed(filepath: str):
    init_db()
    conn = get_conn()
    inserted = 0
    skipped = 0

    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("item_name", "").strip()
            if not name:
                continue
            date = row.get("date", "").strip() or None
            price_raw = row.get("price", "").replace("$", "").strip()
            price = float(price_raw) if price_raw else None

            existing = conn.execute(
                "SELECT id FROM purchase_history WHERE store='kroger' AND normalized_name=?",
                (normalize(name),),
            ).fetchone()

            if existing:
                skipped += 1
                continue

            conn.execute(
                """INSERT INTO purchase_history (store, item_name, normalized_name, purchased_at, price)
                   VALUES ('kroger', ?, ?, ?, ?)""",
                (name, normalize(name), date, price),
            )
            inserted += 1

    conn.commit()
    conn.close()
    print(f"Done. Inserted {inserted}, skipped {skipped} duplicates.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run scripts/seed_kroger_history.py <path-to-csv>")
        sys.exit(1)
    seed(sys.argv[1])
