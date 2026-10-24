from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.on("console", lambda m: print("CONSOLE:", m.type, m.text))
    page.on("pageerror", lambda e: print("PAGEERROR:", e))

    page.goto("http://localhost:4173")
    page.wait_for_timeout(1000)

    # Click Script Text tab
    script_tab = page.locator("button:has-text('Script Text')").first
    script_tab.click()
    page.wait_for_timeout(500)

    ta = page.locator("#script-textarea")
    print("Textarea visible:", ta.is_visible())
    print("Textarea initial val:", ta.input_value())
    ta.fill("A beautiful golden sunrise illuminates the snow covered mountain peaks.")
    page.wait_for_timeout(500)
    print("Textarea updated val:", ta.input_value())

    btn = page.locator("button[type='submit']").first
    print("Submit button enabled:", btn.is_enabled())

    page.on("request", lambda r: print("REQUEST:", r.method, r.url))
    btn.click()
    page.wait_for_timeout(3000)
    print("Current URL:", page.url)
    browser.close()
