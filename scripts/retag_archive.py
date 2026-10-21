#!/usr/bin/env python3
"""
One-time pass: re-tag every headline in data/archive/*.json with the current
rules in fetch_news.py (topic, places, companies, utilities, figures and story
clusters). Ids, titles, links, sources and dates are kept, and no entry is
removed; a headline the current filters would reject (off topic, a blocked
outlet, or outside the U.S.) keeps its entry with its topic refreshed and
"filtered": true, which the site uses to hide it.

    python scripts/retag_archive.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_news as fn  # noqa: E402

KEEP = ("id", "title", "link", "source", "published", "feed", "snippet")


def main():
    gaz, geo = fn.load_gazetteer()
    files = sorted(p for p in fn.ARCHIVE_DIR.glob("*.json") if fn.MONTH_RE.match(p.stem))
    months, everything, rejected = {}, [], []
    for path in files:
        items = fn.load_json(path, {}).get("items", [])
        out = []
        for old in items:
            it = {k: old[k] for k in KEEP if k in old}
            if not fn.tag_item(it, gaz, geo):
                # Keep the archived record; only its topic follows the new rules.
                it = dict(old)
                it["category"], it["tags"] = fn.classify(it["title"])
                it["filtered"] = True
                rejected.append(it)
            out.append(it)
        months[path] = out
        everything += out
    clusters = fn.cluster_items([i for i in everything if not i.get("filtered")])
    for path, items in months.items():
        items.sort(key=lambda x: x["published"], reverse=True)
        path.write_text(json.dumps({"month": path.stem, "count": len(items), "items": items},
                                   ensure_ascii=False, indent=1), encoding="utf-8")
    fn.write_archive_index(fn.ARCHIVE_DIR)
    shown = [i for i in everything if not i.get("filtered")]
    n = len(shown)
    print(f"Re-tagged {len(everything)} archived headlines in {len(files)} month files: {n} shown in {clusters} stories")
    for cat, c in Counter(i["category"] for i in shown).most_common():
        print(f"  {cat:22} {c:5} {100 * c / n:5.1f}%")
    print(f"{len(rejected)} are rejected by today's filters (kept, marked filtered):")
    for it in rejected[:12]:
        print("  -", it["source"], "|", it["title"][:110])


if __name__ == "__main__":
    main()
