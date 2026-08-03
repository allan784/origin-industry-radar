python
"""
ONE-TIME (or occasional) manual login helper for the LinkedIn snapshot tool.

Run this from your own laptop, never from GitHub Actions. It opens a real,
visible Chromium window pointed at linkedin.com. You log in yourself -
including any 2FA/CAPTCHA challenge LinkedIn throws at you - exactly as if
you'd opened the browser normally. Once you're logged in and looking at your
feed, come back to this terminal and press Enter.

What this script does NOT do:
  - It never sees, stores, or asks for your password. You type it into
    LinkedIn's real login page, not into anything this script controls.
  - It doesn't automate the login itself - only you log in.

What it DOES do:
  - Saves the resulting browser session (cookies + local storage) to
    scraper/.linkedin_session.json so linkedin_snapshot.py can reuse it
    without you logging in every time.

That session file is equivalent to being logged in as you. Treat it like a
password:
  - It's already excluded via .gitignore - never remove it from there.
  - Never upload it anywhere, paste it into a chat, or commit it to git.
  - Delete it (rm scraper/.linkedin_session.json) if you ever want to revoke
    it - same effect as logging out everywhere.
  - It will expire on its own periodically (LinkedIn session lifetime, plus
    security checks may invalidate it early) - if the snapshot script starts
    failing to find any posts, just rerun this login step again.
"""
import os
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
SESSION_PATH = os.path.join(HERE, ".linkedin_session.json")


def main():
    print("Opening a browser window. Log into LinkedIn yourself, then come back here.")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://www.linkedin.com/login")

        input("\nOnce you're fully logged in and can see your LinkedIn feed, press Enter here...")

        context.storage_state(path=SESSION_PATH)
        browser.close()

    print(f"\nSession saved to {SESSION_PATH}")
    print("This file is gitignored. Keep it that way - it's equivalent to your login.")
    print("You can now run linkedin_snapshot.py without logging in again, until the session expires.")


if __name__ == "__main__":
    main()
