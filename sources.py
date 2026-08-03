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
