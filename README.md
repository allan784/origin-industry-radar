markdown
# Origin Fitness — Industry Radar (v1)

A free, self-hosted dashboard that scans UK and international fitness-industry
sources twice daily and tags items into four categories: consumer fitness
trends, consumer equipment trends, gym trends, gym equipment trends. Includes
a "foresight" flag for US/Australian items that haven't shown up in the UK
yet.

Cost to run: £0. It uses GitHub's free tier for hosting (Pages), scheduling
(Actions), and a free SMTP account for the weekly email. No database, no
server to maintain, no App Store.

**What this is not**: a finished intelligence product. It's a rule-based
discovery feed — Google News search results plus Reddit, auto-tagged by
keyword matching. No AI is scoring relevance or writing summaries in v1
(that costs money at scale; see "Upgrade path" below). Treat every item as a
lead to sanity-check, not a verified fact, before it goes in front of a
customer, in a blog post, or in front of the Board.

---

## What's covered, and what deliberately isn't

**Covered automatically:**
- Google News search feeds, UK + US + Australia, per category (free, no key, won't get blocked)
- Reddit public JSON listings for relevant subreddits (r/Fitness, r/homegym, etc.)

**Not covered automatically (known gaps):**
- **LinkedIn** — no free, non-authenticated way to pull this at any real scale without violating their ToS aggressively enough to risk the account/IP getting blocked outright, regardless of who accepts the legal risk. Automated pulls are excluded; see the manual snapshot tool below for the accepted-risk, human-triggered alternative.
- **Paywalled/membership trade journals** (e.g. anything ukactive or UKREPs gate) — if it's public and has an RSS feed or shows up in Google News, it'll appear; if it's behind a login, it won't.
- **Company report and accounts (Companies House)** — not wired in for v1. Free API exists; needs your own free API key (companieshouse.gov.uk/developer) and a bit more build. Flagged as a natural v2 addition.
- **Podcasts** — not covered. No free universal transcript source; would need per-podcast RSS + a transcription step, which isn't free at any volume. v2 candidate if a specific 3-5 podcasts matter enough to justify it.

## How it works

scraper/sources.py - all source config: queries, subreddits, sector keywords
scraper/fetch.py - pulls raw items from Google News RSS + Reddit
scraper/classify.py - rule-based category/sector/region/foresight tagging, dedup
scraper/build_dashboard.py - orchestrator, writes site/data.json (keeps rolling 45-day window)
scraper/digest.py - builds + sends the weekly email summary
scraper/linkedin_login.py - one-time manual login helper (local only)
scraper/linkedin_snapshot.py - manual, on-demand LinkedIn snapshot (local only)
scraper/linkedin_accounts.csv - the 100 accounts to check
site/ - the static dashboard (index.html, style.css, app.js)
.github/workflows/scrape.yml - runs twice daily, updates data.json, publishes to Pages
.github/workflows/weekly-digest.yml - runs weekly, emails the team


## Deploy it (about 15 minutes, all free)

1. **Create a GitHub account** if you don't have one (github.com — free).
2. **Create a new repository**, e.g. `origin-industry-radar`. Set it to **Public**
   (GitHub Pages is free for public repos; private repos need a paid plan for Pages).
   If you don't want it public, use Cloudflare Pages instead (also free, but a different setup step —
   ask me and I'll adjust the workflow).
3. **Upload this whole folder's contents** into the repo, preserving the `scraper/` and `site/` folder structure — do not upload the zip file itself; extract it first and upload its contents.
4. **Enable GitHub Pages**: repo → Settings → Pages → Build and deployment →
   Source → "GitHub Actions". (Not "Deploy from branch" — the workflow handles it.)
5. **Set up the free email account for the digest** (skip this step if you'd
   rather run without email for now — the dashboard works without it):
   - Easiest free option: a Gmail account with an **App Password** (Google
     Account → Security → 2-Step Verification → App Passwords). Don't use your
     normal Gmail password — app passwords are scoped and revocable.
   - In your repo: Settings → Secrets and variables → Actions → New repository secret. Add:
     - `SMTP_HOST` = `smtp.gmail.com`
     - `SMTP_PORT` = `587`
     - `SMTP_USER` = the Gmail address
     - `SMTP_PASSWORD` = the app password
     - `DIGEST_RECIPIENTS` = comma-separated list of the 10 team emails
6. **First run**: repo → Actions tab → "Scan sources and publish dashboard" →
   Run workflow (manual trigger). Takes 1-2 minutes. Once green, your dashboard
   is live at `https://<your-github-username>.github.io/origin-industry-radar/`.
7. Share that URL with the team. No login needed, works on any phone browser.

After that, it runs itself: scans at 06:00 and 18:00 UTC daily, emails a
digest Monday mornings.

## Tuning it

The query list in `scraper/sources.py` is a first pass, not a final answer.
After a week of real output, expect to:
- Drop queries that return mostly noise
- Add named competitor/brand queries (e.g. specific chain names, specific
  equipment manufacturers) once you see what's missing
- Add UK trade press names directly if you find ones with working RSS feeds
  (check `<publication>/feed` or `/rss` — I used Google News as the robust
  default rather than guessing at unverified feed URLs)

## LinkedIn — manual snapshot tool (separate from the automated pipeline)

This does **not** run on a schedule, does **not** run in GitHub Actions, and
does **not** store your LinkedIn password anywhere. It's a script you run
yourself, from your own laptop, when you want an update on named accounts.

**Why it's built this way, not scheduled:** LinkedIn's bot detection reads
"same login, same two times a day, from a datacenter IP, with no mouse
movement" as a textbook automated account. The realistic result of putting
this in GitHub Actions would be your account hitting a security checkpoint or
restriction within days. Running it manually from your own machine, at
irregular times, in small batches, doesn't eliminate the ToS risk you've
accepted, but it removes the specific pattern that gets accounts flagged fast.

**One-time setup (on your own laptop, not this sandbox):**

cd origin-industry-radar/scraper
pip install -r requirements-linkedin.txt
playwright install chromium
python linkedin_login.py

A real browser window opens. Log into LinkedIn yourself (including any 2FA).
Press Enter in the terminal once you're looking at your feed. This saves a
session file (`scraper/.linkedin_session.json`) - already gitignored, never
commit it, treat it like a password.

**Fill in your accounts:** edit `scraper/linkedin_accounts.csv` - replace the
three example rows with your real 100 (name, LinkedIn URL, optional note).

**Run a batch:**

python linkedin_snapshot.py --start 0 --end 20

Do the next 20-30 another day, not all 100 in one sitting - bursty, high-volume
activity from one login is exactly the pattern that gets flagged. The script
already paces itself (8-18 second gaps between profiles) but batching across
days is the bigger lever.

**What you get:** posts pulled from each account's public activity feed,
tagged with a best-effort category guess and merged into the same
`site/data.json` the automated pipeline writes to, under a new "Industry
voices (LinkedIn)" filter on the dashboard, marked with a "manual snapshot"
tag so the team knows it's not from the twice-daily automated scan.

**Known fragility:** LinkedIn's page structure isn't designed to be parsed
and changes without notice. If a profile returns nothing, the script saves
the raw page text to `scraper/.linkedin_raw/<name>.txt` (also gitignored) so
you can check manually rather than the run silently losing that account's
data.

After running it, commit and push `site/data.json` (and only that file - the
session file and raw dumps stay local) so the team dashboard picks up the
new items on the next Pages deploy.

## Upgrade path (needs budget, not built in v1)

- **AI classification/summarisation**: swap the keyword tagging in
  `classify.py` for a call to an LLM per item. Turns "here's 200 headlines" into
  "here's what actually matters and why." Costs API tokens — at this volume,
  likely a few pounds a month, not free, but cheap.
- **Companies House integration**: pull UK gym chain accounts/filings automatically.
- **Push notifications**: would need a proper PWA + service worker + hosting
  that can hold VAPID keys, or a native app. Bigger build, real (if still small) cost.
- **Podcast coverage**: transcription API costs money per episode.

## Legal note

Allan has accepted the legal risk of scraping publicly available sources for
this internal tool. LinkedIn is excluded from *automated* scraping specifically
because the risk there (account/IP blocking, ToS enforcement) is disproportionate
to what a keyword search would return anyway. The manual snapshot tool is a
separate, accepted-risk exception, run by a human, not by unattended automation.
This isn't a legal opinion — if this tool's scope grows or gets used outside
the 10-person team, get that looked at properly.
