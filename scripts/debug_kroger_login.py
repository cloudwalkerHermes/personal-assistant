from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        args=["--disable-blink-features=AutomationControlled"],
    )
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 800},
    )
    page = ctx.new_page()
    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    page.goto("https://www.kroger.com/signin")
    time.sleep(8)

    page.screenshot(path="kroger_signin.png", full_page=True)
    print("URL:", page.url)
    print("Title:", page.title())

    # Check main frame inputs
    inputs = page.locator("input").all()
    print(f"\nMain frame inputs ({len(inputs)}):")
    for el in inputs:
        print("  type=%s name=%s id=%s" % (el.get_attribute("type"), el.get_attribute("name"), el.get_attribute("id")))

    # Check iframes
    frames = page.frames
    print(f"\nFrames ({len(frames)}):")
    for f in frames:
        print(" ", f.url[:80])
        for el in f.locator("input").all():
            print("    input type=%s name=%s id=%s" % (el.get_attribute("type"), el.get_attribute("name"), el.get_attribute("id")))

    browser.close()
