"""Intercept network requests on the Recent Items tab to find the API endpoint."""
from playwright.sync_api import sync_playwright
import time, json

api_calls = []

def handle_request(request):
    if any(x in request.url for x in ["api", "purchase", "history", "recent", "item", "product"]):
        api_calls.append({"method": request.method, "url": request.url})

def handle_response(response):
    if any(x in response.url for x in ["purchase", "history", "recent", "mypurchase"]):
        try:
            body = response.body()
            print(f"\nRESPONSE {response.status} {response.url[:100]}")
            print(body[:500])
        except Exception:
            pass

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 800},
    )
    page = ctx.new_page()
    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    page.on("request", handle_request)
    page.on("response", handle_response)

    page.goto("https://www.kroger.com/signin")
    time.sleep(8)
    page.fill('#signInName', 'wynamsorg@gmail.com')
    page.fill('#password', 'Sf.caA55B,uS42-')
    page.click('button[type="submit"], #next')
    time.sleep(8)

    page.goto("https://www.kroger.com/mypurchases")
    page.wait_for_load_state("domcontentloaded")
    time.sleep(4)
    page.click('button:has-text("Recent Items")')
    time.sleep(15)

    print("\n\nALL MATCHING API CALLS:")
    for c in api_calls:
        print(f"  {c['method']} {c['url'][:120]}")

    browser.close()
