#!/usr/bin/env python3
"""
The Rack Report: add U.S. towns that the news mentions to scripts/gazetteer.json.

What it is for: a headline is located only when a place in it is in the gazetteer. This script
counts every U.S. town from GeoNames (towns of 1,000+ people, via the cities.json npm package,
CC BY 4.0, https://www.geonames.org) in the archived headlines that have no town or county yet,
and adds names seen at least MIN_MENTIONS times. A name found in one state gets one entry; a
name found in several states gets a list of candidates, and the tagger only uses it when the
headline or the outlet names the state (see find_locations in fetch_news.py).

Names are skipped when they are an English word ("Mobile", "Commerce"), or listed in DENY:
people, companies and projects that share a town's name, foreign places, and names that in
the news nearly always mean a county ("Coweta" is Coweta County, Georgia, not Coweta, Oklahoma).
Existing gazetteer entries are never changed. The coordinates come from GeoNames, never typed in.

    npm pack cities.json an-array-of-english-words   # in an empty folder, then untar both
    python scripts/gazetteer_towns.py CITIES_JSON WORDS_JSON          # print what would be added
    python scripts/gazetteer_towns.py CITIES_JSON WORDS_JSON --write  # add it
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_news as fn  # noqa: E402

MIN_MENTIONS = 3
DENY = set("""
Elon George Allen Ferguson Bernie Leon Vincent Jerome Clark Douglas Vance Harris Lucas Luther Moore Davis
Emerson Eaton Benson Scott Robinson Patterson Hancock Stanley Cameron Byron Boyd Snyder Hubbard Wayne Bradley
Crowley Erin Matthews Keller McDonald Remington Hawley Dryden Morton Bryan Abernathy Gonzalez Garfield
Wentworth Elizabeth Hampshire Greenland Southside Kenwood Lakeview Jupiter Dakota Lebanon Delhi Nottingham
Blackstone Gibraltar Niagara Coweta Calvert Putnam Middlesex Tarrant Caddo Osage Cherokee Carroll Knox Greene
Fayette Tazewell Pulaski Winnebago Trumbull Dinwiddie Powhatan Louisa Rockingham Calhoun Sedgwick Genesee
Nassau Meade Prince_George Box_Elder DeSoto De_Soto Martindale Brightwood Tri-Cities Orchard_Hills Central_City
Flint_City Oakland_City Middle_East White_House New_Kent Jefferson Cumberland Richland Forsyth Chatham
Shelby Benton Boone Fulton Hamilton Monroe Marion
""".replace("_", " ").split())
DENY = {d.replace(" ", " ") for d in DENY}
CODE_TO_STATE = {v: k for k, v in fn.STATE_CODES.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cities_json")
    ap.add_argument("words_json")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    words = set(json.loads(Path(args.words_json).read_text()))
    by_name = defaultdict(list)
    for c in json.loads(Path(args.cities_json).read_text()):
        if c["country"] == "US" and c["admin1"] in CODE_TO_STATE:
            by_name[c["name"]].append(c)
    gaz_doc = json.loads(fn.GAZ_FILE.read_text(encoding="utf-8"))
    have = set(gaz_doc)
    names = [n for n in by_name if n not in have and n not in DENY and len(n) > 3
             and (" " in n or n.lower() not in words)]
    rx = {n: re.compile(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])") for n in names}

    gaz, geo = fn.load_gazetteer()
    count = Counter()
    for p in sorted(fn.ARCHIVE_DIR.glob("*.json")):
        if not fn.MONTH_RE.match(p.stem):
            continue
        for old in fn.load_json(p, {}).get("items", []):
            it = {k: old[k] for k in ("id", "title", "source", "published", "snippet") if k in old}
            if not fn.tag_item(it, gaz, geo) or it.get("location_precision") in ("city", "county"):
                continue
            text = it["title"] + " " + it.get("snippet", "")
            count.update(n for n, r in rx.items() if n in text and r.search(text))

    added = {}
    for n, k in count.most_common():
        if k < MIN_MENTIONS:
            break
        # One state per name: GeoNames can list two places with one name in the same state.
        per_state = {}
        for c in by_name[n]:
            per_state.setdefault(c["admin1"], c)
        cands = [[round(float(c["lat"]), 4), round(float(c["lng"]), 4), 3,
                  f"{n}, {CODE_TO_STATE[c['admin1']]}, US", "US"] for _, c in sorted(per_state.items())]
        added[n] = cands[0] if len(cands) == 1 else cands
        print(f"{k:4}  {n}  ({', '.join(sorted(per_state))})")
    print(f"{len(added)} towns to add ({sum(isinstance(v[0], list) for v in added.values())} in several states)")
    if args.write and added:
        gaz_doc.update(added)
        gaz_doc["_readme"] = gaz_doc["_readme"].rstrip() + (
            "" if "GeoNames" in gaz_doc["_readme"] else
            " Towns added by scripts/gazetteer_towns.py come from GeoNames (CC BY 4.0, geonames.org); a town name"
            " found in several states holds a list of candidates and is used only when the story names the state.")
        # The file keeps one entry per line.
        lines = [f"{json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}" for k, v in gaz_doc.items()]
        fn.GAZ_FILE.write_text("{\n" + ",\n".join(lines) + "\n}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
