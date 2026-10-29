# Decisions

Why The Rack Report works the way it does. Read the relevant entry before changing something it
covers; if you change the decision, edit the entry (date it) rather than deleting it.

## 1. No AI or LLM service anywhere in the pipeline (2026-10-29)

**Rule.** The site never depends on Claude, Claude Code, or any AI or LLM service to run. No calls
to the Anthropic, OpenAI or any other model API, no API keys, and no secrets beyond GitHub's own
`GITHUB_TOKEN`. Refreshes, tagging, company and place detection, status changes, matching,
clustering, health checks and the weekly summary are all deterministic code that GitHub Actions
runs on its own. Claude Code may edit the rules and data files, but if Claude disappeared tomorrow
the site must keep updating and tagging exactly as it does today.

**Why.** The owner does not watch the site day to day. A model call can change its answers,
fail, rate-limit, cost money, or need a key that expires; any of those would silently degrade or
stop the site. Rules in code are slower to write, but they give the same answer every time,
can be tested (`tests/`), and can be read and fixed by anyone.

**Enforced by** `scripts/no_ai.py`, run by `scripts/healthcheck.py` (check "No AI services, API
keys or extra secrets") and by `tests/test_no_ai.py`, which every workflow runs before it
commits. It fails on an AI SDK import (`anthropic`, `openai`, `google.generativeai`, LangChain and
others, in Python or JavaScript), a model API host, any `*_API_KEY` name or `x-api-key` header, an
AI package in `requirements.txt` or `package.json`, and any workflow `secrets.X` other than
`secrets.GITHUB_TOKEN`. Company names are fine: OpenAI and Anthropic are tracked operators.

**Do not** add an AI step "to improve tagging". When tagging is wrong, add the headline to
`tests/test_tagging.py` with the right answer and fix the rule.

## 2. A self-sustaining update loop instead of a frequent cron (2026-10-29)

Between Oct 26 and 29, 2026 GitHub started the `*/5` schedule only 13 times in about 75 hours, at
gaps of 3.5 to 6.5 hours (it should have been about 900); every run that did start succeeded.
Scheduled workflows on GitHub are best-effort, so the refresh does not rely on them:
`update.yml` runs `scripts/update_loop.sh` for 5 h 40 min, refreshing once an hour, then starts
its own next run with `gh workflow run` (a `workflow_dispatch` made with `GITHUB_TOKEN` does
start a workflow). An hourly cron at :17 and `watchdog.yml` every 2 hours only restart the chain
if it ever breaks; a start while a loop is running is skipped by the `gate` job, not queued.

## 3. Back off when Google rate-limits (2026-10-29)

If more than half the feeds end in HTTP 429 after retries, `fetch_news.py` writes nothing and
exits 75; the loop skips that cycle and tries again an hour later. Hammering a rate limit makes it
worse, and an hour's gap is invisible to readers.

## 4. news.json holds 30 or 90 days, sized by bytes (2026-10-29)

`data/news.json` holds 90 days when that fits in 2.5 MB, otherwise 30 days, with no item cap; the
fields the pages never read are left out. The Newsroom loads older months from
`data/archive/` only when someone asks for a longer range. A fixed item cap silently dropped
stories on busy weeks; a byte budget keeps the page fast instead.

## 5. Headlines and records are never deleted

The archive is append-only (a headline rejected by today's rules is kept with `filtered: true`),
and registry records are hidden, never deleted (merges leave `merged_into`). Rules change; data
that was thrown away cannot be re-tagged, and links to project pages must keep working.

## 6. Curated projects win over headlines

`data/projects.json` is the human-checked source; its status, place and figures always win over
what headlines suggest. Headlines still attach news and events to curated records. When
headlines contradict a curated status, it is listed for review (docs/REVIEW_PROPOSALS.md), not
changed automatically.

## 7. Only operators create projects (2026-10-29)

Organisations fall in five fields: operators (`companies`), investors, builders, suppliers and
utilities. Only an operator, a project code name or a stated figure can create a project; a
headline naming only a contractor or supplier ("Mortenson breaks ground in Hermantown") can join
the one project already tracked at that place but never creates one. Otherwise every Vertiv or
Caterpillar headline would become a fake project. Names that are also common words (Stream,
Prime, Page, Element, Edged, Ascent, Galaxy, Switch, Carrier...) only match with a qualifying word
next to them.

## 8. Topic order (2026-10-29)

The first matching rule wins, in this order: Cancelled / Blocked, a labelled opinion piece, New
Announcement, Construction, Expansion, Land Acquisition, Operations, Markets / Earnings, Deals /
Investment, Economy / Jobs, Environment, Power / Utility, Community, AI Infrastructure, Politics,
Policy / Permits, Analysis / Opinion, General. Targets: General under 10% and Policy / Permits
under 20% (the health check enforces both). AI Infrastructure comes after Community because "AI"
is in so many headlines that a fight over an "AI data center" is a community story; putting it
after Policy too would push Policy / Permits to 20.5% of recent headlines, so it stays before.

## 9. A stage word must describe the present stage (2026-10-29)

"Could break ground this summer", "on track to be completed", "opens in 2026", "when the facility
opens" are future; "solar farm opens" and "completes purchase" are not the data center opening.
These do not move a status. A step right after "after"/"following" already happened. The rules
were checked against a stricter reading on 150 records (`scripts/status_audit.py`,
`data/audit_sample.json`): 13 disagreements before the fix, 1 after (where the strict reading is
wrong). Every run re-reads every attached headline with today's rules, so a fix corrects old
records too.

## 10. Places: towns from GeoNames, ambiguous names need a state (2026-10-29)

Coordinates are never typed in by hand. Counties are Census centroids; towns come from GeoNames
(CC BY 4.0) via `scripts/gazetteer_towns.py`, which adds only names seen 3+ times in unlocated
headlines and skips English words, people, companies and county-like names. A town name that
exists in several states (Lansing, Jackson) is used only when the headline or the outlet names
the state. Local outlets map to a home state (`source_states`) only as a last resort, marked
`location_precision: "source"`. Located share went from 45% to 62% of archived headlines; the
health check requires 55% of recent ones.

## 11. A town-level headline does not join an umbrella (2026-10-29)

An umbrella ("Amazon, Texas (site not yet named)") collects headlines that name only a state. A
headline that names a town creates the named site, which then absorbs the umbrella. Before this,
such headlines joined the umbrella and the town was lost.

## 12. Tell the owner only when a decision is needed

Two emails at most: the "Health check failed" issue (opens on failure, closes itself when the
check passes again) and the Monday "Weekly summary" issue (closes the previous one). Everything
else (rule fixes, data refreshes, re-derived statuses) happens without notification.
