# Contributing

How to change The Rack Report without breaking it. The owner rarely looks at the site, so every
change must leave it able to explain, test and run itself.

## The rules

1. **No AI or LLM service, ever** (docs/DECISIONS.md, decision 1). No model API, no API key, no
   secret other than `GITHUB_TOKEN`. The health check and the tests fail if you add one.
2. **Never edit `CNAME`.** It must contain exactly `therackreport.org`. Do not change the GitHub
   Pages settings.
3. **Small commits**, one change each, with a message that says what changed and why.
4. **Read a file before changing it**, and keep its style: plain comments, the same naming.
5. **Tests pass before you commit**: `python -m pytest -q tests` and
   `python scripts/healthcheck.py --no-write`. For page changes, also
   `node scripts/healthcheck_browser.mjs` (needs Playwright).
6. **Pull before you push**: `git pull --rebase origin main`; the hourly loop commits data often.
7. **Nothing is deleted.** Archive headlines and registry records are hidden or merged, never
   removed.

## Change a rule (topics, operators, places, statuses)

All tagging rules are in `scripts/fetch_news.py`, each list commented with example headlines.

1. Find a real headline the rule gets wrong (`data/archive/*.json`).
2. Add it to `tests/test_tagging.py` with the right answer (in `HEADLINES`, or the group for that
   kind of rule: `GUARDED`, `STAGES`, `CANCELS`, `ORGS`, `HINTS`, `DROPPED`). Run the tests: it
   should fail.
3. Change the rule. Keep comments with an example for anything you add.
4. Run the tests until all pass. Check the shares: `python scripts/healthcheck.py --no-write`
   (General under 10%, Policy / Permits under 20%, 55%+ located).
5. For a status rule, also run `python scripts/status_audit.py` and look at the disagreements.
6. Re-tag and replay so old data follows the new rule:
   `python scripts/retag_archive.py && python scripts/registry.py --backfill && python scripts/fetch_news.py --no-fetch && git checkout data/status.json`
7. Commit the rule and tests first, then the data in a separate commit.

**Adding an operator:** add it to `COMPANIES` (with a guard if the name is also a common word)
and a one-line description with the same name in `assets/companies.js`. Investors, builders and
suppliers go in `INVESTORS`, `BUILDERS`, `SUPPLIERS`; they never create projects.

**Adding places:** never type coordinates by hand; see docs/RUNBOOK.md, "Improve locations".

## Change a page

- Shared styles: `assets/style.css` (colours are tokens at the top). Shared code: `assets/app.js`.
- Bump the asset version (`?v=rr21` → `rr22`) in every `*.html` and in `scripts/registry.py`
  (project page template), then rebuild pages: `python scripts/registry.py --pages`.
- Links are clean (`/newsroom`, not `newsroom.html`) and every page must be in `sitemap.xml`.
- Test at 390 px and desktop; the browser health check does both.

## Add a data field

Describe it in `scripts/data_readme.py` and run `python scripts/data_readme.py` to regenerate
docs/DATA_DICTIONARY.md. `tests/test_docs.py` fails while a field is undescribed.

## Add a workflow

Pin every action to a commit SHA, give it the fewest permissions it needs, and add it to
`WORKFLOW_PERMISSIONS` in `scripts/healthcheck.py` with a one-line reason. Use only
`secrets.GITHUB_TOKEN`. If it writes data files, use the `data-files` concurrency group and run
the tests before committing.

## Decisions

If your change reverses or adds a design decision, write it in docs/DECISIONS.md.
