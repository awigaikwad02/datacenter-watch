#!/usr/bin/env python3
"""
The Rack Report: audit the project status rules against a stricter reading of the headlines.

What it is for: a record's status comes from the stage word in each of its headlines ("breaks
ground" = Under construction, "opens" = Operational; fetch_news.guess_status). This script takes
a fixed sample of registry records, re-reads every headline with a stricter check, replays both
readings through registry.derive, and lists the records whose status would differ. The stricter
check only counts a stage word in the headline's main clause, so it ignores one that is
  - after a subordinating word: despite, after, before, ahead of, following, until, once, if, amid
  - after an intent or future marker: plans to, aims to, set to, expected to, on track to, will, could, to
  - about something other than the data center: a plant, factory, solar farm, office or hub that opens
  - about a step that is not the building: completes an application, a purchase, a deal or a review
Disagreements are leads for fixing the rules in fetch_news.py, not automatic corrections.

Writes data/audit_sample.json (the sample, both readings and the disagreements). The previous
run's counts are kept under "previous_run" so a rule change can be compared before and after.

    python scripts/status_audit.py              # default 150 records
    python scripts/status_audit.py --size 300
"""

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_news as fn  # noqa: E402
import registry as reg  # noqa: E402

OUT = fn.DATA / "audit_sample.json"
# Share of the sample per current status; Operational and Cancelled are over-sampled because a
# wrong step there misleads readers most.
MIX = {"Operational": 0.3, "Under construction": 0.25, reg.CANCELLED: 0.2, "Announced": 0.25}

BREAK = re.compile(r"\b(despite|after|before|ahead of|following|until|once|if|unless|amid|while|"
                   r"plans? to|planning to|aims? to|hopes? to|seeks? to|wants? to|set to|slated to|"
                   r"expected to|scheduled to|poised to|on track to|in line to|will|would|could|may|might|"
                   r"to|near|nears|nearing|push(es)? .{0,20} to|urges? .{0,20} to)\b", re.I)
NOT_DC = re.compile(r"\b(plant|factory|manufacturing|hub|solar|farm|wind|substation|office|headquarters|"
                    r"warehouse|store|school|training|recycling|water|pipeline|line|mine|park)\b", re.I)
NOT_BUILDING = re.compile(r"^\W*(?:\w+\W+){0,3}?(application|purchase|acquisition|sale|deal|financing|"
                          r"transaction|merger|review|study|annexation|agreement|rezoning|filing|survey|"
                          r"funding|offering|ipo|loan)\b", re.I)


def strict_status(title):
    """The stage signal when only main-clause stage words count."""
    if reg.fn.is_cancelled(title):
        before = title[:fn.CANCEL_RE.search(title).start()]
        if not BREAK.search(" ".join(before.split()[-4:])):
            return fn.CANCELLED
    for status, rx in fn.STATUS_RULES:
        for m in rx.finditer(title):
            before = " ".join(title[:m.start()].split()[-5:])
            if BREAK.search(before):
                continue
            # "Crusoe opens second Tulsa plant", "solar farm opens", "completes its application"
            if status == "Operational" and (NOT_DC.search(" ".join(title[:m.start()].split()[-3:]))
                                            or NOT_DC.search(" ".join(title[m.end():].split()[:3]))
                                            or NOT_BUILDING.search(title[m.end():])):
                continue
            return status
    return None


def sample(records, size):
    """A fixed, stratified sample: the same records every run until the registry changes."""
    pool = sorted((r for r in records.values() if not r.get("hidden") and r["news"] and not r.get("curated")),
                  key=lambda r: hashlib.sha1(r["id"].encode()).hexdigest())
    out = []
    for status, share in MIX.items():
        out += [r for r in pool if r["status"] == status][:round(size * share)]
    # A status with too few records leaves room: fill it with the next records in the fixed order.
    taken = {r["id"] for r in out}
    out += [r for r in pool if r["id"] not in taken][:max(0, size - len(out))]
    return out


def replay(r, reader):
    r = copy.deepcopy(r)
    for n in r["news"]:
        n["stage_signal"] = reader(n["title"])
    reg.derive(r, resignal=False)
    return r["status"], [(h["date"][:10], h["status"]) for h in r["status_history"]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=150)
    args = ap.parse_args()
    records = reg.load()
    rows, dis = [], []
    for r in sample(records, args.size):
        now, hist_now = replay(r, fn.guess_status)
        strict, hist_strict = replay(r, strict_status)
        heads = [{"id": n["id"], "title": n["title"], "published": n["published"][:10],
                  "rules": fn.guess_status(n["title"]), "strict": strict_status(n["title"])} for n in r["news"]]
        row = {"id": r["id"], "name": r["name"], "status_rules": now, "status_strict": strict,
               "history_rules": hist_now, "history_strict": hist_strict, "headlines": heads}
        rows.append(row)
        if now != strict:
            dis.append({"id": r["id"], "name": r["name"], "rules": now, "strict": strict,
                        "headlines": [h for h in heads if h["rules"] != h["strict"]]})
    prev = fn.load_json(OUT, {})
    doc = {
        "_readme": "Status audit written by scripts/status_audit.py. records: a fixed stratified sample of detected "
                   "registry records; for each, the status replayed from its headlines with the live rules "
                   "(status_rules, history_rules) and with a stricter main-clause reading (status_strict, "
                   "history_strict), and every headline's stage signal under both (rules, strict). "
                   "disagreements: records whose status differs, with the headlines that differ. previous_run: "
                   "the counts from the run before, to compare a rule change.",
        "generated": reg.now_iso(),
        "size": len(rows),
        "by_status": {s: sum(1 for x in rows if x["status_rules"] == s) for s in MIX},
        "disagreement_count": len(dis),
        "headline_disagreements": sum(1 for x in rows for h in x["headlines"] if h["rules"] != h["strict"]),
        "previous_run": {k: prev[k] for k in ("generated", "size", "disagreement_count", "headline_disagreements") if k in prev},
        "disagreements": dis,
        "records": rows,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(rows)} records, {len(dis)} status disagreements, {doc['headline_disagreements']} headline disagreements")
    for d in dis:
        print(f"- {d['id']}: rules {d['rules']} / strict {d['strict']}")
        for h in d["headlines"]:
            print(f"    {h['rules']} -> {h['strict']}: {h['title'][:110]}")


if __name__ == "__main__":
    main()
