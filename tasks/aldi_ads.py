#!/usr/bin/env python3
"""
tasks/aldi_ads.py
-----------------
Wednesday morning Aldi weekly specials blast via Thunderbit CLI.
Scrapes aldi.us/en/weekly-specials/ with an explicit schema so pricing
and categories come back reliably. Sends formatted Telegram message.

Run from personal-assistant/:
    .venv/bin/python3 tasks/aldi_ads.py
"""

import os
import sys
import json
import subprocess
from datetime import date

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

from dotenv import load_dotenv
load_dotenv()

from integrations.telegram import send as telegram_send

THUNDERBIT_API_KEY = os.getenv("THUNDERBIT_API_KEY")
ALDI_URL           = "https://www.aldi.us/en/weekly-specials/"
THUNDERBIT_BIN     = "/home/arcus/.hermes/node/bin/thunderbit"

SCHEMA = json.dumps({
    "Product Name": {
        "type": "text",
        "instruction": "Name of the product on sale",
    },
    "Current Price": {
        "type": "number",
        "instruction": "Current sale price in USD",
    },
    "Product Size": {
        "type": "text",
        "instruction": "Size or quantity of the product",
    },
    "Category": {
        "type": "text",
        "instruction": "Section category such as Price Drops, Weekly Ad, ALDI Finds Food, New and Trending, Best Selling ALDI Finds",
    },
})

SKIP_CATEGORIES = {"Best Selling ALDI Finds"}

CATEGORY_EMOJI = {
    "Price Drops":              "📉",
    "Weekly Ad":                "🛒",
    "Weekly Ad Products":       "🛒",
    "ALDI Finds Food":          "🍽️",
    "New & Trending":           "✨",
    "New and Trending":         "✨",
    "Best Selling ALDI Finds":  "🛍️",
}

CATEGORY_ORDER = [
    "Price Drops",
    "Weekly Ad",
    "ALDI Finds Food",
    "New & Trending",
    "Best Selling ALDI Finds",
]


# ── SCRAPE ────────────────────────────────────────────────────────────────────

def scrape() -> list[dict]:
    if not THUNDERBIT_API_KEY:
        raise RuntimeError("THUNDERBIT_API_KEY not set in .env")

    env    = {**os.environ, "THUNDERBIT_API_KEY": THUNDERBIT_API_KEY}
    result = subprocess.run(
        [THUNDERBIT_BIN, "extract", ALDI_URL, "--format", "json", "--schema", SCHEMA],
        capture_output=True, text=True, env=env, timeout=120,
    )

    output = (result.stdout + result.stderr).replace("\r", "")
    idx    = output.find("{")
    if idx == -1:
        raise RuntimeError(f"No JSON in thunderbit output:\n{output[:400]}")

    data, _ = json.JSONDecoder().raw_decode(output, idx)
    if not data.get("success"):
        raise RuntimeError(f"Thunderbit error: {data.get('error')}")

    return data["data"]["extracted_data"]


# ── FORMAT ────────────────────────────────────────────────────────────────────

def build_message(rows: list[dict]) -> str:
    by_cat: dict[str, list[dict]] = {}
    for row in rows:
        cat = (row.get("Category") or "Other").strip()
        by_cat.setdefault(cat, []).append(row)

    today = date.today().strftime("%b %-d")
    lines = [f"🛒 Aldi Weekly Specials — {today}", ""]

    all_cats = CATEGORY_ORDER + [c for c in by_cat if c not in CATEGORY_ORDER]

    for cat in all_cats:
        if cat not in by_cat or cat in SKIP_CATEGORIES:
            continue
        emoji = CATEGORY_EMOJI.get(cat, "•")
        lines.append(f"{emoji} {cat}")

        for item in by_cat[cat]:
            name  = item.get("Product Name", "?")
            price = item.get("Current Price")
            size  = item.get("Product Size", "")
            price_str = f"${float(price):.2f}" if price else ""
            size_str  = f" / {size}" if size and size.lower() not in ("1 each", "") else ""
            lines.append(f"  • {name}  {price_str}{size_str}".rstrip())

        lines.append("")

    return "\n".join(lines).rstrip()


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    print("Scraping Aldi weekly specials via Thunderbit...")
    try:
        rows = scrape()
    except Exception as e:
        print(f"[!] Scrape failed: {e}")
        telegram_send(f"⚠️ Aldi scraper failed: {e}")
        return

    print(f"Got {len(rows)} items.")
    msg = build_message(rows)
    print(msg)
    telegram_send(msg)


if __name__ == "__main__":
    main()
