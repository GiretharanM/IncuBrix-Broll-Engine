from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.on("console", lambda m: print("CONSOLE:", m.type, m.text))
    page.on("pageerror", lambda e: print("PAGEERROR:", e))
    page.on("response", lambda r: print("RESPONSE:", r.status, r.url))

    page.goto("http://localhost:4173")
    page.wait_for_timeout(1000)

    # Click Script Text tab
    page.locator("button:has-text('Script Text')").first.click()
    page.wait_for_timeout(500)

    # Fill script
    page.locator("#script-textarea").fill("A beautiful golden sunrise illuminates the mountain lake.")
    page.wait_for_timeout(500)

    # Click button
    btn = page.locator("button:has-text('Create B-Roll Video')").first
    print("Button enabled:", btn.is_enabled())
    btn.click()

    page.wait_for_timeout(4000)
    print("Current page URL:", page.url)
    browser.close()
