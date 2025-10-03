from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser   = p.chromium.launch(headless=False)
    context   = browser.new_context()
    page      = context.new_page()

    page.goto("https://www.amazon.com/")
    page.click("text=Sign in")      # complete login + any 2FA here
    # … wait / fill …
    input("type something to finish")
    context.storage_state(path="amazon_state.json")   # <-- save state
    browser.close()