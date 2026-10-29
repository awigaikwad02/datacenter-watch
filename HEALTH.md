# The Rack Report: health check

> **Current state (2026-10-29).** The audit below is the original one from 2026-10-25 and is kept
> as a record. Since then:
> - The health check runs every **6 hours** (not daily) and also checks: the no-AI ground rule
>   (`scripts/no_ai.py`), the pytest suite (`tests/`), per-workflow permissions, General under 10%
>   and Policy / Permits under 20% of headlines, and at least **55%** of headlines located (now ~59%
>   of recent headlines, 62% of the archive). Freshness allows **3 hours**.
> - "Needs attention" item 1 (unreliable scheduled runs) is solved without a token: the update
>   workflow is a self-sustaining hourly loop, with a backup cron and a 2-hourly watchdog
>   (docs/DECISIONS.md, decision 2). Items 2 to 4 still stand.
> - Project Atlas is now Rack Radar (`/radar`); the browser check also tests the old `/atlas` redirect.
> - What to do when a check fails: docs/RUNBOOK.md.

Audit run on 2026-10-25, 21:09 to 21:25 UTC, against `main` (data commit `22c6aab`, then the fixes listed below).
"Before" is the first run of each check. "Now" is after the fixes.

The checks are repeatable:
- `python scripts/healthcheck.py`
- `node scripts/healthcheck_browser.mjs`
- the daily **Health check** workflow at 07:23 UTC

The latest result is on the Methodology page and in `data/health.json`.

## 1. Results

| Area | Check | Before | Now | Measured value |
|---|---|---|---|---|
| Pipeline | Last 10 workflow runs | PASS | PASS | 10/10 succeeded, average 28 s. After the fixes: 8/9 succeeded plus 1 Pages deploy cancelled because a newer push replaced it |
| Pipeline | Last "Update news data" commit within 2 h | PASS | PASS | 1 h 31 m old (19:41 UTC). See Needs attention #1: scheduled runs come every 3 to 5 h |
| Pipeline | `data/status.json` feeds_ok = feeds_total | PASS | PASS | 12 of 12 feeds, 11 new headlines in the last run |
| Pipeline | Fetcher on `scripts/sample_feed.xml` | PASS | PASS | exit 0; news, candidates and status files parse |
| Data | All data files parse as JSON | PASS | PASS | 6/6 (news, candidates, projects, status, archive month, archive index) |
| Data | News items have every field; http(s) links; valid dates | PASS | PASS | 1,648 items, 0 problems |
| Data | News ids unique; no future dates | PASS | PASS | 0 duplicates, 0 future dates |
| Data | `news.json` "updated" within 2 h | PASS | PASS | 1 h 31 m old |
| Data | No category above 30% | PASS | PASS | General 389 (23.6%), Policy / Permits 376, New Announcement 238, Power / Utility 206, AI Infrastructure 164, Cancelled / Blocked 92, Deals / Investment 78, Construction 61, Expansion 30, Operations 8, Land Acquisition 6 |
| Data | At least 50% of headlines have a location | PASS | PASS | 854 of 1,648 (51.8%); 195 (11.8%) name a company |
| Data | Archive matches index and covers `news.json` | PASS | PASS | 1 month file, index matches, 1,737 headlines, no duplicate ids, every news id archived, earliest 2026-10-14 |
| Data | Candidate pins: inside the U.S. box, valid status, source_url | PASS | PASS | 241 pins, 0 problems (box includes Alaska, Hawaii and the territories) |
| Data | Curated `projects.json`: fields, no duplicates, timelines complete | PASS | PASS | 49 projects, 0 problems |
| Data | No headline located outside the U.S. | PASS | PASS | 0 items |
| Data | "Projects announced this month" leaves out Cancelled / Blocked | PASS | PASS | Python recomputed 147 = page shows 147; 29 cancelled or blocked sites this month correctly left out |
| Site | 6 pages + 404 at 390 px and 1280 px: console errors, CSP violations, failed requests | PASS | PASS | 14 loads, 0 / 0 / 0. The site sets no CSP, so 0 violations means little |
| Site | Overview stat counters | FAIL | PASS | The live page showed "-2,397" for 1,286 (first animation frame before start time). Found on the live page, not one of the listed checks |
| Site | Internal links resolve, use clean URLs, appear in sitemap | PASS | PASS | 18 links in the source, 6 rendered pages; 0 broken, 0 with `.html` |
| Site | Sitemap entries return 200 | PASS | PASS | 6/6 locally and on the live site |
| Site | Canonical and og:url clean; og.png returns 200 | PASS | PASS | 6/6 pages; og.png 200 live (140 KB) |
| Site | CNAME exact; robots.txt and sitemap.xml return 200 | PASS | PASS | `therackreport.org`; both 200 live; robots.txt names the sitemap |
| Site | External resources https; Leaflet SRI; no unescaped data in HTML | PASS | PASS | 0 http URLs; 4/4 CDN files with sha384 integrity; 0 unescaped fields (pattern-based scan) |
| Site | Page weight (HTML+CSS+JS, CDN excluded); `news.json` size | PASS | PASS | learn 211 KB (largest), atlas 137, newsroom 127, index 125, companies 124, methodology 124, 404 111; `news.json` 1,664 KB |
| Site | Freshness badge shows `news.json` time; 10-minute no-store poller | PASS | PASS | Badge "Updated 2h ago" matches the data; the poller code is present |
| Site | Atlas: pins, state bubbles, pin click, filters, deep link | PASS | PASS | 25 markers, 29 state bubbles at zoom 5+; pin opened "Project Matador"; filter 242 → 6 (AL); `#project=stargate-abilene` opened |
| Site | Accessibility (axe-core), serious or critical | FAIL | PASS | Before: `link-in-text-block` (serious, 3 links on /methodology). Now: 0 |
| Domain | `A therackreport.org` = 4 GitHub Pages IPs | PASS | PASS | 185.199.108.153, .109, .110, .111 (via dns.google) |
| Domain | `CNAME www.therackreport.org` = awigaikwad02.github.io | PASS | PASS | awigaikwad02.github.io. |
| TLS | Valid certificate | PASS | PASS | Let's Encrypt YR1, valid 2026-10-21 to **2027-01-19**, covers apex + www; TLS 1.2/1.3; SSL Labs grade B; no HSTS header |
| TLS | http redirects to https | PASS | PASS | `http://therackreport.org/` ends at `https://therackreport.org/` (200) |
| TLS | www redirects to the apex | PASS | PASS | `https://www.therackreport.org/newsroom` ends at `https://therackreport.org/newsroom` (200); missing paths return 404 with the custom page |
| Security | No secrets in the repo | PASS | PASS | 0 matches in 45 tracked files (token patterns, key/secret/password assignments, private keys) |
| Security | Workflow actions pinned to commit SHAs | FAIL | PASS | Before: `actions/checkout@v4`, `actions/setup-python@v5`. Now pinned (v4.4.0, v5.6.0, setup-node v4.4.0) |
| Security | Workflow permissions | PASS | PASS | Data job: `contents: write` only. Health job also has `issues: write` and `actions: read`, which it needs |
| Security | Fetcher drops non-http(s) links and strips control characters | FAIL | PASS | Before: a `javascript:` link and control characters got through. Now: 0 and 0 |
| Security | `SECURITY.md` exists | FAIL | PASS | Added |

## 2. What was fixed

| Commit | Fix |
|---|---|
| `9c5652a` | Overview counters could show negative numbers (first animation frame earlier than its start time). Clamped; hidden tabs show the final value. |
| `73ed6c7` | Links inside running text are underlined (axe `link-in-text-block`, serious). |
| `b5a533d` | Fetcher drops links that are not `http(s)://` and strips control and invisible characters. |
| `f265fdd` | Added `SECURITY.md`. |
| `09c3462` | Added `scripts/healthcheck.py` and `scripts/healthcheck_browser.mjs`. |
| `4bbf761` | Data workflow: actions pinned to commit SHAs; runs `healthcheck.py --context update` before committing, so a failing check blocks the commit. |
| `54556cc` | Daily **Health check** workflow (07:23 UTC and on demand); commits `data/health.json`; keeps one "Health check failed" issue and closes it on the next pass. |
| `3f4779c` | Methodology page: "Site health" block (last check, overall status, failing checks). First `data/health.json`. |
| `e3c0a96` | README: health-check docs. |
| `9aa9c79` | A Pages deploy cancelled because a newer push replaced it, or a failed run of the health check itself, no longer counts as a pipeline failure. |

Verified in CI:
- The data workflow ran with the new gate, passed and committed (`b4bf70e`).
- The first health run flagged that cancelled Pages deploy and opened issue #1.
- After `9aa9c79`, the next run passed and closed #1 automatically.

## 3. What could not be checked directly, and how it was covered

- **No direct network access to the site.** The sandbox's proxy blocks therackreport.org, github.io, DNS-over-HTTPS resolvers and crt.sh, and `dig` is not installed. I ran the live checks through an outside fetcher (Firecrawl):
  - DNS: Google's DNS JSON API.
  - Certificate: the SSL Labs API.
  - HTTP status and redirect targets: the final URL and status code.
  - Exact redirect codes (301 vs 308) could not be seen.
  - crt.sh returned no entries for the domain, so certificate-log history is unchecked.
- **Browser checks ran on a local copy of `main`.** They used a server that mimics GitHub Pages. Leaflet came from local copies, and map tiles and web fonts were stubbed, because the CDN is blocked here. The same checks then ran in GitHub Actions against the real CDN and passed.
- **GitHub Actions logs could not be downloaded here.** I read CI results from the committed `data/health.json` and the issue history instead.
- **CSP:** the site sets no Content-Security-Policy, so "zero CSP violations" is automatically true. Adding a CSP would be a separate change.
- **Unescaped data in HTML:** the scan is pattern-based. It catches a data field added straight into an HTML string (tested with a planted example), not every possible path.

## 4. Needs attention

1. **Scheduled data runs are unreliable.** On 2026-10-25 GitHub ran the hourly schedule only 5 times: 01:14, 06:15, 11:45, 16:28 and 19:41 UTC. Every run succeeded, but the gaps are longer than 2 hours, so the freshness checks will fail on many days and open the "Health check failed" issue. The fix is an external trigger:
   - a fine-grained token limited to this repository, with Actions read/write permission;
   - an hourly job at a cron service that calls the `workflow_dispatch` API.
2. **Turn on private vulnerability reporting** (repository Settings → Code security). The "Report a vulnerability" button in `SECURITY.md` needs it.
3. **Optional: HSTS.** GitHub Pages sends no HSTS header for custom domains, which is part of SSL Labs' grade B. Adding one would mean proxying through Cloudflare (orange cloud) with HSTS turned on. It's not urgent.
4. **Information only: certificate expiry.** The certificate expires on 2027-01-19, and GitHub renews it automatically. Nothing to do unless the TLS checks start failing.

To watch: 51.8% of headlines have a location, just above the 50% threshold. If it drops below, the daily check fails (the hourly gate only warns). Better place matching would be my job, not Awi's.
