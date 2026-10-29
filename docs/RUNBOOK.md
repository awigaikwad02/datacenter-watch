# Runbook

What to do when something needs attention. Each section starts with how you would notice.
Everything here can be done from the GitHub website; nothing needs an API key or an AI service.

Commands below assume a local clone with `pip install -r scripts/requirements.txt`.

---

## The data stopped updating

**You notice:** the site's badge says "Updated N h ago" in amber, or an issue "Health check failed"
says the data has not been refreshed for N hours (opened by the watchdog after 6 h).

1. Actions → **Update data center news**. Is a run *in progress*?
   - **Yes, and it started less than 6 h ago:** it is probably waiting for the next hourly cycle.
     Open it → the "Refresh once an hour" step → look at the last `Cycle N` group:
     - `Google rate limited most feeds; skipping this cycle` → nothing to do; it retries in an hour.
     - `the data health check failed; nothing committed` → see "A health check failed" below; the
       table just above that line names the failing check.
     - `tests failed; nothing committed` → a recent rule change broke a test; see "A test failed".
     - `fetch_news.py exited 1` with `every feed returned zero items` → Google returned nothing;
       usually temporary. If it lasts more than a day, open a feed URL from `data/feeds.json` in a
       browser to see whether Google changed something.
   - **No run in progress:** the chain broke. Click **Run workflow** (leave "chain" unticked). The
     gate job lets it through because nothing else is running, and the loop restarts. The watchdog
     would do the same within 2 hours.
2. If runs start but fail at "Install dependencies" or "Check out repo", it is a GitHub outage;
   check githubstatus.com and wait.
3. If a **Backfill news** run is in progress, the loop waits for it (they share a lock). Either let
   it finish or cancel it (Actions → the run → Cancel); the backfill resumes later where it stopped.

The issue closes itself when the next full health check passes.

## A health check failed

**You notice:** an issue "Health check failed" with a table of checks.

Find the FAIL rows. Common ones:

| Check | Meaning | What to do |
|---|---|---|
| news.json updated within 3h / Last data commit within 3h | Data is stale | "The data stopped updating" above |
| Feeds all returned data | A feed returned nothing in the last run | Usually transient; if it repeats, check that feed's query |
| General under 10% / Policy / Permits under 20% / No category above 30% | Topic rules are drifting with the news | Add the new phrasing to `CATEGORY_RULES` in `scripts/fetch_news.py`, add a test row, see CONTRIBUTING |
| At least 55% of headlines located | Places are missed | Run `python scripts/source_states.py` and the town script (see "Improve locations") |
| Tests pass (pytest) | A test fails | "A test failed" below |
| No AI services, API keys or extra secrets | Someone added an AI call, a key or a secret | Remove it. This is the ground rule (docs/DECISIONS.md, decision 1); there is no exception |
| Workflow permissions minimal | A workflow asks for a permission not in `WORKFLOW_PERMISSIONS` | Remove it, or add the workflow with a reason in `scripts/healthcheck.py` |
| Browser: ... | A page errors, a link breaks, or accessibility regressed | The detail column names the page; reproduce with `node scripts/healthcheck_browser.mjs` |
| Check crashed: ... | A check itself threw an error | The detail is the Python error; usually a data file with an unexpected shape |

Run it yourself: Actions → **Health check** → Run workflow, or locally
`python scripts/healthcheck.py --no-write`.

## A test failed

**You notice:** the loop log says `tests failed`, or the health check row "Tests pass" fails.

Run `python -m pytest -q tests` locally. The failing test names the headline and the field that
differs. Either the rule change was wrong (fix the rule) or the expected value in the test was
wrong (fix the row and say why in the commit message). Never delete a row to make the suite pass.

## Fix a project record

**You notice:** a wrong project on Rack Radar or its page (`/projects/<id>/`), or an item in the
weekly summary's "Needs you" list, or `docs/REVIEW_PROPOSALS.md`.

Edit `data/project_overrides.json` (add to `operations`, then commit). The next hourly cycle
applies it. Operations:

| Operation | Use it to |
|---|---|
| `{"op": "merge", "from": ID, "into": ID}` | Join a duplicate into the right record |
| `{"op": "split", "id": ID, "headline_ids": [...], "new_id": ID}` | Move headlines that belong to another project into a new record |
| `{"op": "rename", "id": ID, "name": "..."}` | Fix the name |
| `{"op": "set_status", "id": ID, "status": "Operational", "date": "YYYY-MM-DD"}` | Force a status from a date |
| `{"op": "set_location", "id": ID, "lat": N, "lon": N, "location": "Town, State, US", "precision": "city"}` | Move the pin (use real coordinates, e.g. from GeoNames) |
| `{"op": "hide", "id": ID}` | Hide something that is not a project |
| `{"op": "alias", "id": ID, "alias": "Project X"}` | Make headlines with that name match |

Headline ids are in `data/registry.json` under the record's `news`. To move headlines into an
existing record: `split` into a temporary id, then `merge` that into the target (examples in
`docs/REVIEW_PROPOSALS.md`). For a curated project, edit `data/projects.json` instead; curated
fields always win.

Check before committing: `python scripts/fetch_news.py --no-fetch && git checkout data/status.json`,
then look at the record. Nothing is ever deleted, so a wrong operation is undone by removing it.

## Add or change a tagging rule

See docs/CONTRIBUTING.md, "Change a rule". In short: add the headline to `tests/test_tagging.py`
with the right answer, change the rule in `scripts/fetch_news.py`, run the tests, then re-tag:
`python scripts/retag_archive.py && python scripts/registry.py --backfill && python scripts/fetch_news.py --no-fetch && git checkout data/status.json`.

## Improve locations

1. `python scripts/source_states.py` lists local outlets that now qualify for a home state;
   `--write` adds them to `data/feeds.json`. Look at the list first: a station named after a
   city in another state sometimes lands wrong (add it to `FIXED` or `NOT_LOCAL`).
2. Towns: in an empty folder, `npm pack cities.json an-array-of-english-words` and untar both,
   then `python scripts/gazetteer_towns.py <cities.json> <index.json>` (dry run) and `--write`.
   Add person and company names that collide with towns to `DENY`.
3. Re-tag (above) and run the tests.

## Run a news backfill

Actions → **Backfill news** → Run workflow with `start`, `end` and `window_days`. It commits every
20 windows and can be re-run with the same inputs to resume. While it runs the hourly loop waits.
It writes `BACKFILL.md` with what to review.

## Weekly summary

Every Monday at 13:00 UTC an issue "Weekly summary <date>" opens (last week's is closed). It lists
headlines added, projects created and status changes, top operators, records to review, the
health status, and a **Needs you** list. If that list is empty, there is nothing to do.

## Recover from a bad commit

Every data commit is small and named "Update news data <time>". To undo one:
`git revert <sha>` and push; the next cycle starts from there. Do not force-push `main`. Never
edit `CNAME` (it must contain exactly `therackreport.org`).
