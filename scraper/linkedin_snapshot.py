python
"""
Manual, on-demand LinkedIn snapshot. Run this yourself, from your own
machine, whenever you want an update on the accounts in linkedin_accounts.csv.

NOT scheduled. NOT run from GitHub Actions. NOT run against a datacenter IP.
That's deliberate - see README for why. Running this repeatedly in a tight
loop, on a fixed schedule, or against far more than a handful of accounts in
one sitting recreates the exact bot signature we're trying to avoid. Batch
it: do 15-20 accounts, take a break, do the next batch another day.

Usage:
    python scraper/linkedin_login.py        # once, or whenever the session expires
    python scraper/linkedin_snapshot.py --start 0 --end 20
    python scraper/linkedin_snapshot.py --start 20 --end 40
    ...

This is best-effort scraping of LinkedIn's rendered page. LinkedIn's markup
changes without notice and isn't designed to be parsed - if this starts
returning nothing, that's the most likely reason, not a bug in the merge
logic. It falls back to saving raw page text per profile if it can't find
structured post elements, so you don't lose the run entirely.
"""
import argparse
import csv
import os
import random
import sys
import time
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from classify import tag_sectors, dedupe, _hash_url  # noqa: E402
from build_dashboard import load_existing, prune  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SESSION_PATH = os.path.join(HERE, ".linkedin_session.json")
ACCOUNTS_CSV = os.path.join(HERE, "linkedin_accounts.csv")
DATA_PATH = os.path.join(HERE, "..", "site", "data.json")
RAW_DUMP_DIR = os.path.join(HERE, ".linkedin_raw")  # gitignored, for manual review when parsing fails

# Best-effort selector for LinkedIn's post containers. Known to be fragile -
# LinkedIn changes class names periodically. If this stops matching anything,
# the script falls back to a raw text dump per profile instead of failing.
POST_SELECTOR = "div.feed-shared-update-v2, div[data-urn*='activity']"

CATEGORY_KEYWORDS = {
    "consumer_fitness_trends": ["workout", "training trend", "class format", "member experience", "wellness"],
    "consumer_equipment_trends": ["wearable", "home gym", "connected fitness", "smart equipment"],
    "gym_trends": ["membership", "gym opening", "gym closure", "operator", "leisure centre", "acquisition"],
    "gym_equipment_trends": ["equipment launch", "new kit", "manufacturer", "supplier", "product range"],
}


def guess_category(text: str) -> str:
    text_l = text.lower()
    best, best_score = "industry_voices", 0
    for cat, kws in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in kws if kw in text_l)
        if score > best_score:
            best, best_score = cat, score
    return best


def load_accounts():
    accounts = []
    with open(ACCOUNTS_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("url", "").startswith("http"):
                accounts.append(row)
    return accounts


def scrape_profile(page, account):
    url = account["url"].rstrip("/") + "/recent-activity/all/"
    items = []
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(random.uniform(2500, 4500))
        for _ in range(2):
            page.mouse.wheel(0, 1800)
            page.wait_for_timeout(random.uniform(1200, 2200))

        posts = page.query_selector_all(POST_SELECTOR)
        if not posts:
            os.makedirs(RAW_DUMP_DIR, exist_ok=True)
            dump_path = os.path.join(RAW_DUMP_DIR, f"{account['name'].replace(' ', '_')}.txt")
            with open(dump_path, "w", encoding="utf-8") as f:
                f.write(page.inner_text("body"))
            print(f"  [no structured posts found for {account['name']} - raw page text saved to {dump_path}]")
            return items

        for p in posts[:8]:
            text = p.inner_text().strip().replace("\n", " ")
            if len(text) < 20:
                continue
            items.append({
                "title": f"{account['name']}: {text[:120]}",
                "url": account["url"],
                "summary": text[:500],
                "source": f"LinkedIn — {account['name']}",
                "source_type": "linkedin_manual",
                "region": "uk_or_global",
            })
    except Exception as exc:
        print(f"  [warn] failed to fetch {account['name']}: {exc}")
    return items


def enrich_linkedin(items):
    enriched = []
    for it in items:
        text = f"{it['title']} {it['summary']}"
        it["category"] = guess_category(text)
        it["sectors"] = tag_sectors(text)
        it["foresight"] = False
        it["fetched_at"] = datetime.now(timezone.utc).isoformat()
        it["id"] = _hash_url(it["url"] + it["title"])
        enriched.append(it)
    return dedupe(enriched)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=20, help="exclusive end index - keep batches small")
    args = parser.parse_args()

    if not os.path.exists(SESSION_PATH):
        print("No saved session found. Run: python scraper/linkedin_login.py first.")
        return

    accounts = load_accounts()[args.start:args.end]
    if not accounts:
        print("No accounts in range - check linkedin_accounts.csv and your --start/--end.")
        return

    print(f"Fetching {len(accounts)} accounts (index {args.start}-{args.end}). "
          f"This deliberately runs slowly - don't parallelise it.")

    all_items = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=SESSION_PATH)
        page = context.new_page()

        for i, account in enumerate(accounts):
            print(f"[{i+1}/{len(accounts)}] {account['name']}")
            all_items.extend(scrape_profile(page, account))
            time.sleep(random.uniform(8, 18))

        browser.close()

    enriched = enrich_linkedin(all_items)
    print(f"\nExtracted {len(enriched)} posts across {len(accounts)} accounts.")

    existing = load_existing()
    existing_by_id = {it["id"]: it for it in existing.get("items", [])}
    new_count = sum(1 for it in enriched if it["id"] not in existing_by_id)
    for it in enriched:
        existing_by_id[it["id"]] = it

    merged = prune(list(existing_by_id.values()))
    merged.sort(key=lambda x: x.get("fetched_at", ""), reverse=True)

    output = {
        "last_run": existing.get("last_run"),
        "last_linkedin_run": datetime.now(timezone.utc).isoformat(),
        "item_count": len(merged),
        "new_this_run": new_count,
        "items": merged,
    }
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        import json
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Merged into {DATA_PATH} ({new_count} new items).")
    print("Remember to commit+push site/data.json if you want the team dashboard to show this.")


if __name__ == "__main__":
    main()
