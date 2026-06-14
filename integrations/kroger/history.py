import requests
from core.db import get_conn, init_db
from integrations.kroger.auth import get_valid_token

BASE_URL = "https://api.kroger.com/v1"


def _get(path: str, params: dict = None) -> dict:
    resp = requests.get(
        f"{BASE_URL}{path}",
        headers={"Authorization": f"Bearer {get_valid_token()}"},
        params=params,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_past_purchases() -> list[dict]:
    data = _get("/lists/past-purchases")
    return data.get("data", {}).get("items", [])


def sync_purchase_history():
    init_db()
    items = fetch_past_purchases()

    if not items:
        print("No past purchases returned from Kroger API.")
        return

    conn = get_conn()
    inserted = skipped = 0

    for item in items:
        name = item.get("description", "").strip()
        if not name:
            continue
        normalized = name.lower().strip()

        existing = conn.execute(
            "SELECT id FROM purchase_history WHERE store='kroger' AND normalized_name=?",
            (normalized,),
        ).fetchone()

        if existing:
            skipped += 1
            continue

        price = None
        items_data = item.get("items", [])
        if items_data:
            price = items_data[0].get("price", {}).get("regular")

        conn.execute(
            """INSERT INTO purchase_history (store, item_name, normalized_name, price)
               VALUES ('kroger', ?, ?, ?)""",
            (name, normalized, price),
        )
        inserted += 1

    conn.commit()
    conn.close()
    print(f"Synced Kroger history. Inserted {inserted}, skipped {skipped} duplicates.")
