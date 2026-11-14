#!/usr/bin/env python3
"""
The Rack Report: the weekly summary, posted every Monday as a GitHub issue.

What it is for: the owner rarely looks at the site. Once a week this writes one short Markdown
report: what came in, what changed, what is broken, and a "Needs you" list of the decisions only
a person can make. An empty "Needs you" list means there is nothing to do.

It compares the data now with the data as committed at --since (a git ref from a week ago, which
the workflow finds with `git rev-list -1 --before="7 days ago"`). Pure Python on the repository's
own files; no API and no AI service (docs/DECISIONS.md, decision 1).

Reads: data/archive/, data/registry.json, data/registry_review.json, data/registry_rejects.json,
data/health.json, data/news.json, data/projects.json, docs/REVIEW_PROPOSALS.md.
Writes: the Markdown to --out (or stdout).

    python scripts/weekly_summary.py --since HEAD~150 --out /tmp/summary.md
Run by: .github/workflows/weekly.yml (Mondays 13:00 UTC).
"""

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
NOW = datetime.now(timezone.utc)
SITE = "https://therackreport.org"
STAGE = {"Announced": 1, "Under construction": 2, "Operational": 3}


def load(path, default=None):
    """A JSON file from the working tree, or default when it is missing or broken."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def at(ref, path, default=None):
    """A JSON file as it was committed at a git ref, or default."""
    if not ref:
        return default
    r = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=ROOT, capture_output=True, text=True)
    try:
        return json.loads(r.stdout) if r.returncode == 0 else default
    except ValueError:
        return default


def when(s):
    """An ISO time as an aware datetime (None when it does not parse)."""
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def week_headlines():
    """Archived headlines published in the last 7 days that the site shows."""
    cutoff = NOW - timedelta(days=7)
    out = []
    for p in sorted((DATA / "archive").glob("2*.json"))[-2:]:
        for it in (load(p, {}) or {}).get("items", []):
            d = when(it.get("published"))
            if d and d >= cutoff and not it.get("filtered"):
                out.append(it)
    return out


def link(r):
    """Markdown link to a record's project page."""
    return f"[{r['name']}]({SITE}/projects/{r['id']}/)"


def curated_conflicts(records):
    """Curated projects whose latest headline reports a later stage than their curated status."""
    out = []
    for r in records.values():
        if not r.get("curated") or r.get("hidden"):
            continue
        signals = [n for n in r["news"] if n.get("stage_signal") in STAGE]
        if not signals:
            continue
        top = max(signals, key=lambda n: (STAGE[n["stage_signal"]], n["published"]))
        if STAGE[top["stage_signal"]] > STAGE.get(r.get("curated_status"), 0) and r.get("curated_status") in STAGE:
            out.append((r, top))
    return out


def summary(since):
    """The report as Markdown."""
    reg_now = {r["id"]: r for r in (load(DATA / "registry.json", {}) or {}).get("records", [])}
    reg_then = {r["id"]: r for r in (at(since, "data/registry.json", {}) or {}).get("records", [])}
    idx_now = load(DATA / "archive/index.json", {}) or {}
    idx_then = at(since, "data/archive/index.json", {}) or {}
    health = load(DATA / "health.json", {}) or {}
    review = (load(DATA / "registry_review.json", {}) or {}).get("records", [])
    rejects = (load(DATA / "registry_rejects.json", {}) or {}).get("items", [])
    news = load(DATA / "news.json", {}) or {}
    week = week_headlines()
    stories = {it.get("cluster_id") or it["id"]: it for it in week}

    L = [f"Summary for the week to {NOW:%A %B %-d, %Y} ({NOW:%H:%M} UTC). Written by `scripts/weekly_summary.py`; "
         "no reply needed unless **Needs you** lists something.", ""]

    # Needs you first: the only part that asks for anything.
    needs = []
    failing = [c for c in health.get("checks", []) if c.get("status") == "fail"]
    if failing:
        needs.append(f"**The health check is failing** ({len(failing)} checks): " +
                     "; ".join(f"{c['name']} ({c.get('value', '')})" for c in failing[:5]) +
                     ". See docs/RUNBOOK.md, \"A health check failed\".")
    upd = when(news.get("updated"))
    if upd and NOW - upd > timedelta(hours=6):
        needs.append(f"**Data is {int((NOW - upd).total_seconds() // 3600)} hours old.** See docs/RUNBOOK.md, \"The data stopped updating\".")
    if review:
        needs.append(f"**{len(review)} project records may mix two projects** (data/registry_review.json). Proposed fixes, ready to "
                     "paste, are in docs/REVIEW_PROPOSALS.md: " + ", ".join(f"`{r['id']}`" for r in review[:8]) + ".")
    conflicts = curated_conflicts(reg_now)
    if conflicts:
        needs.append(f"**{len(conflicts)} curated projects have headlines saying they moved on** (change `status` in data/projects.json "
                     "if you agree): " + "; ".join(f"{link(r)} is {r['curated_status']}, headline says {n['stage_signal']}: "
                                                     f"[{n['title'][:90]}]({n['link']})" for r, n in conflicts[:6]))
    L += ["## Needs you", ""] + ([f"{i}. {n}" for i, n in enumerate(needs, 1)] or ["Nothing. Everything below is for information."]) + [""]

    L += ["## This week", ""]
    added = (idx_now.get("total") or 0) - (idx_then.get("total") or 0) if idx_then else None
    L.append(f"- **Headlines:** {len(week):,} published in the last 7 days, in {len(stories):,} stories" +
             (f"; the archive grew by {added:,} to {idx_now.get('total', 0):,}." if added is not None else "."))
    cats = Counter(it.get("category") for it in week)
    if cats:
        L.append("- **Topics:** " + ", ".join(f"{c} {n}" for c, n in cats.most_common(6)) + ".")
    located = sum(1 for it in week if it.get("state"))
    if week:
        L.append(f"- **Located:** {100 * located / len(week):.0f}% of the week's headlines name a U.S. place.")
    cos = Counter(c for it in stories.values() for c in it.get("companies", []))
    if cos:
        L.append("- **Most-covered operators** (stories): " + ", ".join(f"{c} {n}" for c, n in cos.most_common(8)) + ".")
    orgs = Counter(o for it in stories.values() for k in ("investors", "builders", "suppliers") for o in it.get(k, []))
    if orgs:
        L.append("- **Investors, builders and suppliers in the news:** " + ", ".join(f"{c} {n}" for c, n in orgs.most_common(6)) + ".")
    L.append("")

    new = [r for i, r in reg_now.items() if i not in reg_then and not r.get("hidden")] if reg_then else []
    moved = [(reg_then[i]["status"], r) for i, r in reg_now.items()
             if i in reg_then and reg_then[i].get("status") != r.get("status") and not r.get("hidden")] if reg_then else []
    L += ["## Projects", ""]
    if not reg_then:
        L.append("No registry from a week ago to compare with.")
    else:
        L.append(f"- **{len(new)} new records** ({sum(1 for r in new if r.get('confidence') != 'low')} medium or high confidence); "
                 f"{len(reg_now)} in the registry, {sum(1 for r in reg_now.values() if not r.get('hidden'))} visible.")
        for r in sorted(new, key=lambda r: (r.get("confidence") != "high", r["name"]))[:10]:
            L.append(f"  - {link(r)}: {r['status']}, {r['location'].replace(', US', '')}, {r.get('confidence')} confidence")
        by = Counter(f"{a} → {r['status']}" for a, r in moved)
        L.append(f"- **{len(moved)} status changes**" + (": " + ", ".join(f"{k} {v}" for k, v in by.most_common()) if moved else "."))
        for a, r in moved[:10]:
            L.append(f"  - {link(r)}: {a} → {r['status']}")
    L.append("")

    week_rejects = [x for x in rejects if (when(x.get("published")) or NOW) >= NOW - timedelta(days=7)]
    L += ["## Headlines that started no project", "",
          f"{len(week_rejects)} project-shaped headlines this week matched no record and started none "
          f"({len(rejects)} in the last 30 days, data/registry_rejects.json). Usually a council vote with no company named; "
          "a real project among them is picked up when a later headline names its operator."]
    town = [x for x in week_rejects if x.get("precision") in ("city", "county")]
    for x in town[:8]:
        L.append(f"- [{x['title'][:100]}]({x['link']}) ({x.get('source', '')}): {x['reason']}")
    L.append("")

    L += ["## Health", ""]
    if health:
        L.append(f"Last full check {health.get('checked_at', '?')}: **{str(health.get('overall', '?')).upper()}**, "
                 f"{sum(c['status'] == 'pass' for c in health.get('checks', []))} passed, {len(failing)} failed, "
                 f"{sum(c['status'] == 'warn' for c in health.get('checks', []))} warnings.")
        for c in failing[:10]:
            L.append(f"- FAIL {c['name']}: {c.get('value', '')} {c.get('detail', '')}".rstrip())
    else:
        L.append("data/health.json is missing.")
    if upd:
        L.append(f"Data last updated {upd:%Y-%m-%d %H:%M} UTC.")
    return "\n".join(L) + "\n"


def main():
    """Write the summary to --out or print it."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", help="git ref of the data a week ago")
    ap.add_argument("--out", help="write the Markdown here")
    args = ap.parse_args()
    text = summary(args.since)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
