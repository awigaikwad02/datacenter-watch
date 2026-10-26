#!/usr/bin/env python3
"""
Review outputs for the news backfill:

  data/backfill_report.json   numbers for the backfill (per month and query, registry before/after, lists)
  BACKFILL.md                 the same, readable
  data/registry_review.json   records that took headlines naming two different companies (likely wrong merges)

    python scripts/backfill_report.py
"""

import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_news as fn  # noqa: E402
import registry as rg  # noqa: E402

REPORT_JSON = fn.DATA / "backfill_report.json"
REVIEW_JSON = fn.DATA / "registry_review.json"
REPORT_MD = fn.ROOT / "BACKFILL.md"
SITE = "https://therackreport.org"


def archive_items():
    items = {}
    for p in sorted(fn.ARCHIVE_DIR.glob("*.json")):
        if fn.MONTH_RE.match(p.stem):
            for it in fn.load_json(p, {}).get("items", []):
                items.setdefault(it["id"], it)
    return items


def operational_date(r):
    hist = [h for h in r.get("status_history", []) if h.get("status") == "Operational"]
    return hist[-1] if hist else None


def main():
    prog = fn.load_json(fn.DATA / "backfill_progress.json", {})
    base = prog.get("baseline", {}).get("registry", {})
    base_ids = set(base.get("ids", []))
    recs = rg.load()
    vis = [r for r in recs.values() if not r.get("hidden")]
    arch = archive_items()
    now = datetime.now(timezone.utc)
    by_month = Counter(i["published"][:7] for i in arch.values() if not i.get("filtered"))

    queries = sorted({q for m in prog.get("months", {}).values() for q in m})
    months = [{"month": m, "archive_total": by_month.get(m, 0),
               **{q: prog["months"][m].get(q, {"fetched": 0, "passed": 0, "new": 0}) for q in queries}}
              for m in sorted(prog.get("months", {}))]

    created_ops = []
    for r in vis:
        if r["id"] in base_ids or r.get("curated") or r.get("status") != "Operational":
            continue
        h = operational_date(r)
        n = next((x for x in r["news"] if h and x["id"] == h.get("headline_id")), None)
        created_ops.append({"id": r["id"], "name": r["name"], "place": r["location"].replace(", US", ""), "state": r.get("state"),
                            "completed": (h or {}).get("date", "")[:10], "headline": n["title"] if n else "", "link": n["link"] if n else "",
                            "page": f"{SITE}/projects/{r['id']}/"})
    created_ops.sort(key=lambda x: (x["state"] or "", x["completed"]))

    cutoff = (now - timedelta(days=730)).isoformat()
    completed_24m = [r for r in vis if r.get("status") == "Operational" and operational_date(r)
                     and str(operational_date(r).get("date")) >= cutoff and operational_date(r).get("headline_id")]

    largest = sorted((r for r in vis if r.get("capacity_mw")), key=lambda r: -r["capacity_mw"])[:30]
    largest = [{"id": r["id"], "name": r["name"], "state": r.get("state"), "status": r["status"], "capacity_mw": r["capacity_mw"],
                "curated": r.get("curated", False), "confidence": r.get("confidence")} for r in largest]

    # Records whose headlines name two different companies with nothing in common.
    review = []
    for r in vis:
        sets = []
        for n in r["news"]:
            cos = frozenset(arch.get(n["id"], {}).get("companies", []))
            if cos:
                sets.append((cos, n))
        clash = next(((a, b) for i, a in enumerate(sets) for b in sets[i + 1:] if not (a[0] & b[0])), None)
        if clash:
            review.append({"id": r["id"], "name": r["name"], "state": r.get("state"), "companies": sorted(set().union(*(s for s, _ in sets))),
                           "example": [{"companies": sorted(c), "title": n["title"], "id": n["id"]} for c, n in clash],
                           "suggestion": "split the headlines of the other company into a new record, or merge into the right one"})
    review.sort(key=lambda x: x["id"])

    count = lambda key: dict(sorted(Counter(r.get(key) for r in vis).items()))
    after = {"count": len(recs), "visible": len(vis), "status": count("status"), "confidence": count("confidence"),
             "umbrellas": sum(1 for r in vis if r.get("umbrella"))}
    lost_ids = sorted(base_ids - set(recs))
    lost_news = sorted(set(base.get("news_ids", [])) - {n["id"] for r in recs.values() for n in r["news"]})
    report = {
        "generated": now.isoformat(timespec="seconds"),
        "range": {"start": prog.get("start"), "end": prog.get("end"), "window_days": prog.get("window_days"), "done": prog.get("done")},
        "requests": prog.get("requests"), "failed_requests": prog.get("failed_requests"),
        "fetched": prog.get("fetched"), "passed_filters": prog.get("passed"), "added_to_archive": prog.get("added"),
        "archive": {"before": prog.get("baseline", {}).get("archive_ids"), "after": len(arch),
                    "earliest": min((i["published"] for i in arch.values()), default=None)},
        "months": months,
        "registry_before": {k: base.get(k) for k in ("count", "visible", "status", "confidence")},
        "registry_after": after,
        "lost_records": lost_ids, "lost_news": lost_news,
        "operational_created_by_backfill": created_ops,
        "operational_completed_last_24_months": len(completed_24m),
        "largest_by_mw": largest,
        "review_count": len(review),
    }
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    REVIEW_JSON.write_text(json.dumps({"generated": report["generated"], "_readme": "Records that received headlines naming two different "
                                       "companies with nothing in common: likely wrong merges. Fix with split or merge in "
                                       "data/project_overrides.json.", "records": review}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    write_md(report, queries, review)
    print(f"Wrote {REPORT_JSON.name}, {REVIEW_JSON.name} ({len(review)} to review) and BACKFILL.md")
    return 0


def esc(s):
    return str(s if s is not None else "").replace("|", "\\|").replace("\n", " ")


def write_md(rep, queries, review):
    b, a = rep["registry_before"], rep["registry_after"]
    statuses = sorted(set((b.get("status") or {}).keys()) | set(a["status"].keys()))
    conf = sorted(set((b.get("confidence") or {}).keys()) | set(a["confidence"].keys()))
    L = [f"# News backfill report", "",
         f"Generated {rep['generated']}. Range {rep['range']['start']} to {rep['range']['end']} in {rep['range']['window_days']}-day windows "
         f"({'complete' if rep['range']['done'] else 'in progress'}).", "",
         f"- Requests: {rep['requests']} ({rep['failed_requests']} failed)",
         f"- Headlines fetched: {rep['fetched']}; passed the filters: {rep['passed_filters']}; new to the archive: {rep['added_to_archive']}",
         f"- Archive: {rep['archive']['before']} headlines before, {rep['archive']['after']} after; earliest {str(rep['archive']['earliest'])[:10]}",
         f"- Operational records with a completion date (from a headline) in the last 24 months: {rep['operational_completed_last_24_months']}",
         f"- Records lost: {len(rep['lost_records'])}; attached headlines lost: {len(rep['lost_news'])}",
         f"- Records to review (headlines from two different companies): {rep['review_count']} (see `data/registry_review.json`)", "",
         "## Headlines per month and query", "",
         "Fetched / passed the filters / new to the archive, by the month the window starts in.", "",
         "| Month | " + " | ".join(queries) + " | Archive total |", "|---" * (len(queries) + 2) + "|"]
    for m in rep["months"]:
        L.append(f"| {m['month']} | " + " | ".join(f"{m[q]['fetched']} / {m[q]['passed']} / {m[q]['new']}" for q in queries) + f" | {m['archive_total']} |")
    L += ["", "## Registry before and after", "", "| | Before | After |", "|---|---|---|",
          f"| Records (visible) | {b.get('count')} ({b.get('visible')}) | {a['count']} ({a['visible']}) |"]
    L += [f"| {s} | {(b.get('status') or {}).get(s, 0)} | {a['status'].get(s, 0)} |" for s in statuses]
    L += [f"| Confidence {c} | {(b.get('confidence') or {}).get(c, 0)} | {a['confidence'].get(c, 0)} |" for c in conf]
    L += [f"| Umbrellas | | {a['umbrellas']} |", "",
          f"## Operational projects created by the backfill ({len(rep['operational_created_by_backfill'])})", "",
          "| State | Project | Place | Completed | Headline |", "|---|---|---|---|---|"]
    for o in rep["operational_created_by_backfill"]:
        L.append(f"| {esc(o['state'])} | [{esc(o['name'])}]({o['page']}) | {esc(o['place'])} | {o['completed']} | [{esc(o['headline'])}]({o['link']}) |")
    L += ["", "## 30 largest projects by MW", "", "| # | Project | State | Status | MW | Source |", "|---|---|---|---|---|---|"]
    for i, r in enumerate(rep["largest_by_mw"], 1):
        L.append(f"| {i} | [{esc(r['name'])}]({SITE}/projects/{r['id']}/) | {r['state']} | {r['status']} | {r['capacity_mw']:,} | "
                 f"{'curated' if r['curated'] else 'detected, ' + str(r['confidence'])} |")
    L += ["", f"## Records to review ({len(review)})", "",
          "Each received headlines naming different companies with nothing in common, which usually means two projects were merged.", "",
          "| Record | Companies | Example headlines |", "|---|---|---|"]
    for r in review:
        L.append(f"| `{r['id']}` | {esc(', '.join(r['companies']))} | " + " / ".join(f"{esc(', '.join(e['companies']))}: {esc(e['title'])}" for e in r["example"]) + " |")
    REPORT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
