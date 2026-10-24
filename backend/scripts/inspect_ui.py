from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.on("console", lambda m: print("CONSOLE:", m.type, m.text))
    page.on("pageerror", lambda e: print("PAGEERROR:", e))
    page.on("request", lambda r: print("REQUEST:", r.method, r.url, r.post_data))
    page.on("response", lambda r: print("RESPONSE:", r.status, r.url))

    page.goto("http://localhost:4173")
    page.wait_for_timeout(1000)

    print("Clicking submit button...")
    page.locator("button[type='submit']").click()
    page.wait_for_timeout(3000)
    print("Hash after click:", page.evaluate("() => window.location.hash"))
    print("Page title after click:", page.title())
    browser.close()
