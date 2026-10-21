#!/usr/bin/env python3
"""
Exit 0 when this run changed the data, 1 when it did not.

Used by the workflow so an hour with no new headlines makes no commit: the
"updated" timestamps (and data/status.json) always change, so instead we
compare the item ids and cluster ids of data/news.json and
data/project_candidates.json with the committed versions, and check whether
the archive gained anything.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = {"data/news.json": "items", "data/project_candidates.json": "projects"}


def signature(text, key):
    try:
        rows = json.loads(text).get(key, [])
    except (json.JSONDecodeError, AttributeError):
        return None
    return sorted((r.get("id"), r.get("cluster_id")) for r in rows)


def committed(path):
    r = subprocess.run(["git", "show", "HEAD:" + path], cwd=ROOT, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def main():
    if not committed("data/status.json"):
        print("data/status.json is not committed yet")
        return 0
    for path, key in FILES.items():
        now = (ROOT / path).read_text(encoding="utf-8") if (ROOT / path).exists() else ""
        if signature(now, key) != signature(committed(path), key):
            print(f"{path}: items changed")
            return 0
    archive = subprocess.run(["git", "status", "--porcelain", "--", "data/archive"], cwd=ROOT, capture_output=True, text=True).stdout
    if archive.strip():
        print("data/archive changed")
        return 0
    print("No new or changed items; only timestamps moved")
    return 1


if __name__ == "__main__":
    sys.exit(main())
