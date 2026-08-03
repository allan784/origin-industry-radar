"""
Weekly email digest. Reads site/data.json, pulls items from the last 7 days,
groups by category, sends a plain-text summary email via SMTP.

Requires these GitHub Actions secrets (see README for setup):
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, DIGEST_RECIPIENTS
  (DIGEST_RECIPIENTS = comma-separated email addresses)

Uses SMTP rather than a paid transactional email API so it works with a free
Gmail account + app password, or any other free-tier SMTP provider, without
locking the project to one vendor.
"""
import json
import os
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(HERE, "..", "site", "data.json")

CATEGORY_LABELS = {
    "consumer_fitness_trends": "Consumer fitness trends",
    "consumer_equipment_trends": "Consumer equipment trends",
    "gym_trends": "Gym trends",
    "gym_equipment_trends": "Gym equipment trends",
}


def build_digest_text():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    recent = []
    for it in data.get("items", []):
        try:
            ts = datetime.fromisoformat(it["fetched_at"])
        except Exception:
            continue
        if ts >= cutoff:
            recent.append(it)

    by_cat = {}
    for it in recent:
        by_cat.setdefault(it["category"], []).append(it)

    lines = [f"Origin Fitness Industry Radar — weekly digest", f"{len(recent)} new items this week\n"]
    for cat, label in CATEGORY_LABELS.items():
        cat_items = by_cat.get(cat, [])
        if not cat_items:
            continue
        lines.append(f"\n{label} ({len(cat_items)})")
        lines.append("-" * len(f"{label} ({len(cat_items)})"))
        for it in cat_items[:10]:
            tag = " [FORESIGHT - not yet UK]" if it.get("foresight") else ""
            lines.append(f"- {it['title']}{tag}\n  {it['url']}")
    if not recent:
        lines.append("\nNo new items this week - either a quiet week or the sources need tuning.")

    lines.append("\n\nFull dashboard: see the link shared with the team.")
    lines.append("Rule-based tagging, not human-reviewed - sanity check before quoting externally.")
    return "\n".join(lines)


def send_email(body: str):
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASSWORD"]
    recipients = [r.strip() for r in os.environ["DIGEST_RECIPIENTS"].split(",") if r.strip()]

    msg = MIMEText(body)
    msg["Subject"] = "Origin Fitness Industry Radar — weekly digest"
    msg["From"] = user
    msg["To"] = ", ".join(recipients)

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.sendmail(user, recipients, msg.as_string())
    print(f"Digest sent to {len(recipients)} recipients.")


if __name__ == "__main__":
    text = build_digest_text()
    print(text)  # always printed to Actions log, useful even if email fails
    if os.environ.get("SMTP_HOST"):
        send_email(text)
    else:
        print("\n[info] SMTP_HOST not set - skipping send (local test mode).")
