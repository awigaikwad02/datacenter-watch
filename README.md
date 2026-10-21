# Data Center Watch

A self-updating news board and map for data centers. Static site on GitHub Pages, data refreshed by a GitHub Actions job. No server, no API keys, no cost.

- **index.html**: news feed from Google News RSS searches and Google Alerts RSS, tagged by category, filterable by place and date
- **projects.html**: Leaflet map of curated projects plus sites detected automatically from headlines
- **learn.html**: how a data center works, nine sections with diagrams

## How it runs

```
GitHub Actions (twice daily)
  -> scripts/fetch_news.py
     reads  data/feeds.json          (which feeds to pull)
     reads  scripts/gazetteer.json   (place names -> coordinates)
     writes data/news.json           (the feed)
     writes data/project_candidates.json (projects found in headlines)
  -> commits the two JSON files
GitHub Pages serves the HTML, which fetches the JSON in the browser
```

## Set up (about 10 minutes)

1. **Create the repo and push.** Public repo, so GitHub Pages is free.
   ```bash
   cd datacenter-watch
   git init
   git add .
   git commit -m "Data Center Watch: initial site"
   gh repo create datacenter-watch --public --source=. --push
   ```
2. **Turn on Pages.** Repo Settings, Pages, Source: Deploy from a branch, Branch: `main`, folder `/ (root)`, Save. The site appears at `https://<your-user>.github.io/datacenter-watch/` after a minute.
3. **Let the workflow commit.** Repo Settings, Actions, General, Workflow permissions: choose "Read and write permissions", Save.
4. **Run it once by hand.** Actions tab, "Update data center news", Run workflow. Reload the site when it finishes; the feed fills in.
5. **Add Google Alerts (optional).** At google.com/alerts create an alert (for example `"data center" announced`), click Show options, set Deliver to: RSS feed, create it, then copy the RSS link from the orange icon next to the alert. Paste the URL into the `google_alerts` list in `data/feeds.json` and commit. Add as many alerts as you like.
6. **Curate the map.** Edit `data/projects.json` to add, correct or remove projects. The seed entries are from public reporting and are flagged `verified: false` until you check them.

## Tuning

- Schedule: edit the cron line in `.github/workflows/update.yml` (default 06:17 and 18:17 UTC).
- Searches: edit `google_news` in `data/feeds.json`. Google News search syntax works (`OR`, quotes, `when:7d`).
- Categories: edit `CATEGORY_RULES` in `scripts/fetch_news.py`. First matching rule wins.
- Places: add any city, county or country to `scripts/gazetteer.json` with `[lat, lon, level, display]`.
- Retention: `NEWS_MAX_AGE_DAYS` (60) and `CAND_MAX_AGE_DAYS` (180) in the script.

## Run locally

```bash
pip install -r scripts/requirements.txt
python scripts/fetch_news.py
python -m http.server 8000   # then open http://localhost:8000
```

## Notes

- Google News RSS links go through news.google.com redirects to the publisher; that is normal.
- Category and location tagging is keyword based. Expect some misses; fix the rules rather than the data files, which get rewritten on every run.
- Leaflet and OpenStreetMap tiles load from public CDNs; there is no map API key to manage.
