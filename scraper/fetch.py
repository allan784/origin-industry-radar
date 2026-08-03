python
"""
Fetchers: turn source config into a flat list of raw items.
Each item: {title, url, summary, published, source, source_type}
Deliberately defensive - a single dead feed or rate-limited endpoint should
never take down the whole run.
"""
import time
import urllib.parse
import feedparser
import requests

from sources import (
    GOOGLE_NEWS_RSS, REDDIT_JSON, CATEGORY_QUERIES, REDDIT_SOURCES, REGIONS
)

USER_AGENT = "OriginFitnessIndustryRadar/1.0 (internal tool; contact: allan@originfitness.com)"
TIMEOUT = 15


def fetch_google_news(query: str, region_key: str):
    region = REGIONS[region_key]
    url = GOOGLE_NEWS_RSS.format(
        query=urllib.parse.quote(query),
        hl=region["hl"], gl=region["gl"], ceid=region["ceid"],
    )
    items = []
    try:
        feed = feedparser.parse(url, request_headers={"User-Agent": USER_AGENT})
        for e in feed.entries[:20]:
            items.append({
                "title": e.get("title", "").strip(),
                "url": e.get("link", ""),
                "summary": e.get("summary", "")[:500],
                "published": e.get("published", ""),
                "source": e.get("source", {}).get("title", "Google News") if isinstance(e.get("source"), dict) else "Google News",
                "source_type": "news",
                "query": query,
                "region": region_key,
            })
    except Exception as exc:
        print(f"[warn] google news fetch failed for '{query}' ({region_key}): {exc}")
    return items


def fetch_reddit(subreddit: str):
    items = []
    try:
        url = REDDIT_JSON.format(sub=subreddit)
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        for child in data.get("data", {}).get("children", []):
            d = child.get("data", {})
            if d.get("stickied"):
                continue
            items.append({
                "title": d.get("title", "").strip(),
                "url": f"https://www.reddit.com{d.get('permalink', '')}",
                "summary": (d.get("selftext") or "")[:500],
                "published": time.strftime("%a, %d %b %Y", time.gmtime(d.get("created_utc", time.time()))),
                "source": f"r/{subreddit}",
                "source_type": "reddit",
                "query": subreddit,
                "region": "uk_or_global",
                "score": d.get("score", 0),
            })
    except Exception as exc:
        print(f"[warn] reddit fetch failed for r/{subreddit}: {exc}")
    return items


def fetch_all():
    """Returns dict: category -> list of raw items."""
    results = {cat: [] for cat in CATEGORY_QUERIES}

    for category, region_queries in CATEGORY_QUERIES.items():
        for region_key, queries in region_queries.items():
            for q in queries:
                results[category].extend(fetch_google_news(q, region_key))
                time.sleep(1)

    for category, subs in REDDIT_SOURCES.items():
        for sub in subs:
            results[category].extend(fetch_reddit(sub))
            time.sleep(1)

    return results


if __name__ == "__main__":
    data = fetch_all()
    for cat, items in data.items():
        print(f"{cat}: {len(items)} raw items")
