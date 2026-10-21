# Data Center Watch

A self-updating news board, map and course about U.S. data centers. Static site on GitHub Pages, data refreshed by a GitHub Actions job. No server, no API keys, no cost.

- **index.html**: U.S. data center news from Google News RSS and Google Alerts, tagged by category, state and company. Featured story, state tile map, 30-day volume chart, filters, search, saved stories.
- **projects.html**: interactive Leaflet map of U.S. projects on a vector state map with shading by project count or GW, clustered pins sized by capacity, filters, and a detail panel with related headlines. Sites detected from headlines appear as ringed pins.
- **companies.html**: the hyperscalers, AI labs, GPU clouds, developers, investors and energy partners behind the build-out, with their projects, capacity, states and news mentions.
- **learn.html**: a 14-lesson course from scratch to advanced with diagrams, quizzes, saved progress and interactive tools (campus scale, power chain and outage simulation, rack density, redundancy, PUE/WUE calculator, AI cluster sizing, project timeline).

The site covers the United States only. `scripts/fetch_news.py` drops stories about other countries and tags each story with the states it mentions. Light and dark themes follow the system setting and can be toggled.

## How it runs

```
GitHub Actions (twice daily)
  -> scripts/fetch_news.py
     reads  data/feeds.json          (which feeds to pull)
     reads  scripts/gazetteer.json   (place names -> coordinates)
     writes data/news.json           (the feed, U.S. only, tagged with states)
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
6. **Curate the map and companies.** Edit `data/projects.json` to add, correct or remove projects (each needs an `id`, a two-letter `state`, and `companies` slugs from `data/companies.json`). Edit `data/companies.json` to add companies; `aliases` are the names matched in headlines. The seed entries are from public reporting and are flagged `verified: false` until you check them.

## Tuning

- Schedule: edit the cron line in `.github/workflows/update.yml` (default 06:17 and 18:17 UTC).
- Searches: edit `google_news` in `data/feeds.json`. Google News search syntax works (`OR`, quotes, `when:7d`).
- Categories: edit `CATEGORY_RULES` in `scripts/fetch_news.py`. First matching rule wins.
- Places: add any city, county or country to `scripts/gazetteer.json` with `[lat, lon, level, display]`. U.S. entries end in `, US`; foreign entries are used to filter stories out.
- U.S. filter: `FOREIGN_RE` and `FOREIGN_SOURCES` in the script. Run `python scripts/fetch_news.py --no-fetch` to re-tag the existing data after editing rules.
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
- Leaflet, the marker cluster plugin, topojson-client and the U.S. state boundaries (us-atlas) are vendored in `assets/vendor/` and `data/us-states.json`. Street labels load from CARTO's public basemap tiles; there is no map API key to manage.
