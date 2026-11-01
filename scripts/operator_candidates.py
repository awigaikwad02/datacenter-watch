#!/usr/bin/env python3
"""
The Rack Report: list companies the news names often that are not tracked yet.

What it is for: operators are only recognised when they are in fetch_news.COMPANIES (or the
investor, builder, supplier and utility lists). This scans the archive for capitalised names
directly before "data center(s)", "announces", "breaks ground", "to build", "plans" and "files",
drops places (gazetteer names, counties, states), generic words and names already tracked, and
writes the 50 most frequent with example headlines to data/operator_candidates.json for a person
to review. Nothing is added automatically.

    python scripts/operator_candidates.py
"""

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_news as fn  # noqa: E402

OUT = fn.DATA / "operator_candidates.json"
LEAD = re.compile(r"((?:[A-Z][\w&.'’-]+ ){1,3})(?=(?:[Dd]ata [Cc]ent(?:er|re)s?|Datacent(?:er|re)s?|announces|Announces|breaks ground|"
                  r"Breaks Ground|to build|To Build|plans|Plans|files|Files|unveils|Unveils|acquires|Acquires)\b)")
# Generic words and people that the pattern catches (governors announcing policy are not operators).
SKIP_WORDS = {"Hochul", "Abbott", "Kotek", "Shapiro", "Youngkin", "Newsom", "Pritzker", "Whitmer", "DeSantis", "Landry", "Developer", "Company", "Two", "More", "Global", "Army", "Trump", "Mexico", "York", "Realty", "Prussia", "Indy",
              "South Side", "Silicon Valley", "Pa.", "AI-driven", "AI-ready", "Navy", "Air Force", "Tech", "Firm", "City", "State"}


def candidates(items, gaz, top=50):
    """[(name, count, examples)] for untracked names, most frequent first."""
    tracked = set(fn.COMPANY_ORDER) | {n for lst in (fn.INVESTORS, fn.BUILDERS, fn.SUPPLIERS, fn.UTILITIES) for n, _ in lst}
    count, examples = Counter(), defaultdict(list)
    for it in items:
        t = it["title"]
        if fn.title_case(t):
            continue
        for m in LEAD.finditer(t):
            words = m.group(1).split()
            while words and (words[0] in fn.NAME_GENERIC or words[0] in ("The", "A", "New")):
                words = words[1:]
            name = re.sub(r"['’]s?$", "", " ".join(words)).strip()
            if (len(name) < 3 or name in SKIP_WORDS or name in gaz or name in fn.STATE_CODES or name.endswith(("’s", "'s"))
                    or re.search(r"\b(County|Township|Twp\.?|Parish|City|Town|Village|Project|AI|Texas|Ohio|Virginia|Louisiana)\b", name)
                    or fn.find_companies(name) or any(name.startswith(x) for x in tracked | fn.CONTEXT_ONLY)
                    or any(w in gaz for w in [name.split()[0], name.split()[-1]])):
                continue
            count[name] += 1
            if len(examples[name]) < 3:
                examples[name].append(t)
    return [(n, k, examples[n]) for n, k in count.most_common(top)]


def main():
    """Scan the archive and write data/operator_candidates.json."""
    gaz, _ = fn.load_gazetteer()
    items = [i for p in sorted(fn.ARCHIVE_DIR.glob("2*.json")) for i in fn.load_json(p, {}).get("items", []) if not i.get("filtered")]
    rows = candidates(items, gaz)
    OUT.write_text(json.dumps({
        "_readme": fn.readme("operator_candidates.json"),
        "candidates": [{"name": n, "count": k, "examples": ex} for n, k, ex in rows],
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for n, k, ex in rows:
        print(f"{k:3} {n:28} {ex[0][:80]}")


if __name__ == "__main__":
    main()
