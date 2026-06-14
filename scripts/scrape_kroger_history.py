"""
Scrapes Kroger purchase history from kroger.com and seeds the database.
Run once to populate your item list.

  uv run scripts/scrape_kroger_history.py
"""

import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from core.db import get_conn, init_db
from core.config import KROGER_SHOPPING_EMAIL, KROGER_SHOPPING_PASSWORD


def seed_items(names: list[str]):
    conn = get_conn()
    inserted = skipped = 0
    for name in names:
        normalized = name.lower().strip()
        if not normalized:
            continue
        existing = conn.execute(
            "SELECT id FROM purchase_history WHERE store='kroger' AND normalized_name=?",
            (normalized,),
        ).fetchone()
        if existing:
            skipped += 1
        else:
            conn.execute(
                "INSERT INTO purchase_history (store, item_name, normalized_name) VALUES ('kroger', ?, ?)",
                (name.strip(), normalized),
            )
            inserted += 1
    conn.commit()
    conn.close()
    return inserted, skipped


def scrape():
    init_db()
    all_items = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        print("Navigating to Kroger...")
        page.goto("https://www.kroger.com/signin")
        page.wait_for_load_state("networkidle")

        print("Signing in...")
        page.fill('input[name="email"]', KROGER_SHOPPING_EMAIL)
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")

        page.fill('input[name="password"]', KROGER_SHOPPING_PASSWORD)
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        print("Navigating to purchase history...")
        page.goto("https://www.kroger.com/account/purchase-history")
        page.wait_for_load_state("networkidle")
        time.sleep(3)

        while True:
            # Grab all product names visible on the page
            items = page.locator('[data-testid="product-title"], .kds-Text--l, .product-title, h2.kds-Heading, [class*="product-name"]').all_text_contents()
            items = [i.strip() for i in items if i.strip()]
            all_items.extend(items)
            print(f"  Found {len(all_items)} items so far...")

            # Try to click "Load More" or next page
            try:
                load_more = page.locator('button:has-text("Load More"), button:has-text("Show More"), [data-testid="load-more"]').first
                if load_more.is_visible(timeout=3000):
                    load_more.click()
                    page.wait_for_load_state("networkidle")
                    time.sleep(2)
                else:
                    break
            except PlaywrightTimeout:
                break

        browser.close()

    unique = list(dict.fromkeys(all_items))
    print(f"\nScraped {len(unique)} unique items.")

    if not unique:
        print("Nothing found — the page selectors may need updating.")
        return

    inserted, skipped = seed_items(unique)
    print(f"Seeded DB: {inserted} inserted, {skipped} already existed.")


if __name__ == "__main__":
    scrape()
