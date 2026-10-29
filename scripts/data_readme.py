#!/usr/bin/env python3
"""
The Rack Report: what every data file and field means, in one place.

What it is for: each JSON file the pipeline writes carries a "_readme" object (about + fields)
so someone opening the file cold can read it. The descriptions live here, and only here:
  - the writers embed them (fetch_news.py, registry.py, healthcheck.py, status_audit.py,
    backfill_news.py, backfill_report.py) through readme(name);
  - docs/DATA_DICTIONARY.md is generated from them:  python scripts/data_readme.py
Hand-edited files (data/projects.json, data/project_overrides.json, data/feeds.json,
scripts/gazetteer.json) keep a "_readme" string written by hand; their fields are listed here
too so the data dictionary covers every file.

When you add a field, describe it here and regenerate the dictionary; tests/test_docs.py fails
when a field in the data is not described.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

HEADLINE = {
    "id": "Permanent id: the first 16 hex digits of the SHA-1 of the normalised title. Never reused.",
    "title": "The headline as published (control characters removed).",
    "link": "Link to the article through Google News; only http(s) links are kept.",
    "source": "The outlet's name as Google News gives it.",
    "published": "Publication time, ISO 8601 UTC.",
    "feed": "Archive only. Which feed or backfill query found the headline.",
    "snippet": "Archive only, when the feed gave one: the outlet line under the headline.",
    "category": "Topic: the first matching rule in fetch_news.CATEGORY_RULES (Cancelled / Blocked first, General when none).",
    "tags": "Archive only. Every topic rule that matched, primary first.",
    "locations": "Archive only. Up to three U.S. places found, most precise first: {name, lat, lon, level, precision, country}.",
    "states": "Every two-letter U.S. state the headline is placed in.",
    "state": "The main state (from the most precise place), or absent.",
    "county": "Archive only. The county or parish named, as 'Name County, State, US'.",
    "location_precision": "Archive only. city, county, state, or source (only the outlet's home state was known).",
    "companies": "Operators: companies that own, develop or run data centers (fetch_news.COMPANIES).",
    "utilities": "Utilities and grid operators named (fetch_news.UTILITIES).",
    "investors": "Investors named (fetch_news.INVESTORS).",
    "builders": "Contractors, engineers and architects named (fetch_news.BUILDERS).",
    "suppliers": "Equipment and chip suppliers named (fetch_news.SUPPLIERS).",
    "capacity_mw": "Capacity stated in the title, in megawatts (gigawatts converted); absent when none or above 20,000 MW.",
    "investment_usd_b": "Investment stated in the title, in billions of U.S. dollars.",
    "name_hint": "Archive only. A project name in the title ('Project Sail', 'Wildcat Ridge Data Center'), used for matching.",
    "cluster_id": "The story this headline belongs to: the id of the story's earliest headline.",
    "cluster_title": "Archive only. The story's display headline (the one with the most precise place).",
    "cluster_lead": "news.json only. true on the story's display headline (replaces cluster_title there).",
    "filtered": "Archive only. true when today's rules reject the headline (off topic, foreign, blocked outlet); kept, never shown.",
}

FILES = {
    "news.json": {
        "path": "data/news.json",
        "writer": "scripts/fetch_news.py, every hourly cycle",
        "about": "The recent headlines the site shows: the last 90 days when that fits in 2.5 MB, else the last 30. "
                 "Older headlines are in data/archive/. Fields that the pages never read are left out to keep it small.",
        "fields": {
            "updated": "When this file was written, ISO 8601 UTC. The site's 'Updated N min ago' badge reads it.",
            "window_days": "How many days of headlines items holds (90 or 30).",
            "count": "Number of items.",
            "new_this_run": "Headlines first seen in the run that wrote the file.",
            "items": "The headlines, newest first. Each item: see 'headline fields'.",
        },
    },
    "archive month": {
        "path": "data/archive/YYYY-MM.json",
        "writer": "scripts/fetch_news.py (appends), scripts/retag_archive.py and scripts/backfill_news.py",
        "about": "Every headline ever kept, one file per month of publication. Headlines are only added, never removed; "
                 "one rejected by today's rules is kept with filtered: true.",
        "fields": {
            "month": "YYYY-MM.",
            "count": "Number of items.",
            "items": "The headlines of that month, newest first. Each item: see 'headline fields'.",
        },
    },
    "archive index": {
        "path": "data/archive/index.json",
        "writer": "scripts/fetch_news.py (write_archive_index)",
        "about": "The months available in the archive, for the Newsroom's 'Include archive' switch.",
        "fields": {
            "updated": "When the index was written.",
            "total": "Headlines in the whole archive.",
            "earliest": "Publication time of the oldest archived headline.",
            "latest": "Publication time of the newest archived headline.",
            "months": "One entry per month file, newest first: {month, count, file, earliest, latest}.",
        },
    },
    "headline fields": {
        "path": "(items in news.json and the archive)",
        "writer": "scripts/fetch_news.py (entry_to_item, tag_item, cluster_items)",
        "about": "One headline. A field with no value is left out.",
        "fields": HEADLINE,
    },
    "registry.json": {
        "path": "data/registry.json",
        "writer": "scripts/registry.py, every hourly cycle (and --backfill)",
        "about": "The permanent project registry: curated projects plus projects detected from headlines. Never trimmed: "
                 "a record is hidden, never deleted. Status, history, events, figures and confidence are rebuilt every run "
                 "by replaying the record's headlines in date order. Corrections go in data/project_overrides.json.",
        "fields": {
            "updated": "When the registry was written.",
            "count": "Number of records, hidden ones included.",
            "visible": "Records that are not hidden.",
            "records": "The records, curated first. Each record: see 'registry record fields'.",
        },
    },
    "registry record fields": {
        "path": "(records in registry.json)",
        "writer": "scripts/registry.py",
        "about": "One project. Detected records are built from headlines; curated ones also copy data/projects.json.",
        "fields": {
            "id": "Permanent id: operator-place-state-year for detected records ('aws-richmond-county-nc-2026'), "
                  "operator-state-unnamed for umbrellas, the projects.json id for curated ones.",
            "name": "Display name.",
            "company": "Operators as display text.",
            "companies": "Operators (fetch_news.COMPANIES names). A detected record with none takes them from a later headline.",
            "location": "'Place, State, US'.",
            "state": "Two-letter state.",
            "county": "'Name County, State, US' when known.",
            "city": "'Town, State, US' when known.",
            "lat": "Latitude of the place (town, county centroid or state centre).",
            "lon": "Longitude.",
            "precision": "city, county, state or source: how exactly the place is known.",
            "curated": "true for a project from data/projects.json.",
            "verified": "Curated only: checked against an official source.",
            "notes": "Curated only: notes shown on the project.",
            "timeline": "Curated only: milestones {date, event, url} from projects.json.",
            "announced": "Curated only: YYYY-MM it was announced.",
            "curated_status": "Curated only: the status in projects.json, which always wins.",
            "curated_capacity_mw": "Curated only: capacity from projects.json.",
            "curated_investment_usd_b": "Curated only: investment from projects.json.",
            "imported": "Curated only: the day the registry first saw it.",
            "news": "Every headline attached to the record: {id, title, link, source, published, stage_signal, cluster_id}. "
                    "stage_signal is re-read from the title with today's rules every run.",
            "first_seen": "Publication time of the earliest attached headline.",
            "last_news": "Publication time of the latest attached headline.",
            "status": "Announced, Under construction, Operational or Cancelled / Blocked (Planned is curated only).",
            "status_history": "Each status change: {date, status, headline_id, by}; by is 'curated' or 'override' when not from a headline.",
            "events": "Timeline events that do not change the status: {date, type, headline_id}; type is Approval, Power deal, "
                      "Expansion, Cancelled or Revived.",
            "capacity_mw": "Largest capacity in the record's headlines (or the curated value).",
            "investment_usd_b": "Largest investment in the record's headlines (or the curated value), billions of dollars.",
            "sources_count": "Distinct outlets among the attached headlines.",
            "confidence": "high (operator, town or county, 2+ outlets), medium (operator or figure, and a town or county) or low.",
            "hidden": "true when the record is not shown (merged, hidden by an override).",
            "merged_into": "When merged: the id of the record that now holds its headlines.",
            "hidden_by_override": "true when a 'hide' override hid it.",
            "umbrella": "true for 'Operator, State (site not yet named)': headlines that name only the state.",
            "umbrella_company": "The umbrella's operator.",
            "aliases": "Extra names that match the record (from 'alias' overrides).",
            "renamed": "true when a 'rename' override set the name.",
            "status_override": "{status, date} from a 'set_status' override.",
            "utilities": "Utilities named in the record's headlines.",
            "investors": "Investors named in the record's headlines.",
            "builders": "Builders named in the record's headlines.",
            "suppliers": "Suppliers named in the record's headlines.",
            "name_hints": "Project names seen in the record's headlines; a headline with the same name in the same state matches.",
        },
    },
    "status.json": {
        "path": "data/status.json",
        "writer": "scripts/fetch_news.py, every hourly cycle",
        "about": "A short report of the last update run, shown on the Methodology page and checked by the health check.",
        "fields": {
            "updated": "When the run finished.",
            "feeds_total": "Feeds the run asked for.",
            "feeds_ok": "Feeds that returned at least one entry.",
            "items_total": "Headlines in news.json after the run.",
            "items_new": "Headlines first seen in this run.",
        },
    },
    "health.json": {
        "path": "data/health.json",
        "writer": "scripts/healthcheck.py and scripts/healthcheck_browser.mjs, every 6 hours",
        "about": "The latest full health check. 'Health check failed' issue opens when overall is fail.",
        "fields": {
            "checked_at": "When the Python checks ran.",
            "browser_checked_at": "When the browser checks ran.",
            "overall": "fail when any check failed, else pass.",
            "context": "full (the scheduled check) or update (the gate inside each hourly cycle, not written to this file).",
            "checks": "Every check: {name, status (pass, warn, fail, skip), value, detail}.",
        },
    },
    "audit_sample.json": {
        "path": "data/audit_sample.json",
        "writer": "scripts/status_audit.py (by hand, after a status rule change)",
        "about": "A fixed sample of registry records with their status under the live rules and under a stricter reading.",
        "fields": {
            "generated": "When it was written.",
            "size": "Records in the sample.",
            "by_status": "Sample records per status under the live rules.",
            "disagreement_count": "Records whose status differs between the two readings.",
            "headline_disagreements": "Headlines whose stage signal differs.",
            "previous_run": "The same counts from the run before.",
            "disagreements": "The records that differ, with the headlines that differ.",
            "records": "Every sampled record: {id, name, status_rules, status_strict, history_rules, history_strict, headlines}.",
        },
    },
    "registry_review.json": {
        "path": "data/registry_review.json",
        "writer": "scripts/backfill_report.py",
        "about": "Records that received headlines naming two operators with nothing in common: likely wrong merges. "
                 "Proposed fixes are in docs/REVIEW_PROPOSALS.md.",
        "fields": {
            "generated": "When it was written.",
            "records": "{id, name, state, companies, example: [{companies, title, id}]}.",
        },
    },
    "registry_rejects.json": {
        "path": "data/registry_rejects.json",
        "writer": "scripts/registry.py, every hourly cycle",
        "about": "Project-shaped headlines from the last 30 days that matched no record and started none: possible "
                 "missed projects. The weekly summary lists them; a headline leaves the file once a record holds it.",
        "fields": {
            "count": "Number of items.",
            "items": "{id, title, link, source, published, state, companies, builders, suppliers, precision, reason}; "
                     "reason says why no record was started (only a state, no operator, only a builder or supplier).",
        },
    },
    "backfill_report.json": {
        "path": "data/backfill_report.json",
        "writer": "scripts/backfill_report.py",
        "about": "What the last news backfill fetched and how it changed the registry (also written as BACKFILL.md).",
        "fields": {
            "generated": "When it was written.", "range": "The backfill's start and end dates.",
            "requests": "Feed requests made.", "failed_requests": "Requests that failed after retries.",
            "fetched": "Entries returned.", "passed_filters": "Entries kept by the topic and U.S. filters.",
            "added_to_archive": "New headlines archived.", "archive": "Archive totals after the backfill.",
            "months": "Per month and query: fetched / kept / new.",
            "registry_before": "Registry counts before.", "registry_after": "Registry counts after.",
            "lost_records": "Record ids that disappeared (must be empty).", "lost_news": "Headlines that left every record (must be empty).",
            "operational_created_by_backfill": "Operational records the backfill created.",
            "operational_completed_last_24_months": "Operational records whose completion headline is under 24 months old.",
            "largest_by_mw": "The 30 largest records by capacity.", "review_count": "Records in registry_review.json.",
            "likely_false_operational": "Operational steps whose headline looks like something else opening.",
            "places_with_several_records": "Places with more than one detected record (possible duplicates).",
            "umbrellas_next_to_named_records": "Umbrellas that sit next to a named record for the same operator and state.",
        },
    },
    "backfill_progress.json": {
        "path": "data/backfill_progress.json",
        "writer": "scripts/backfill_news.py",
        "about": "Where a running or interrupted backfill is, so the next run resumes.",
        "fields": {
            "start": "First day.", "end": "Day after the last.", "window_days": "Window length.",
            "next": "Next window to fetch.", "done": "true when finished.", "windows_done": "Windows fetched.",
            "requests": "Requests made.", "failed_requests": "Requests failed.", "consecutive_failures": "Failures in a row (stops at a limit).",
            "fetched": "Entries returned.", "passed": "Entries kept.", "added": "Headlines archived.",
            "months": "Per month counts.", "windows": "Per window counts.", "baseline": "Registry snapshot before the backfill.",
            "updated": "When the progress was saved.",
        },
    },
    "projects.json": {
        "path": "data/projects.json",
        "writer": "edited by hand",
        "about": "Curated projects, entered from public reporting. Their fields win over anything detected.",
        "fields": {"projects": "The curated projects. Each project: see 'curated project fields'."},
    },
    "curated project fields": {
        "path": "(projects in projects.json)",
        "writer": "edited by hand",
        "about": "One curated project. Required: id, name, lat, lon, state, status.",
        "fields": {
            "id": "Permanent id (lowercase, hyphens).", "name": "Display name.", "company": "Operators as display text.",
            "companies": "Operators, exactly as named in fetch_news.COMPANIES.", "location": "'Place, State' (', US' is added).",
            "state": "Two-letter state.", "lat": "Latitude.", "lon": "Longitude.",
            "status": "Announced, Planned, Under construction, Operational or Cancelled / Blocked.",
            "capacity_mw": "Capacity in MW.", "investment_usd_b": "Investment in billions of dollars.",
            "announced": "YYYY-MM.", "notes": "Shown on the project.", "verified": "true when checked against an official source.",
            "timeline": "Milestones: [{date: YYYY-MM or YYYY-MM-DD, event, url}].", "source_url": "Where the facts come from.",
        },
    },
    "project_overrides.json": {
        "path": "data/project_overrides.json",
        "writer": "edited by hand (see docs/RUNBOOK.md, 'Fix a project record')",
        "about": "Corrections applied to the registry after matching, every run, in order.",
        "fields": {
            "operations": "A list of {op, ...}: merge {from, into}; rename {id, name}; set_status {id, status, date}; "
                          "set_location {id, lat, lon, location, precision}; hide {id}; alias {id, alias}; "
                          "split {id, headline_ids, new_id}.",
        },
    },
    "feeds.json": {
        "path": "data/feeds.json",
        "writer": "edited by hand",
        "about": "What the site fetches and how outlets are treated.",
        "fields": {
            "google_news": "Google News RSS searches: [{name, query}] (query uses Google News search syntax; always the U.S. edition).",
            "google_alerts": "Google Alerts RSS URLs.",
            "blocked_sources": "Outlets whose headlines are always dropped. Lines starting with # are comments.",
            "source_states": "Outlet -> home state, used only when a headline names no U.S. place (location_precision 'source'). "
                             "Suggested by scripts/source_states.py.",
        },
    },
    "gazetteer.json": {
        "path": "scripts/gazetteer.json",
        "writer": "edited by hand; towns added by scripts/gazetteer_towns.py",
        "about": "Place names to coordinates. Matching is case sensitive on whole words.",
        "fields": {
            "<place name>": "[lat, lon, level, display, country] or, for a name found in several states, a list of those. "
                            "level 3 = town or county, 2 = state, 1 = country or region. display is 'Name, State, US' for U.S. places.",
        },
    },
}


def readme(name):
    """The {about, fields, written_by} object to embed as "_readme" in the file called name."""
    f = FILES[name]
    out = {"about": f["about"], "written_by": f["writer"], "fields": dict(f["fields"])}
    if name in ("news.json", "archive month"):
        out["item_fields"] = HEADLINE
    if name == "registry.json":
        out["record_fields"] = FILES["registry record fields"]["fields"]
    out["docs"] = "docs/DATA_DICTIONARY.md"
    return out


def dictionary():
    """docs/DATA_DICTIONARY.md as Markdown."""
    out = ["# Data dictionary", "",
           "Every file the site reads or the pipeline writes, and every field in it. Generated from "
           "`scripts/data_readme.py` (`python scripts/data_readme.py`); edit the descriptions there, not here. "
           "The same text is embedded in each written file as `_readme`.", ""]
    for name, f in FILES.items():
        out += [f"## {name}", "", f"- **Path:** `{f['path']}`", f"- **Written by:** {f['writer']}", "", f["about"], "",
                "| Field | Meaning |", "|---|---|"]
        out += [f"| `{k}` | {v.replace('|', '/')} |" for k, v in f["fields"].items()]
        out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "DATA_DICTIONARY.md").write_text(dictionary(), encoding="utf-8")
    print("wrote docs/DATA_DICTIONARY.md")
    sys.exit(0)
