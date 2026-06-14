"""
Add an item to your Kroger purchase history for sale matching.

Usage:
  uv run scripts/add_item.py "Dave's Killer Bread"
  uv run scripts/add_item.py "Horizon Organic Milk" "Tide Pods"
"""

import sys
from core.db import get_conn, init_db


def add(name: str):
    normalized = name.lower().strip()
    conn = get_conn()
    existing = conn.execute(
        "SELECT id FROM purchase_history WHERE store='kroger' AND normalized_name=?",
        (normalized,),
    ).fetchone()
    if existing:
        print(f"Already tracked: {name}")
    else:
        conn.execute(
            "INSERT INTO purchase_history (store, item_name, normalized_name) VALUES ('kroger', ?, ?)",
            (name.strip(), normalized),
        )
        conn.commit()
        print(f"Added: {name}")
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run scripts/add_item.py \"Item Name\" [\"Another Item\"]")
        sys.exit(1)
    init_db()
    for item in sys.argv[1:]:
        add(item)
