# Proposed fixes for the records in `data/registry_review.json`

`data/registry_review.json` lists records that received headlines naming two different operators
with nothing in common, which usually means two projects were merged by mistake. These five were
reviewed on 2026-10-29. **None of this is applied**: each fix is a judgement call, so it waits for
you. To apply one, copy its operations into the `operations` list in
`data/project_overrides.json`, commit, and the next hourly run rebuilds the records (see
`docs/RUNBOOK.md`, "Fix a project record").

All 13 operations below were dry-run against a copy of the registry on 2026-10-29 and do what
each section says. How the operations combine: `split` moves headlines out of a record into a new one; a `split`
followed by a `merge` moves them into a record that already exists. Nothing is ever deleted: a
merged record stays in `data/registry.json` as hidden with `merged_into`.

---

## 1. `meta-tx-unnamed`: "Meta, Texas (site not yet named)", shows Operational

It holds three unrelated stories:

| Headlines | Really about |
|---|---|
| `2101a1ed74b851a3` Oracle, OpenAI Scrap Texas AI Data Center Expansion Plans; Meta Eyes Site: Report<br>`35a859dbe9962d22` Oracle and OpenAI drop Texas data center expansion plan, Bloomberg News reports<br>`d2afa66333ebbd94` Oracle drops after report that it and OpenAI scrapped plans to expand a data center site in Texas<br>`dd42488221b60f86` OpenAI and Oracle Curtail Data Center Expansion in Abilene, Texas<br>`04caf631b022a1f4` Did Oracle and OpenAI scrap Texas data center expansion plans? | Stargate Abilene (curated `stargate-abilene`) |
| `c6dc2600cd8f51bb` Prometheus Hyperscale details plans for Dallas data center campus | A Prometheus Hyperscale project in Dallas (no record yet) |
| `936115f05d17edc5` Meta announces new STEM grants alongside Temple Data Center launch<br>`e1f42729a738acae` Meta's Temple data center goes live amid community concerns over water use and expansion<br>`8af1769ddbbfe3ad` $1.2B Meta Data Center Opens in Temple | Meta's data center in Temple, Bell County (no record yet) |

The other four headlines (Meta's 2025 Texas plans, Governor Abbott's standards, a solar deal) are
statewide and can stay in the umbrella.

```json
{"op": "split", "id": "meta-tx-unnamed", "new_id": "tmp-abilene-from-meta-tx",
 "headline_ids": ["2101a1ed74b851a3", "35a859dbe9962d22", "d2afa66333ebbd94", "dd42488221b60f86", "04caf631b022a1f4"]},
{"op": "merge", "from": "tmp-abilene-from-meta-tx", "into": "stargate-abilene"},
{"op": "split", "id": "meta-tx-unnamed", "new_id": "prometheus-hyperscale-dallas-tx-2026", "headline_ids": ["c6dc2600cd8f51bb"]},
{"op": "rename", "id": "prometheus-hyperscale-dallas-tx-2026", "name": "Prometheus Hyperscale Dallas data center"},
{"op": "split", "id": "meta-tx-unnamed", "new_id": "meta-temple-tx-2026",
 "headline_ids": ["936115f05d17edc5", "e1f42729a738acae", "8af1769ddbbfe3ad"]},
{"op": "rename", "id": "meta-temple-tx-2026", "name": "Meta Temple data center"},
{"op": "set_location", "id": "meta-temple-tx-2026", "lat": 31.0982, "lon": -97.3428, "location": "Temple, Texas, US", "precision": "city"}
```

Effect: the umbrella drops back to Announced; Meta Temple appears as an Operational project in
Temple (GeoNames coordinates); the Abilene record gains the March 2026 scale-back headlines.

## 2. `openai-tx-unnamed`: "OpenAI, Texas (site not yet named)", Under construction

| Headlines | Really about |
|---|---|
| `bc9ddbce51bc816f` Watch Crusoe Enters Second Phase of Building an OpenAI Texas Data Center<br>`501bd68788e8134a` OpenAI CEO Sam Altman shares video of AI data center in Texas, plans 5 more | Stargate Abilene |
| `69f52cf0e3548f8b` Vantage breaks ground on Texas gigawatt data center campus for OpenAI<br>`19ddb5ee955e2ee1` Vantage Data Centers breaks ground on data center campus in Texas<br>`4401f9df103d2954` Vantage Breaks Ground on 1.4GW Texas Data Center for OpenAI | Vantage Frontier, Shackelford County (curated `frontier`) |

```json
{"op": "split", "id": "openai-tx-unnamed", "new_id": "tmp-abilene-from-openai-tx", "headline_ids": ["bc9ddbce51bc816f", "501bd68788e8134a"]},
{"op": "merge", "from": "tmp-abilene-from-openai-tx", "into": "stargate-abilene"},
{"op": "split", "id": "openai-tx-unnamed", "new_id": "tmp-frontier-from-openai-tx", "headline_ids": ["69f52cf0e3548f8b", "19ddb5ee955e2ee1", "4401f9df103d2954"]},
{"op": "merge", "from": "tmp-frontier-from-openai-tx", "into": "frontier"},
{"op": "hide", "id": "openai-tx-unnamed"}
```

The last `hide` is optional: the umbrella is empty afterwards.

## 3. `site-port-washington-wi-2025-8`: "Port Washington data center", Under construction

A duplicate of the curated Lighthouse campus: all six headlines are the December 2025
groundbreaking of the $15 billion Vantage / Stargate campus in Port Washington
(`58658f75224e8556`, `9c32502d6c6bda5d`, `3fdcb5d851e018aa`, `da14740d22e68444`,
`f63d095f1dfcce5a`, `7cdb9bb86ecdb741`).

```json
{"op": "merge", "from": "site-port-washington-wi-2025-8", "into": "stargate-port-washington-lighthouse"}
```

## 4. `stargate-port-washington-lighthouse`: curated, shows Announced

Vantage, OpenAI and Oracle are all correct here. Two things to decide:

- Its status comes from `data/projects.json` ("Announced"), but the groundbreaking above was in
  December 2025. Proposed: set `"status": "Under construction"` for this project in
  `data/projects.json` (curated status always wins over headlines).
- `TMJ4: Will Vantage live up to jobs expectations when AI facility opens in Port Washington?`
  used to read as Operational. Fixed in the rules on 2026-10-29 ("when ... opens" is future);
  no action needed.

## 5. `stargate-abilene`: curated, Under construction

Crusoe, OpenAI and Oracle are correct. The record also holds March 2026 headlines about a new
900 MW Crusoe "AI factory" in Abilene for Microsoft:

- `Microsoft to lease Abilene data center as OpenAI, Oracle scale back plans`
- `Crusoe Expands Abilene AI Campus With New 900 MW 'AI Factory' for Microsoft`
- `Crusoe Announces New 900 MW AI Factory Campus in Abilene, Texas to Support Microsoft AI Infrastructure`

Decide whether that is the same campus (then add `"Microsoft"` to this project's `companies` in
`data/projects.json`) or a separate project (then split those headlines into a new record with a
`split` operation, as in item 1). Also, the curated status may now be "Operational": parts of the
campus have been live since September 2025 ("Crusoe Announces Flagship Abilene Data Center is
Live").

---

## Also found: curated statuses that headlines say are out of date

Curated projects take their status from `data/projects.json`, never from headlines. These now
have headlines saying they are running; if you agree, change `"status"` to `"Operational"` there.

| Project | Status in projects.json | Headline |
|---|---|---|
| `fairwater` (Microsoft, Mount Pleasant, WI) | Under construction | Microsoft's first data center at Mount Pleasant, Wisconsin, campus now operational |
| `google-fort-wayne` (Google, Fort Wayne, IN) | Under construction | Google's $2bn data center now operational in Fort Wayne, Indiana |
| `stargate-abilene` (see item 5) | Under construction | Crusoe Announces Flagship Abilene Data Center is Live |
