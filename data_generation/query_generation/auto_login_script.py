from playwright.sync_api import sync_playwright
import argparse

def auto_login_and_save(email: str,
                        password: str,
                        context_path: str,
                        headless: bool = False,
                        start_url: str = "https://www.amazon.com/"):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()

        # Go to Amazon
        page.goto(start_url)
        page.wait_for_selector("#nav-link-accountList", timeout=15000)

        # Click "Sign in"
        page.click("#nav-link-accountList")

        # Fill email and continue
        page.fill('input[name="email"]', email, timeout=10000)
        page.press('input[name="email"]', 'Enter')

        # Fill password and sign in
        page.wait_for_selector('input[name="password"]', timeout=10000)
        page.fill('input[name="password"]', password)
        page.click('input#signInSubmit')

        # Save storage state
        page.wait_for_load_state('domcontentloaded')
        context.storage_state(path=context_path)

        browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto-login to Amazon and save Playwright storage state.")
    parser.add_argument(
        "--email",
        type=str,
        default="xianrenz+0-1752706588919zQqX@amazon.com",
        help="Amazon account email"
    )
    parser.add_argument(
        "--password",
        type=str,
        default="o9cx0g3@f#2a8hti",
        help="Amazon account password"
    )
    parser.add_argument(
        "--context_path",
        type=str,
        default="data_generation/amazon_state.json",
        help="Path to save Playwright storage state JSON"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode"
    )
    parser.add_argument(
        "--start_url",
        type=str,
        default="https://www.amazon.com/",
        help="Starting URL (default: Amazon homepage)"
    )
    args = parser.parse_args()

    auto_login_and_save(
        email=args.email,
        password=args.password,
        context_path=args.context_path,
        headless=args.headless,
        start_url=args.start_url
    )