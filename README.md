# The Rack Report

U.S. data center intelligence: the buildout, tracked in one place. A static site on GitHub Pages whose data is refreshed every hour by a GitHub Actions job. No server, no API keys, no build step.

Live site: https://therackreport.org/ (custom domain on GitHub Pages; the root `CNAME` file holds the domain and must not be removed or edited)

## Pages

| File | Page | What it does |
|---|---|---|
| `index.html` | Overview | Hero, live metrics, latest major story, headline ticker, project pulse map (lazy-loaded), most active companies, topic mix |
| `newsroom.html` | Newsroom | Every headline with instant filters (company, state, topic, source, today/week/month/90 days), search, save and share; an **Include archive** switch searches the full archive |
| `radar.html` | Rack Radar | Clustered map of curated and detected U.S. projects, filters, list synced with the map, detail panel with timeline and related headlines; deep links with `#project=ID`, `#company=Name`, `#state=TX` |
| `companies.html` | Companies | Company cards and profiles computed from the data; deep links with `#Name` |
| `learn.html` | Learn | Ten modules from beginner to advanced with diagrams, calculators, quizzes and saved progress |
| `methodology.html` | Methodology | Sources, tagging, detection, limitations, how to report an error |
| `projects.html` | Redirect | Sends old map links (`#p=ID`) to Rack Radar |
| `atlas.html` | Redirect | Project Atlas was renamed Rack Radar; keeps `/atlas#project=ID` links working |
| `404.html` | Not found | Served by Pages for any missing path; links to the six pages |

Links use clean, root-relative URLs (`/newsroom`, `/radar`, `/` for the Overview); GitHub Pages serves `newsroom.html` for `/newsroom`. The `.html` files keep their names.
| `robots.txt`, `sitemap.xml` | SEO | Crawl rules and the six pages on https://therackreport.org |

Shared code: `assets/style.css` (all design tokens and components), `assets/app.js` (shell, loader, data loading, helpers), `assets/companies.js` (one-line company descriptions). Each page has its own script in `assets/`. Leaflet and Leaflet.markercluster load from unpkg with subresource integrity; map tiles are OpenStreetMap's standard tiles, darkened with a CSS filter (no API key needed).

Brand files: `assets/mark.svg`, `assets/logo.svg`, `assets/favicon.svg`, `assets/favicon-32.png`, `assets/apple-touch-icon.png` and `assets/og.png`. The PNGs are rendered from the SVGs by `scripts/brand/render.mjs` (optional, needs Node and Playwright).

## How the data runs

```
GitHub Actions (every hour at :17)
  -> scripts/fetch_news.py
     reads  data/feeds.json             Google News RSS searches and Google Alerts feeds
     reads  scripts/gazetteer.json      place names -> coordinates (U.S. and foreign)
     writes data/news.json              headlines with category, state(s), companies, MW/$ figures
     reads  data/projects.json          curated projects (edited by hand)
     reads  data/project_overrides.json corrections to the registry (edited by hand)
     writes data/registry.json          permanent project registry (scripts/registry.py)
     writes projects/<id>/index.html    one static page per visible project, plus sitemap.xml
     writes data/status.json            last run: feeds_total, feeds_ok, items_total, items_new
     writes data/archive/YYYY-MM.json   permanent archive by published month, append-only
     writes data/archive/index.json     months available, item counts, earliest/latest dates
  -> commits the JSON files and the archive, only when item or cluster ids changed
     (scripts/data_changed.py; never touches CNAME)
GitHub Pages serves the HTML; the pages fetch the JSON in the browser
```

`data/projects.json` holds curated projects and is edited by hand. A project can carry an optional `timeline` array of `{date, event, url}` milestones (date as `YYYY-MM` or `YYYY-MM-DD`), shown in Rack Radar detail panel.

### Project registry

`data/registry.json` is the permanent list of projects, written by `scripts/registry.py` (called from the fetcher) and never trimmed: records are hidden, not deleted. Curated projects are re-imported from `data/projects.json` every run and their fields (name, place, status, figures, notes, timeline) win.

Each run, every project-shaped headline (a U.S. place, a site word and a stage word) is attached to the first record that matches, in this order: (a) a headline from the same story cluster is already attached; (b) a project code name in the title (Stargate, Hyperion, Prometheus, Fairwater, Project Rainier, Colossus, Project Matador, any curated name of 6+ characters, any alias) matches a record's name or aliases in the same state; (c) same company and the same county or city; (d) same company and state, when the record is known only to the state; (e) no company on either side, the same city or county and title-word Jaccard >= 0.4 within 60 days. With no match, a new record is created when the headline is at city or county precision and names a tracked company, a code name, a MW/GW figure or a dollar figure. State-only headlines with a company go to one umbrella record per company and state ("Amazon, North Carolina (site not yet named)"), which is folded into the first named site for that company and state when one appears. Everything else stays in the news only.

Status, `status_history`, `events`, figures, `first_seen`/`last_news`, `sources_count` and `confidence` are rebuilt every run by replaying the record's headlines in date order: Announced < Under construction < Operational only moves forward; Cancelled / Blocked adds a Cancelled event and a later construction or operational headline adds a Revived event; Expansion, Approval and Power deal are events and never change status. Confidence is high for a tracked company + city/county + 2 or more outlets, medium for a company or figure + city/county, low otherwise (umbrellas are always low).

Self-test: `python scripts/registry.py --selftest` (also run by the health check). One-time backfill from the archive: `python scripts/registry.py --backfill`. Rebuild pages only: `python scripts/registry.py --pages`.

### Registry overrides

`data/project_overrides.json` holds `{"operations": [ ... ]}`, applied in order after matching on every run. Each operation is idempotent, so they stay in the file:

| Operation | Effect |
|---|---|
| `{"op": "merge", "from": ID, "into": ID}` | Moves all headlines (and so history and events) into `into`; `from` is hidden with `merged_into` set and later headlines follow it. |
| `{"op": "rename", "id": ID, "name": "New name"}` | Sets the display name. |
| `{"op": "set_status", "id": ID, "status": STATUS, "date": "YYYY-MM-DD"}` | Forces the status at that date (forward or backward); later headlines continue from there. STATUS is Announced, Planned, Under construction, Operational or Cancelled / Blocked. |
| `{"op": "set_location", "id": ID, "lat": N, "lon": N, "location": "Place, State, US", "precision": "city"}` | Moves the pin; city or county precision turns an umbrella into a named site. |
| `{"op": "hide", "id": ID}` | Hides a record that is not a project; it keeps collecting its story's headlines. |
| `{"op": "alias", "id": ID, "alias": "Code name"}` | Adds a name that matching rule (b) will look for in headlines. |
| `{"op": "split", "id": ID, "headline_ids": [ID, ...], "new_id": ID}` | Moves those headlines into a new record (same place and companies; rename or relocate it with further operations). |

### Project pages

Every visible record gets a static page at `/projects/<id>/` (no JavaScript; map thumbnail is an OpenStreetMap tile), listed in `sitemap.xml`. If there are more than 2,000 visible records the build switches to one page per state (`/projects/state-xx/`). The pages must stay under 5 MB in total (checked by the health check).

### Archive

`data/news.json` is the recent file: 90 days, up to 3,000 headlines. Every headline that passes the U.S. filter is also appended to `data/archive/YYYY-MM.json` for the month it was published; archive files are never trimmed, existing entries are never rewritten, and a headline id appears in only one month. Headlines that today's rules reject keep their entry with `"filtered": true` and are hidden on the site. `scripts/seed_archive.py` rebuilt the archive from every version of `data/news.json` in git history and is safe to re-run.

Fields written on each headline: `id, title, link, source, published, feed, category, tags, locations, states, state, county, location_precision, companies, utilities, cluster_id, cluster_title` and, when present, `snippet, capacity_mw, investment_usd_b`.

Categories: Cancelled / Blocked, New Announcement, Expansion, Construction, Power / Utility, Land Acquisition, Policy / Permits, Deals / Investment, Operations, AI Infrastructure, General.
Registry statuses: Announced, Planned (curated only), Under construction, Operational, Cancelled / Blocked (Expansion is an event).

### News backfill

`scripts/backfill_news.py` (manual, or the **Backfill news** workflow: Actions → Backfill news → Run workflow with `start`, `end`, `window_days`) fills the archive with older headlines from Google News RSS only, using the same `google_news_url()` builder with `after:`/`before:` date operators and one query per lifecycle stage (operational in two halves, construction, announced in 7-day windows, cancelled, hyperscaler sweep). Every headline goes through `fetch_news.entry_to_item()`, the same path as the hourly run, and is appended to the archive by published month; `data/news.json` is never touched. Requests are 2 to 3 seconds apart with 3 tries on 429/5xx; the run stops after 10 failures in a row. Google keeps only the first 32 words of a query, so the date operators come first; a window that returns 100 results (the cap) is split in half down to one day, and headlines more than a week outside their window are dropped. Progress is saved to `data/backfill_progress.json` after every window and `--resume` continues from there; the workflow commits every 20 windows, then rebuilds the registry from the whole archive (`python scripts/registry.py --backfill`) and writes `BACKFILL.md`, `data/backfill_report.json` and `data/registry_review.json` (`python scripts/backfill_report.py`). If the first month returns nothing at all, the script stops with exit code 3 instead of trying anything else.

### Data quality rules

- **On topic:** the title or description must say data center / data centre / datacenter / hyperscale / colocation, or name a tracked company plus campus / facility / site / megawatt / gigawatt. `blocked_sources` in `data/feeds.json` drops stock-market outlets.
- **Topic order:** Cancelled / Blocked, New Announcement, Construction, Expansion, Land Acquisition, Operations, Deals / Investment, Power / Utility, AI Infrastructure, Policy / Permits (last, and only with a governance phrase).
- **Cancelled / Blocked** is checked before every other topic and status (withdrawn, scrapped, denied, voted down, halted, paused, moratorium passed; "calls for" and "considers" do not count).
- **Locations:** title and RSS description are scanned against `scripts/gazetteer.json` (every U.S. county and parish at its Census centroid, plus townships in the news). `source_states` in `data/feeds.json` maps local outlets to their home state as a last resort. `location_precision` is `city`, `county`, `state` or `source`.
- **Stories:** headlines within 5 days cluster when title-word Jaccard is >= 0.5, or >= 0.3 with the same city/county, or >= 0.3 with the same company and state (union-find; clusters naming different states or places never merge). Each item gets `cluster_id` (earliest member) and `cluster_title` (most precise place, else earliest). The Newsroom shows one card per story and company counts are stories. On Rack Radar, projects known only to the state are "Location unavailable": hidden by default, and with that filter on shown as one bubble per state (folded into cluster circles below zoom 5) that lists its projects when selected.
- **U.S. filter:** every gazetteer entry has a country code; headlines whose only places are non-U.S. are dropped, and `FOREIGN_SOURCES` outlets need a U.S. place or state in the title.
- **Archive re-tag:** `scripts/retag_archive.py` re-applies the current rules to `data/archive/*.json`, keeping ids; rejected headlines stay, marked `"filtered": true`, and the site hides them.
- **Fetching:** 429 and 5xx responses are retried 3 times with exponential backoff; the script exits non-zero if every feed returned nothing.

## Set up

1. Push this repo to GitHub as a public repository.
2. Settings → Pages → Source: Deploy from a branch, branch `main`, folder `/ (root)`. Custom domain: `therackreport.org` (DNS: four A records to 185.199.108–111.153 and a `www` CNAME to `awigaikwad02.github.io`).
3. Settings → Actions → General → Workflow permissions: Read and write permissions.
4. Actions → "Update data center news" → Run workflow once.

## Tuning

- Searches: `google_news` in `data/feeds.json`. Add Google Alerts RSS URLs to `google_alerts`.
- Topics: `CATEGORY_RULES` in `scripts/fetch_news.py` (first match wins).
- Companies: `COMPANIES` and `ALIASES` in the script, plus a description in `assets/companies.js` with the same name.
- U.S. filter: `FOREIGN_RE` and `FOREIGN_SOURCES` in the script.
- Places: `scripts/gazetteer.json`, `name: [lat, lon, level, display, country]` (or a list of those for a county name shared by several states); U.S. displays end in `, US`.
- Retention: `NEWS_MAX_AGE_DAYS` (90), `NEWS_MAX_ITEMS` (3000), `CAND_MAX_AGE_DAYS` (180) and `CAND_MAX_ITEMS` (800). Story grouping: `CLUSTER_DAYS` (5), `CLUSTER_STRONG` (0.5) and `CLUSTER_WEAK` (0.3).

## Run and test locally

```bash
pip install -r scripts/requirements.txt
python scripts/fetch_news.py                       # fetch and rebuild the data files
python scripts/fetch_news.py --no-fetch            # re-tag stored data after changing rules
python scripts/fetch_news.py --sample scripts/sample_feed.xml --out /tmp/rack-test   # offline test (copies the archive, never touches data/)
python scripts/seed_archive.py                     # (re)seed data/archive from git history
python -m http.server 8000                         # then open http://localhost:8000
```

## Health checks

- `python scripts/healthcheck.py`: pipeline, data integrity, internal links, sitemap, metadata, CNAME and security checks. Prints a table, writes `data/health.json`, exits 1 on any failure. `--context update` is the lighter gate the hourly data job runs before committing (a failure blocks the commit).
- `node scripts/healthcheck_browser.mjs` (needs `npm install --no-save playwright @axe-core/playwright` and `npx playwright install chromium`): loads every page at 390px and 1280px on a Pages-like local server and checks console errors, CSP violations, links, the Rack Radar map, the freshness badge and axe-core accessibility. Results are merged into `data/health.json`.
- `.github/workflows/healthcheck.yml` runs both daily at 07:23 UTC (and on demand), commits `data/health.json`, and keeps one "Health check failed" issue open while anything fails; it closes the issue on the next passing run. The Methodology page shows the latest result.
- `HEALTH.md` holds the most recent full audit.

## Notes

- Only headlines and short machine-generated summaries are shown; article text is never copied.
- Tags and pins are automatic and can be wrong. See `methodology.html` for limitations and how to report errors.
