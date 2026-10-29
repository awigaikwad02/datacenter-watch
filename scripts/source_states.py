#!/usr/bin/env python3
"""
The Rack Report: suggest home states for local news outlets (data/feeds.json "source_states").

What it is for: a local outlet's headline often names no state ("County approves data center
rules"), so the tagger falls back to the outlet's home state (location_precision "source").
This script finds outlets in the archive with at least MIN_HEADLINES headlines, of which at least
MIN_LOCATED name a place themselves, and at least SHARE of those are in one state. It prints the
suggestions; with --write it adds them to data/feeds.json (existing entries are never changed).

Outlets in NOT_LOCAL (companies, law firms, regional stations covering several states) are skipped,
and FIXED holds outlets whose majority state is wrong because their city name is ambiguous
(e.g. the Portland Press Herald is in Maine, not Oregon).

    python scripts/source_states.py           # print suggestions
    python scripts/source_states.py --write   # add them to data/feeds.json
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_news as fn  # noqa: E402

MIN_HEADLINES = 5
MIN_LOCATED = 3
SHARE = 0.8
NOT_LOCAL = {"Crusoe", "Entergy", "McGuireWoods", "WUSA9", "DC News Now", "Applied Digital Corporation (APLD)",
             "Pipeline and Gas Journal", "The Gazette", "The Mercury", "Leader Publications"}
FIXED = {
    "Portland Press Herald - Maine Sunday Telegram": "ME", "Columbus Ledger-Enquirer": "GA",
    "decaturish.com": "GA", "WCBD News 2": "SC", "WTVG": "OH", "Maryland Matters": "MD",
}


def suggest(items, known):
    """{outlet: state} for outlets not in `known` that meet the thresholds."""
    by = defaultdict(list)
    for it in items:
        by[it.get("source", "")].append(it)
    out = {}
    for src, its in by.items():
        if not src or src in known or src in NOT_LOCAL or len(its) < MIN_HEADLINES:
            continue
        if src in FIXED:
            out[src] = FIXED[src]
            continue
        # Only places named in the headline itself count, not an earlier outlet-state guess.
        st = Counter(i["state"] for i in its if i.get("state") and i.get("location_precision") != "source")
        located = sum(st.values())
        if located >= MIN_LOCATED:
            top, n = st.most_common(1)[0]
            if n / located >= SHARE:
                out[src] = top
    return out


def main():
    """Run the script (see the module docstring for what it does and its options)."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    gaz, geo = fn.load_gazetteer()
    geo.source_states.clear()  # measure from the headlines alone
    items = []
    for p in sorted(fn.ARCHIVE_DIR.glob("*.json")):
        if fn.MONTH_RE.match(p.stem):
            for old in fn.load_json(p, {}).get("items", []):
                it = {k: old[k] for k in ("id", "title", "source", "published", "snippet") if k in old}
                if fn.tag_item(it, gaz, geo):
                    items.append(it)
    cfg = fn.load_json(fn.FEEDS_FILE, {})
    known = cfg.get("source_states", {})
    new = suggest(items, known)
    for k, v in sorted(new.items()):
        print(f"{v}  {k}")
    print(f"{len(new)} new outlets ({len(known)} already listed)")
    if args.write and new:
        # source_states is the last block of feeds.json: append lines instead of reformatting the file.
        text = fn.FEEDS_FILE.read_text(encoding="utf-8").rstrip()
        assert text.endswith("}\n}") or text.endswith("}\r\n}"), "source_states must be the last block"
        body = text[:text.rindex("}", 0, text.rindex("}"))].rstrip()  # up to the last entry
        lines = ",\n".join(f"    {json.dumps(k, ensure_ascii=False)}: {json.dumps(v)}" for k, v in sorted(new.items()))
        fn.FEEDS_FILE.write_text(body + ",\n" + lines + "\n  }\n}\n", encoding="utf-8")
        assert fn.load_json(fn.FEEDS_FILE, {})["source_states"] == {**known, **new}


if __name__ == "__main__":
    main()
