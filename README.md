# The Rack Report

U.S. data center intelligence: the buildout, tracked in one place. A static site on GitHub Pages whose data is refreshed every three hours by a GitHub Actions job. No server, no API keys, no build step.

Live site: https://therackreport.org/ (custom domain on GitHub Pages; the root `CNAME` file holds the domain and must not be removed or edited)

## Pages

| File | Page | What it does |
|---|---|---|
| `index.html` | Overview | Hero, live metrics, latest major story, headline ticker, project pulse map (lazy-loaded), most active companies, topic mix |
| `newsroom.html` | Newsroom | Every headline with instant filters (company, state, topic, source, today/week/month/90 days), search, save and share; an **Include archive** switch searches the full archive |
| `atlas.html` | Project Atlas | Clustered map of curated and detected U.S. projects, filters, list synced with the map, detail panel with timeline and related headlines; deep links with `#project=ID`, `#company=Name`, `#state=TX` |
| `companies.html` | Companies | Company cards and profiles computed from the data; deep links with `#Name` |
| `learn.html` | Learn | Ten modules from beginner to advanced with diagrams, calculators, quizzes and saved progress |
| `methodology.html` | Methodology | Sources, tagging, detection, limitations, how to report an error |
| `projects.html` | Redirect | Sends old map links to the Atlas |
| `404.html` | Not found | Served by Pages for any missing path; links to the six pages |

Links use clean, root-relative URLs (`/newsroom`, `/atlas`, `/` for the Overview); GitHub Pages serves `newsroom.html` for `/newsroom`. The `.html` files keep their names.
| `robots.txt`, `sitemap.xml` | SEO | Crawl rules and the six pages on https://therackreport.org |

Shared code: `assets/style.css` (all design tokens and components), `assets/app.js` (shell, loader, data loading, helpers), `assets/companies.js` (one-line company descriptions). Each page has its own script in `assets/`. Leaflet and Leaflet.markercluster load from unpkg with subresource integrity; map tiles are OpenStreetMap's standard tiles, darkened with a CSS filter (no API key needed).

Brand files: `assets/mark.svg`, `assets/logo.svg`, `assets/favicon.svg`, `assets/favicon-32.png`, `assets/apple-touch-icon.png` and `assets/og.png`. The PNGs are rendered from the SVGs by `scripts/brand/render.mjs` (optional, needs Node and Playwright).

## How the data runs

```
GitHub Actions (every 3 hours at :17)
  -> scripts/fetch_news.py
     reads  data/feeds.json             Google News RSS searches and Google Alerts feeds
     reads  scripts/gazetteer.json      place names -> coordinates (U.S. and foreign)
     writes data/news.json              headlines with category, state(s), companies, MW/$ figures
     writes data/project_candidates.json projects detected in headlines (U.S. only)
     writes data/archive/YYYY-MM.json   permanent archive by published month, append-only
     writes data/archive/index.json     months available, item counts, earliest/latest dates
  -> commits the JSON files and the archive (never touches CNAME)
GitHub Pages serves the HTML; the pages fetch the JSON in the browser
```

`data/projects.json` holds curated projects and is edited by hand. A project can carry an optional `timeline` array of `{date, event, url}` milestones (date as `YYYY-MM` or `YYYY-MM-DD`), shown in the Atlas detail panel.

### Archive

`data/news.json` is the recent file: 90 days, up to 3,000 headlines. Every headline that passes the U.S. filter is also appended to `data/archive/YYYY-MM.json` for the month it was published; archive files are never trimmed and existing entries are never rewritten. `scripts/seed_archive.py` rebuilt the archive from every version of `data/news.json` in git history and is safe to re-run.

Fields written on each headline: `id, title, link, source, published, feed, category, tags, locations, states, state, county, location_precision, companies, utilities, cluster_id, cluster_title` and, when present, `snippet, capacity_mw, investment_usd_b`. Candidates (rebuilt every run from recent and archived headlines) add `status, location, lat, lon, state, companies, utilities, precision, cluster_id, source, source_url, published`.

Categories: Cancelled / Blocked, New Announcement, Expansion, Construction, Power / Utility, Land Acquisition, Policy / Permits, Deals / Investment, Operations, AI Infrastructure, General.
Statuses: Announced, Planned (curated only), Under construction, Operational, Expansion, Cancelled / Blocked.

### Data quality rules

- **On topic:** the title or description must say data center / data centre / datacenter / hyperscale / colocation, or name a tracked company plus campus / facility / site / megawatt / gigawatt. `blocked_sources` in `data/feeds.json` drops stock-market outlets.
- **Topic order:** Cancelled / Blocked, New Announcement, Construction, Expansion, Land Acquisition, Operations, Deals / Investment, Power / Utility, AI Infrastructure, Policy / Permits (last, and only with a governance phrase).
- **Cancelled / Blocked** is checked before every other topic and status (withdrawn, scrapped, denied, voted down, halted, paused, moratorium passed; "calls for" and "considers" do not count).
- **Locations:** title and RSS description are scanned against `scripts/gazetteer.json` (every U.S. county and parish at its Census centroid, plus townships in the news). `source_states` in `data/feeds.json` maps local outlets to their home state as a last resort. `location_precision` is `city`, `county`, `state` or `source`.
- **Stories:** headlines within 5 days cluster when title-word Jaccard is >= 0.5, or >= 0.3 with the same city/county, or >= 0.3 with the same company and state (union-find; clusters naming different states or places never merge). Each item gets `cluster_id` (earliest member) and `cluster_title` (most precise place, else earliest). The Newsroom shows one card per story, the Atlas one site per story (state-level ones as an approximate bubble per state from zoom 5, folded into cluster circles below), and company counts are stories.
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

## Notes

- Only headlines and short machine-generated summaries are shown; article text is never copied.
- Tags and pins are automatic and can be wrong. See `methodology.html` for limitations and how to report errors.
