# Architecture

The Rack Report is a static site. GitHub Actions writes JSON files and static project pages into
the repository; GitHub Pages serves the repository; the pages load the JSON in the browser. There
is no server, no database and no AI service (docs/DECISIONS.md, decision 1).

## The hourly loop

```mermaid
flowchart TD
    subgraph Triggers
        chain["previous loop run<br/>gh workflow run update.yml -f chain=true"]
        cron["cron 17 * * * *<br/>(backup)"]
        watch["watchdog.yml every 2 h<br/>data older than 3 h"]
        hand["Run workflow by hand"]
    end
    chain --> gate
    cron --> gate
    watch --> gate
    hand --> gate
    gate{"gate job:<br/>is a loop already running?"}
    gate -- "yes (and not a chain start)" --> skip["skipped"]
    gate -- "no" --> loop
    subgraph loop["loop job: scripts/update_loop.sh, 5 h 40 min"]
        direction TB
        reset["reset to origin/main"] --> fetch["fetch_news.py"]
        fetch -- "exit 75: rate limited" --> wait
        fetch --> hc["healthcheck.py --context update"]
        hc --> tests["pytest tests/"]
        tests --> changed["data_changed.py"]
        changed -- "only timestamps moved" --> wait
        changed --> commit["commit 'Update news data' + push"]
        commit --> wait["sleep until the next hour"]
        wait --> reset
    end
    loop --> next["Start the next loop (always)"]
    next --> chain
```

A failure in the health check or the tests blocks that cycle's commit; the next cycle tries
again from the latest `main`. The loop exits red only if no cycle succeeded.

## Inside fetch_news.py

```mermaid
flowchart LR
    feeds["data/feeds.json<br/>Google News RSS searches"] --> rss["fetch_feed<br/>retries 429 / 5xx"]
    rss --> entry["entry_to_item<br/>clean title, safe link, age"]
    entry --> tag["tag_item"]
    gaz["scripts/gazetteer.json<br/>+ source_states"] --> tag
    tag -- "off topic, foreign,<br/>blocked outlet" --> drop["dropped"]
    tag --> cluster["cluster_items<br/>stories"]
    cluster --> archive["data/archive/YYYY-MM.json<br/>append only"]
    cluster --> news["data/news.json<br/>30 or 90 days, 2.5 MB"]
    cluster --> registry["registry.update"]
    registry --> regjson["data/registry.json"]
    registry --> pages["projects/&lt;id&gt;/index.html<br/>sitemap.xml"]
    news --> status["data/status.json"]
```

`tag_item` decides, with rules only:

| Field | How | Where |
|---|---|---|
| on topic | names a data center, or an operator plus a site word | `ON_TOPIC_RE`, `SITE_RE` |
| U.S. only | a U.S. place, no foreign marker, not a foreign outlet | `FOREIGN_RE`, `FOREIGN_SOURCES`, `us_filter` |
| `category` | first matching topic rule | `CATEGORY_RULES`, `OPINION_LABEL`, `is_cancelled` |
| `state`, places | gazetteer names, ambiguous towns resolved by state context, outlet state last | `find_locations` |
| `companies` (operators) | whole-word, case-sensitive patterns with guards for common words | `COMPANIES`, `ALIASES` |
| `investors`, `builders`, `suppliers`, `utilities` | the same, separate lists | `INVESTORS`, `BUILDERS`, `SUPPLIERS`, `UTILITIES` |
| `capacity_mw`, `investment_usd_b` | figures in the title | `extract_numbers` |
| `name_hint` | "Project X", "X Data Center", "X campus", "X Technology Park" | `name_hint` |
| stage signal | first status rule whose match describes the present | `STATUS_RULES`, `stage_counts` |

## Inside the registry

```mermaid
flowchart TD
    h["project-shaped headline<br/>(place + site word + stage word)"] --> a{"a. same story<br/>already attached?"}
    a -- yes --> attach
    a -- no --> b{"b. code name<br/>(Stargate, Hyperion...)"}
    b -- yes --> attach
    b -- no --> b2{"b2. same project name<br/>in the same state"}
    b2 -- yes --> attach
    b2 -- no --> c{"c. same operator,<br/>same town or county"}
    c -- yes --> attach
    c -- no --> d{"d. state-only headline,<br/>same operator's umbrella"}
    d -- yes --> attach
    d -- no --> e{"e. no operator, same place,<br/>similar title within 60 days"}
    e -- yes --> attach
    e -- no --> f{"f. builder or supplier only,<br/>one record at the place"}
    f -- yes --> attach
    f -- no --> new{"town or county + operator,<br/>code name or figure?"}
    new -- yes --> create["create record<br/>(folds the umbrella)"]
    new -- "state only + operator" --> umb["umbrella record"]
    new -- "builder/supplier only, or nothing" --> none["stays in the news only"]
    attach["attach headline"] --> derive
    create --> derive
    umb --> derive
    derive["derive: replay headlines in date order<br/>status only moves forward;<br/>cancel, revive; events; confidence"] --> ov["apply data/project_overrides.json"]
```

Status moves Announced → Under construction → Operational and never back; Cancelled / Blocked
can be revived by a construction or opening headline. Curated projects (`data/projects.json`)
keep their curated status.

## Watching over it

```mermaid
flowchart LR
    hc6["healthcheck.yml<br/>every 6 h"] --> py["healthcheck.py<br/>data, site, security, no-AI, tests"]
    hc6 --> br["healthcheck_browser.mjs<br/>pages at 390 px and 1280 px, axe"]
    py --> hj["data/health.json"]
    br --> hj
    hj -- fail --> issue["issue 'Health check failed'<br/>(email)"]
    hj -- pass --> close["closes that issue"]
    wd["watchdog.yml every 2 h"] -- "data > 3 h old" --> restart["start update.yml"]
    wd -- "data > 6 h old" --> issue
    wk["weekly.yml Monday 13:00 UTC"] --> sum["issue 'Weekly summary &lt;date&gt;'<br/>closes last week's"]
```

## Files at a glance

| Path | What |
|---|---|
| `scripts/fetch_news.py` | Fetch, tag, cluster, archive, write news.json; all tagging rules |
| `scripts/registry.py` | Project registry, overrides, project pages, sitemap |
| `scripts/update_loop.sh` | The hourly loop run by update.yml |
| `scripts/healthcheck.py`, `scripts/healthcheck_browser.mjs` | Health checks |
| `scripts/no_ai.py` | The ground-rule scanner |
| `scripts/weekly_summary.py` | The Monday summary issue |
| `scripts/data_readme.py` | Field descriptions; generates docs/DATA_DICTIONARY.md |
| `scripts/data_changed.py` | Whether a cycle changed anything worth committing |
| `scripts/retag_archive.py` | Re-tag the whole archive after a rule change |
| `scripts/status_audit.py` | Check the status rules against a stricter reading |
| `scripts/source_states.py`, `scripts/gazetteer_towns.py` | Suggest outlet home states; add GeoNames towns |
| `scripts/backfill_news.py`, `scripts/backfill_report.py` | Fetch older headlines; report on it |
| `scripts/seed_archive.py` | Historical: built the first archive from git history |
| `tests/` | pytest suite; run before every commit |
| `data/` | All data; see docs/DATA_DICTIONARY.md |
| `assets/` | CSS, JavaScript, brand images |
