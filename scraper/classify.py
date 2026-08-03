"""
Rule-based classification. No AI calls in v1 - this is deliberately dumb,
transparent, and free. It won't catch nuance or judge relevance the way a
human analyst would; it will catch obvious keyword matches. Treat the
"sector" tag especially as a rough first pass, not a verdict.

Upgrade path (not built in v1, needs budget/API key):
  swap `tag_sectors()` for a call to an LLM classifier once there's budget
  for it - the item shape (title/summary/url) is already the right input.
"""
import hashlib
import re
from datetime import datetime, timezone

from sources import MARKET_SECTORS

FOREIGN_REGIONS = {"us", "au"}


def _hash_url(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def tag_sectors(text: str):
    text_l = text.lower()
    hits = []
    for sector, keywords in MARKET_SECTORS.items():
        if any(kw in text_l for kw in keywords):
            hits.append(sector)
    return hits or ["unclassified"]


def is_foresight(item: dict) -> bool:
    """Flag items from abroad as 'not yet in the UK' foresight candidates."""
    return item.get("region") in FOREIGN_REGIONS


def dedupe(items: list) -> list:
    seen = set()
    out = []
    for item in items:
        key = item.get("url") or item.get("title")
        h = _hash_url(key)
        if h in seen:
            continue
        seen.add(h)
        out.append(item)
    return out


def enrich(category: str, items: list) -> list:
    enriched = []
    for item in items:
        text = f"{item.get('title','')} {item.get('summary','')}"
        item["category"] = category
        item["sectors"] = tag_sectors(text)
        item["foresight"] = is_foresight(item)
        item["fetched_at"] = datetime.now(timezone.utc).isoformat()
        item["id"] = _hash_url(item.get("url") or item.get("title", ""))
        enriched.append(item)
    return dedupe(enriched)

scraper/sources.py:

python
"""
Source configuration for the Origin Fitness Industry Radar.

v1 scope (per Allan, 31 July 2026):
  - Consumer fitness trends
  - Consumer equipment trends
  - Gym trends (commercial)
  - Gym equipment trends (commercial)

Design choice: rather than guessing at individual publishers' RSS paths (many
trade titles don't publish reliable feeds, or move them), v1 uses Google News
RSS search feeds as the primary mechanism. This is free, requires no API key,
won't get blocked, and lets us target category + region precisely via query
strings. It's a breadth-first net, not a hand-picked list of "best" sources -
expect noise, and expect to tune the queries after the first couple of weeks
of real output.

Supplemented by:
  - Reddit's public read-only JSON endpoints (no auth, no login-wall) for
    consumer sentiment/community signal.
  - Companies House free API as an optional add-on for UK company accounts
    data (requires the user's own free API key - see README). Not wired into
    v1 by default.

KNOWN GAPS (flagged, not silently dropped):
  - LinkedIn: no free, ToS-compliant, non-authenticated way to pull this at
    scale. Excluded from automated v1. Recommend a manual monthly check of
    named competitor/industry-body LinkedIn pages instead.
  - ukactive / UKREPs / paywalled trade journals: where these publish public
    RSS we pick it up via Google News; where content sits behind membership,
    it will not appear here. That's a real coverage gap, not a bug.
"""

REGIONS = {
    "uk": {"gl": "GB", "ceid": "GB:en", "hl": "en-GB", "label": "UK"},
    "us": {"gl": "US", "ceid": "US:en", "hl": "en-US", "label": "USA"},
    "au": {"gl": "AU", "ceid": "AU:en", "hl": "en-AU", "label": "Australia"},
}

MARKET_SECTORS = {
    "local_authority": ["local authority", "council leisure", "council-run gym", "public leisure centre", "leisure trust"],
    "independent_gym": ["independent gym", "boutique gym", "indie gym", "single-site gym"],
    "chain_gym": ["puregym", "the gym group", "david lloyd", "virgin active", "anytime fitness", "planet fitness",
                  "f45", "third space", "nuffield health", "everyone active", "better gym", "energie fitness"],
    "strength_conditioning": ["s&c studio", "strength and conditioning", "strength & conditioning", "performance studio",
                              "crossfit box", "powerlifting gym"],
    "budget_gym": ["budget gym", "low-cost gym", "discount gym"],
    "hotel_corporate": ["hotel gym", "corporate gym", "workplace gym", "office gym"],
    "home_fitness": ["home gym", "home workout", "connected fitness", "smart home gym"],
}

CATEGORY_QUERIES = {
    "consumer_fitness_trends": {
        "uk": ["fitness trend UK gym-goers", "workout trend UK 2026", "fitness class trend UK"],
        "us": ["fitness trend 2026 America", "workout trend US gym-goers"],
        "au": ["fitness trend Australia gym-goers"],
    },
    "consumer_equipment_trends": {
        "uk": ["home fitness equipment trend UK", "wearable fitness tech UK consumer"],
        "us": ["home fitness equipment trend US", "connected fitness equipment America"],
        "au": ["home fitness equipment trend Australia"],
    },
    "gym_trends": {
        "uk": ["UK gym chain news", "UK health club membership trend", "gym operator UK news"],
        "us": ["US gym chain news", "American health club trend"],
        "au": ["Australia gym chain news"],
    },
    "gym_equipment_trends": {
        "uk": ["commercial gym equipment UK", "health club equipment supplier UK"],
        "us": ["commercial gym equipment US", "fitness equipment manufacturer America"],
        "au": ["commercial gym equipment Australia"],
    },
}

REDDIT_SOURCES = {
    "consumer_fitness_trends": ["Fitness", "naturalbodybuilding", "loseit"],
    "consumer_equipment_trends": ["homegym", "gym_equipment"],
    "gym_trends": ["personaltraining"],
    "gym_equipment_trends": ["homegym"],
}

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl={hl}&gl={gl}&ceid={ceid}"
REDDIT_JSON = "https://www.reddit.com/r/{sub}/top.json?limit=15&t=week"
