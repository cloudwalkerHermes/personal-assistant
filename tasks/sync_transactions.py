"""
Syncs transactions from all linked Plaid accounts to the DB.

Run on a schedule (daily or weekly):
  uv run tasks/sync_transactions.py
"""

from core.db import get_conn, init_db
from integrations.plaid.client import sync_transactions


def get_linked_items() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT item_id, access_token, institution_name, cursor FROM plaid_items"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_transactions(item_id: str, added: list, removed: list[str], next_cursor: str):
    conn = get_conn()

    for txn in added:
        category = None
        cats = txn.get("personal_finance_category")
        if cats:
            category = cats.get("primary")

        try:
            conn.execute(
                """INSERT OR IGNORE INTO transactions
                   (transaction_id, item_id, account_id, date, name, merchant_name, amount, category, pending)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    txn["transaction_id"],
                    item_id,
                    txn["account_id"],
                    str(txn["date"]),
                    txn.get("name"),
                    txn.get("merchant_name"),
                    txn.get("amount"),
                    category,
                    1 if txn.get("pending") else 0,
                ),
            )
        except Exception as e:
            print(f"  Warning: skipped transaction {txn['transaction_id']}: {e}")

    for txn_id in removed:
        conn.execute("DELETE FROM transactions WHERE transaction_id=?", (txn_id,))

    conn.execute(
        "UPDATE plaid_items SET cursor=? WHERE item_id=?", (next_cursor, item_id)
    )
    conn.commit()
    conn.close()


def run():
    init_db()
    items = get_linked_items()

    if not items:
        print("No linked accounts. Run scripts/plaid_link.py first.")
        return

    for item in items:
        name = item["institution_name"] or item["item_id"]
        print(f"Syncing {name}...")
        try:
            added, removed, next_cursor = sync_transactions(
                item["access_token"], item["cursor"]
            )
            save_transactions(item["item_id"], added, removed, next_cursor)
            print(f"  +{len(added)} transactions, -{len(removed)} removed")
        except Exception as e:
            print(f"  Error syncing {name}: {e}")

    print("\nSync complete.")


if __name__ == "__main__":
    run()
