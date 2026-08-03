name: Scan sources and publish dashboard

on:
  schedule:
    # 06:00 and 18:00 UTC - adjust if you want different local times
    - cron: "0 6 * * *"
    - cron: "0 18 * * *"
  workflow_dispatch: {}   # lets you trigger a manual run from the Actions tab

permissions:
  contents: write
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: false

jobs:
  scan:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r scraper/requirements.txt

      - name: Run scraper and build dashboard
        run: python scraper/build_dashboard.py

      - name: Commit updated data
        run: |
          git config user.name "industry-radar-bot"
          git config user.email "actions@users.noreply.github.com"
          git add site/data.json
          git diff --quiet --cached || git commit -m "Scheduled scan: $(date -u +'%Y-%m-%d %H:%M UTC')"
          git push

      - name: Setup Pages
        uses: actions/configure-pages@v5

      - name: Upload site artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: site

      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
