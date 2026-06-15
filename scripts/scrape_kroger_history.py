"""
Scrapes Kroger purchase history via internal API and seeds the database.
Uses Playwright to get session cookies, then calls the purchase-history API
to collect UPCs, then resolves product names via the developer API.

Run once to populate your item list:
  uv run scripts/scrape_kroger_history.py
"""

import time
from playwright.sync_api import sync_playwright
from core.db import get_conn, init_db
from core.config import KROGER_SHOPPING_EMAIL, KROGER_SHOPPING_PASSWORD
from integrations.kroger.client import KrogerClient

HISTORY_API = "https://www.kroger.com/atlas/v1/post-order/v1/purchase-history-search"


def fetch_all_upcs_via_playwright() -> set[str]:
    upcs = set()
    captured_pages = {}

    def handle_response(response):
        if "purchase-history-search" in response.url and response.status == 200:
            try:
                body = response.json()
                orders = body.get("data", {}).get("postOrderSearch", {}).get("data", [])
                page_no = response.url.split("pageNo=")[-1].split("&")[0]
                captured_pages[page_no] = orders
            except Exception:
                pass

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--headless=new",
            ],
        )
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page = ctx.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page.on("response", handle_response)

        print("Signing in to Kroger...")
        page.goto("https://www.kroger.com/signin")
        time.sleep(8)
        page.fill('#signInName', KROGER_SHOPPING_EMAIL)
        page.fill('#password', KROGER_SHOPPING_PASSWORD)
        page.click('button[type="submit"], #next')
        time.sleep(8)

        # Navigate to purchase history — the browser will call the API automatically
        print("Loading purchase history (page 1)...")
        page.goto("https://www.kroger.com/mypurchases")
        page.wait_for_load_state("domcontentloaded")
        time.sleep(6)

        # Use page.evaluate to trigger subsequent pages via fetch
        page_no = 2
        while True:
            result = page.evaluate(f"""async () => {{
                const r = await fetch('{HISTORY_API}?pageNo={page_no}&pageSize=50');
                if (!r.ok) return null;
                return await r.json();
            }}""")
            if not result:
                break
            orders = result.get("data", {}).get("postOrderSearch", {}).get("data", [])
            if not orders:
                break
            captured_pages[str(page_no)] = orders
            print(f"  Fetched page {page_no}...")
            page_no += 1

        browser.close()

    # Extract UPCs from all captured pages
    for orders in captured_pages.values():
        for order in orders:
            for item in order.get("lineItems", []):
                upc = item.get("upc", "").strip()
                if upc:
                    upcs.add(upc)

    print(f"  Captured {len(captured_pages)} pages, {len(upcs)} unique UPCs.")
    return upcs


def resolve_products(upcs: set[str]) -> list[tuple[str, str]]:
    """Returns list of (upc, name) tuples."""
    client = KrogerClient()
    results = []
    upc_list = list(upcs)

    for i in range(0, len(upc_list), 10):
        batch = upc_list[i:i+10]
        try:
            data = client._get("/products", {
                "filter.productId": ",".join(batch),
                "filter.locationId": "03500957",
                "filter.limit": 10,
            })
            for product in data.get("data", []):
                name = product.get("description", "").strip()
                upc = product.get("upc", "").strip()
                if name and upc:
                    results.append((upc, name))
        except Exception as e:
            print(f"  Warning: batch lookup failed ({e})")
        time.sleep(0.2)

    return results


def seed_items(products: list[tuple[str, str]]):
    conn = get_conn()
    inserted = skipped = 0
    for upc, name in products:
        normalized = name.lower().strip()
        if not normalized:
            continue
        existing = conn.execute(
            "SELECT id FROM purchase_history WHERE store='kroger' AND normalized_name=?",
            (normalized,),
        ).fetchone()
        if existing:
            # Backfill UPC if missing
            conn.execute(
                "UPDATE purchase_history SET upc=? WHERE store='kroger' AND normalized_name=? AND upc IS NULL",
                (upc, normalized),
            )
            skipped += 1
        else:
            conn.execute(
                "INSERT INTO purchase_history (store, item_name, normalized_name, upc) VALUES ('kroger', ?, ?, ?)",
                (name.strip(), normalized, upc),
            )
            inserted += 1
    conn.commit()
    conn.close()
    return inserted, skipped


def run():
    init_db()

    upcs = fetch_all_upcs_via_playwright()
    print(f"Found {len(upcs)} unique UPCs across all orders.")

    if not upcs:
        print("No UPCs found — something went wrong with the session.")
        return

    print("Resolving product names via Kroger API...")
    products = resolve_products(upcs)
    print(f"Resolved {len(products)} products.")

    inserted, skipped = seed_items(products)
    print(f"\nDone. Inserted {inserted} items, skipped {skipped} duplicates.")


if __name__ == "__main__":
    run()
