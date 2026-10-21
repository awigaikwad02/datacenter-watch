#!/usr/bin/env python3
"""
Seed data/archive/ from every version of data/news.json in git history.

Run once from the repository root (safe to re-run: the archive only ever
appends headlines it has not seen):

    python scripts/seed_archive.py

Each historical headline is re-tagged with the current rules in
fetch_news.py, so stories outside the United States are left out, the same
as on the live site.
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_news as fn  # noqa: E402


def git(*args):
    return subprocess.run(["git", *args], cwd=fn.ROOT, check=True, capture_output=True).stdout


def main():
    gaz, patterns = fn.load_gazetteer()
    shas = git("log", "--format=%H", "--", "data/news.json").decode().split()
    seen = {}
    versions = 0
    # Oldest first, so a later version of the same headline wins
    for sha in reversed(shas):
        try:
            data = json.loads(git("show", sha + ":data/news.json"))
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            continue
        versions += 1
        for it in data.get("items", []):
            if it.get("id") and it.get("published") and it.get("title"):
                seen[it["id"]] = it
    for it in fn.load_json(fn.NEWS_FILE, {}).get("items", []):
        seen[it["id"]] = it

    kept, dropped = [], 0
    for it in seen.values():
        it = dict(it)
        if fn.tag_item(it, gaz, patterns):
            kept.append(it)
        else:
            dropped += 1
    kept.sort(key=lambda x: x["published"], reverse=True)
    added = fn.archive_items(kept, fn.ARCHIVE_DIR)
    print(f"Read {versions} versions of data/news.json and the current file: {len(seen)} unique headlines")
    print(f"Archived {added} new headlines; {dropped} were outside the U.S. and left out")
    index = json.loads((fn.ARCHIVE_DIR / "index.json").read_text())
    print(f"Archive now holds {index['total']} headlines from {index['earliest']} to {index['latest']}")


if __name__ == "__main__":
    sys.exit(main())
