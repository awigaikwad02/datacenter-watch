# Security policy

The Rack Report (https://therackreport.org) is a static site on GitHub Pages. There are no
accounts, forms, cookies or server-side code; the only moving part is a GitHub Actions job that
reads public RSS feeds and commits JSON files to this repository.

## Reporting a problem

Please report security issues privately rather than in a public issue:

- Use GitHub's **Report a vulnerability** button under the repository's Security tab, or
- Message the maintainer on LinkedIn: https://www.linkedin.com/in/avishkar-gaikwad-/

Include the page or file, what you found and how to reproduce it. You should get a reply within a
week. Please give a reasonable chance to fix the problem before disclosing it.

## What is in scope

- Script injection through headline text, links or other data shown on the site
- The data pipeline (`scripts/fetch_news.py`, `.github/workflows/`) committing unsafe content
- Third-party code loaded by the pages (Leaflet and Leaflet.markercluster from unpkg with
  subresource integrity; Google Fonts; OpenStreetMap tiles)
- Secrets accidentally committed to the repository

Wrong tags, misplaced pins or off-topic headlines are data-quality issues; please open a normal
issue for those (see the Methodology page).

## Safeguards in place

- Headlines are stored as plain text: tags, control and invisible characters are stripped, and
  links that are not `http://` or `https://` are dropped before anything is written.
- Every data value is HTML-escaped before it is rendered.
- CDN scripts and stylesheets carry `integrity` hashes; GitHub Actions are pinned to commit SHAs
  and the workflows have the minimum permissions they need.
- `scripts/healthcheck.py` runs after every data update (a failing check blocks the commit) and
  daily with `scripts/healthcheck_browser.mjs`; failures open a "Health check failed" issue.
