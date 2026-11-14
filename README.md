# The Rack Report

U.S. data center intelligence: the buildout, tracked in one place. A static site on GitHub Pages
whose data is refreshed every hour by GitHub Actions. No server, no build step, no API keys.

Live site: https://therackreport.org/ (custom domain on GitHub Pages; the root `CNAME` file holds
the domain and must never be removed or edited).

## Ground rule: no AI in the pipeline

The site never depends on Claude, Claude Code, or any AI or LLM service to run. There are no calls
to the Anthropic, OpenAI or any model API anywhere in the pipeline, no API keys, and no secrets
beyond GitHub's own `GITHUB_TOKEN`. Fetching, tagging, company and place detection, status
changes, matching, clustering, health checks and the weekly summary are all deterministic code
that GitHub Actions runs on its own. Claude Code may edit the rules and data files, but if it
disappeared tomorrow the site would keep updating and tagging exactly as it does today.

This is enforced: `scripts/no_ai.py` (run by the health check and `tests/test_no_ai.py`) fails if
any file imports or calls an AI SDK or model API, names an API key, lists an AI package, or if any
workflow uses a secret other than `GITHUB_TOKEN`. Do not add an AI step "to improve tagging":
improve the rules and add a test instead. Why: [docs/DECISIONS.md](docs/DECISIONS.md), decision 1.

## Documentation

| Document | Read it when |
|---|---|
| [docs/RUNBOOK.md](docs/RUNBOOK.md) | Something needs fixing: data stopped updating, a health check failed, a project record is wrong, a backfill |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | You want to see how the pieces fit (diagrams of the hourly loop, the tagger and the registry) |
| [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md) | You need to know what a file or field means (generated from `scripts/data_readme.py`) |
| [docs/DECISIONS.md](docs/DECISIONS.md) | You wonder why something is done the way it is, before changing it |
| [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) | You are about to change a rule, a page or a workflow |
| [docs/REVIEW_PROPOSALS.md](docs/REVIEW_PROPOSALS.md) | Proposed fixes to project records that wait for a human decision |
| [HEALTH.md](HEALTH.md), [SECURITY.md](SECURITY.md), [BACKFILL.md](BACKFILL.md) | The health check, security notes, and the last news backfill |

## Pages

| File | Page | What it does |
|---|---|---|
| `index.html` | Overview | Live metrics, latest major story, headline ticker, project pulse map, most active companies, topic mix |
| `newsroom.html` | Newsroom | Every headline with instant filters (company, state, utility, investor, builder, supplier, source, topic, time), search, save and share; older months load from the archive on demand |
| `radar.html` | Rack Radar | Clustered map of curated and detected projects, filters, list synced with the map, detail panel with status timeline and headlines; deep links `#project=ID`, `#company=Name`, `#state=TX` |
| `companies.html` | Companies | Operator cards and profiles computed from the data, and "Who builds and equips them" (investors, builders, suppliers); deep links `#Name` |
| `learn.html` | Learn | Ten modules from beginner to advanced |
| `methodology.html` | Methodology | Sources, how to read the data, tagging, detection, limitations, how to report an error |
| `projects/<id>/` | Project pages | One static page per visible registry record (written by `scripts/registry.py`) |
| `atlas.html`, `projects.html` | Redirects | Project Atlas was renamed Rack Radar; old `/atlas#project=ID` and `#p=ID` links keep working |
| `404.html` | Not found | Served by Pages for any missing path |

Links use clean root-relative URLs (`/newsroom`, `/radar`); GitHub Pages serves `newsroom.html`
for `/newsroom`. Shared code: `assets/style.css` (design tokens and components), `assets/app.js`
(shell, data loading, helpers), `assets/companies.js` (operator descriptions); each page has its
own script in `assets/`. Leaflet loads from unpkg with subresource integrity; tiles are
OpenStreetMap's. Asset URLs carry a version (`?v=rr21`): bump it in every page and in
`scripts/registry.py` when CSS or JS changes.

## How the data runs (short version)

```
GitHub Actions: update.yml runs scripts/update_loop.sh for 5h40m, once an hour:
  fetch_news.py   Google News RSS (data/feeds.json) -> tag -> cluster -> archive -> data/news.json
  registry.py     project-shaped headlines -> data/registry.json -> projects/<id>/ pages, sitemap.xml
  healthcheck.py --context update, then pytest   (a failure blocks the commit)
  data_changed.py -> commit "Update news data <time>" and push
then it starts its own next run. Backups: an hourly cron at :17 and watchdog.yml every 2 hours.
GitHub Pages serves the HTML; the pages fetch the JSON in the browser.
```

Every step is described, with diagrams, in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Workflows

| Workflow | When | What |
|---|---|---|
| `update.yml` | Self-chaining loop, hourly backup cron | The data refresh (above) |
| `watchdog.yml` | Every 2 hours | Data older than 3 h: restart the loop. Older than 6 h: open or update the "Health check failed" issue |
| `healthcheck.yml` | Every 6 hours | Full health check (Python and browser), commits `data/health.json`, opens or closes the "Health check failed" issue |
| `weekly.yml` | Mondays 13:00 UTC | Opens the "Weekly summary" issue (and closes last week's) |
| `backfill.yml` | By hand | Fetches older headlines into the archive; see the runbook |

You get an email only when an issue opens: "Health check failed" (something is broken) or the
weekly summary (a digest with anything that needs your decision).

## Run and test locally

```bash
pip install -r scripts/requirements.txt
python -m pytest -q tests                          # tagging, registry, no-AI and docs tests
python scripts/healthcheck.py --no-write           # the health check, without writing data/health.json
python scripts/fetch_news.py --sample scripts/sample_feed.xml --out /tmp/rack-test   # offline run, never touches data/
python scripts/fetch_news.py --no-fetch            # re-tag stored headlines after changing rules
python scripts/retag_archive.py && python scripts/registry.py --backfill   # re-tag the whole archive and replay it
python -m http.server 8000                         # then open http://localhost:8000
```

## Set up (already done for therackreport.org)

1. Public repository; Settings → Pages → Deploy from a branch, `main`, `/ (root)`; custom domain `therackreport.org`.
2. Settings → Actions → General → Workflow permissions: Read and write.
3. Actions → "Update data center news" → Run workflow once; the loop keeps itself going from there.

## Notes

- Only headlines, outlet names and links are stored; article text is never copied.
- Tags, places and statuses are automatic and can be wrong; the Methodology page explains how to read them.
- Place data: U.S. Census county centroids and GeoNames towns (CC BY 4.0, geonames.org).
