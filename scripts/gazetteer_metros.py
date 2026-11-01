#!/usr/bin/env python3
"""
The Rack Report: add the suburbs and counties of the largest U.S. data center metros.

What it is for: a headline about "Independence" or "Olathe" is a Kansas City story, and its
project must be pinned there, not stacked on downtown Kansas City. For each metro in METROS (its
core city and its main counties), this adds every GeoNames town of 1,000+ people in those
counties to scripts/gazetteer.json, and tags the metro's towns, counties and core city with the
metro's name. The tagger then:
  - prefers a suburb or county over the metro's core city when a headline names both;
  - resolves a town or county name found in several states ("Independence", "Clay County") to the
    one in the metro the story or the outlet belongs to (SOURCE_METROS, plus outlets named after
    the core city, such as "Kansas City Star");
  - only accepts town names that are also English words ("Liberty", "Independence") in
    sentence-case headlines, where the capital letter means a name.
It also adds landmark aliases (LANDMARKS: "Kansas City International Airport" is in Platte
County) and the split-state names (SPLIT: "Kansas City, Kansas" is Wyandotte County, not
Missouri; Texarkana, Bristol, Sioux City, Lake Tahoe).

Coordinates come only from GeoNames (towns, via the cities.json npm package, CC BY 4.0) and from
the gazetteer's existing Census county centroids; nothing is typed in by hand. Existing entries
are kept; a name already used for another place becomes a list of candidates.

    npm pack cities.json an-array-of-english-words   # in an empty folder, untar both
    python scripts/gazetteer_metros.py CITIES_DIR WORDS_JSON          # print what would change
    python scripts/gazetteer_metros.py CITIES_DIR WORDS_JSON --write  # write the gazetteer
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_news as fn  # noqa: E402
from gazetteer_towns import DENY as TOWN_DENY  # noqa: E402

# People and companies that share a town's name (see gazetteer_towns.py), except names asked for
# by place: De Soto, Kansas is a Kansas City suburb with data center projects.
DENY = TOWN_DENY - {"De Soto", "DeSoto"}
# Common surnames that are also suburb names: in the news they are nearly always people ("Jones digs in").
DENY |= set("""Jones Smith Johnson Williams Brown Miller Wilson Anderson Thomas White Martin Thompson Garcia Martinez Lewis
Lee Walker Hall Young King Wright Hill Green Adams Baker Nelson Carter Mitchell Perez Roberts Turner Phillips Campbell Evans
Edwards Collins Stewart Morris Murphy Cook Rogers Morgan Cooper Peterson Bailey Reed Kelly Howard Cox Ward Richardson Watson
Brooks Wood James Bennett Gray Hughes Price Sanders Myers Long Ross Foster Powell Jenkins Perry Russell Sullivan Bell Coleman
Butler Henderson Barnes Fisher Vasquez Simmons Graham Marshall Owens Harrison Gibson Wallace Hamilton Ellis Hunt Ford
Star Banks""".split())  # "Kansas City Star printing plant", "banks"

# Metro -> (core cities, counties as (state, "Name County")). Counties are the metro's central and
# fast-growing data center counties, not every county of the Census metro area.
METROS = {
    "Kansas City": (["Kansas City"], [("MO", "Jackson"), ("MO", "Clay"), ("MO", "Platte"), ("MO", "Cass"), ("KS", "Johnson"),
                                      ("KS", "Wyandotte"), ("KS", "Miami"), ("KS", "Leavenworth")]),
    "Atlanta": (["Atlanta"], [("GA", "Fulton"), ("GA", "DeKalb"), ("GA", "Cobb"), ("GA", "Gwinnett"), ("GA", "Clayton"), ("GA", "Douglas"),
                              ("GA", "Fayette"), ("GA", "Henry"), ("GA", "Coweta"), ("GA", "Newton"), ("GA", "Bartow"), ("GA", "Paulding")]),
    "Dallas-Fort Worth": (["Dallas", "Fort Worth"], [("TX", "Dallas"), ("TX", "Tarrant"), ("TX", "Collin"), ("TX", "Denton"), ("TX", "Ellis"),
                                                     ("TX", "Kaufman"), ("TX", "Rockwall"), ("TX", "Johnson"), ("TX", "Parker"), ("TX", "Hood")]),
    "Chicago": (["Chicago"], [("IL", "Cook"), ("IL", "DuPage"), ("IL", "Kane"), ("IL", "Will"), ("IL", "Lake"), ("IL", "McHenry"),
                              ("IL", "Kendall"), ("IN", "Lake")]),
    "Detroit": (["Detroit"], [("MI", "Wayne"), ("MI", "Oakland"), ("MI", "Macomb"), ("MI", "Washtenaw"), ("MI", "Livingston")]),
    "Phoenix": (["Phoenix"], [("AZ", "Maricopa"), ("AZ", "Pinal")]),
    "Columbus": (["Columbus"], [("OH", "Franklin"), ("OH", "Delaware"), ("OH", "Licking"), ("OH", "Fairfield"), ("OH", "Union"), ("OH", "Madison"),
                                ("OH", "Pickaway")]),
    "Indianapolis": (["Indianapolis"], [("IN", "Marion"), ("IN", "Hamilton"), ("IN", "Hendricks"), ("IN", "Johnson"), ("IN", "Boone"),
                                        ("IN", "Hancock"), ("IN", "Morgan"), ("IN", "Shelby")]),
    "Northern Virginia": (["Ashburn"], [("VA", "Loudoun"), ("VA", "Prince William"), ("VA", "Fairfax"), ("VA", "Fauquier"), ("VA", "Stafford"),
                                        ("VA", "Culpeper"), ("VA", "Spotsylvania")]),
    "Milwaukee": (["Milwaukee"], [("WI", "Milwaukee"), ("WI", "Waukesha"), ("WI", "Ozaukee"), ("WI", "Washington"), ("WI", "Racine"),
                                  ("WI", "Kenosha")]),
    "Minneapolis": (["Minneapolis", "St. Paul"], [("MN", "Hennepin"), ("MN", "Ramsey"), ("MN", "Dakota"), ("MN", "Anoka"), ("MN", "Washington"),
                                                  ("MN", "Scott"), ("MN", "Carver"), ("MN", "Wright"), ("MN", "Sherburne")]),
    "Denver": (["Denver"], [("CO", "Denver"), ("CO", "Adams"), ("CO", "Arapahoe"), ("CO", "Douglas"), ("CO", "Jefferson"), ("CO", "Broomfield"),
                            ("CO", "Weld")]),
    "Salt Lake City": (["Salt Lake City"], [("UT", "Salt Lake"), ("UT", "Davis"), ("UT", "Utah"), ("UT", "Tooele"), ("UT", "Weber")]),
    "Portland": (["Portland"], [("OR", "Multnomah"), ("OR", "Washington"), ("OR", "Clackamas"), ("WA", "Clark")]),
    "Seattle": (["Seattle"], [("WA", "King"), ("WA", "Snohomish"), ("WA", "Pierce")]),
    "Houston": (["Houston"], [("TX", "Harris"), ("TX", "Fort Bend"), ("TX", "Montgomery"), ("TX", "Brazoria"), ("TX", "Galveston"),
                              ("TX", "Waller")]),
    "San Antonio": (["San Antonio"], [("TX", "Bexar"), ("TX", "Comal"), ("TX", "Guadalupe"), ("TX", "Medina")]),
    "Austin": (["Austin"], [("TX", "Travis"), ("TX", "Williamson"), ("TX", "Hays"), ("TX", "Bastrop"), ("TX", "Caldwell")]),
    "Nashville": (["Nashville"], [("TN", "Davidson"), ("TN", "Williamson"), ("TN", "Rutherford"), ("TN", "Sumner"), ("TN", "Wilson"),
                                  ("TN", "Montgomery")]),
    "Charlotte": (["Charlotte"], [("NC", "Mecklenburg"), ("NC", "Cabarrus"), ("NC", "Gaston"), ("NC", "Union"), ("NC", "Iredell"),
                                  ("NC", "Catawba"), ("SC", "York"), ("SC", "Lancaster")]),
    "Richmond": (["Richmond"], [("VA", "Henrico"), ("VA", "Chesterfield"), ("VA", "Hanover"), ("VA", "Goochland"), ("VA", "Powhatan"),
                                ("VA", "New Kent")]),
    "Pittsburgh": (["Pittsburgh"], [("PA", "Allegheny"), ("PA", "Westmoreland"), ("PA", "Washington"), ("PA", "Butler"), ("PA", "Beaver")]),
    "Cleveland": (["Cleveland"], [("OH", "Cuyahoga"), ("OH", "Lake"), ("OH", "Lorain"), ("OH", "Medina"), ("OH", "Summit"), ("OH", "Geauga")]),
    "Cincinnati": (["Cincinnati"], [("OH", "Hamilton"), ("OH", "Butler"), ("OH", "Warren"), ("OH", "Clermont"), ("KY", "Boone"), ("KY", "Kenton"),
                                    ("KY", "Campbell")]),
    "St. Louis": (["St. Louis"], [("MO", "St. Louis"), ("MO", "St. Charles"), ("MO", "Jefferson"), ("MO", "Franklin"), ("MO", "Lincoln"),
                                  ("IL", "St. Clair"), ("IL", "Madison")]),
    "Omaha": (["Omaha"], [("NE", "Douglas"), ("NE", "Sarpy"), ("NE", "Cass"), ("IA", "Pottawattamie")]),
    "Des Moines": (["Des Moines"], [("IA", "Polk"), ("IA", "Dallas"), ("IA", "Warren"), ("IA", "Story"), ("IA", "Jasper")]),
    "Oklahoma City": (["Oklahoma City"], [("OK", "Oklahoma"), ("OK", "Canadian"), ("OK", "Cleveland"), ("OK", "Logan")]),
    "Tulsa": (["Tulsa"], [("OK", "Tulsa"), ("OK", "Rogers"), ("OK", "Wagoner"), ("OK", "Creek"), ("OK", "Mayes")]),
    "Memphis": (["Memphis"], [("TN", "Shelby"), ("TN", "Tipton"), ("TN", "Fayette"), ("MS", "DeSoto"), ("AR", "Crittenden")]),
    "Louisville": (["Louisville"], [("KY", "Jefferson"), ("KY", "Oldham"), ("KY", "Bullitt"), ("KY", "Shelby"), ("IN", "Clark"), ("IN", "Floyd")]),
    "Birmingham": (["Birmingham"], [("AL", "Jefferson"), ("AL", "Shelby"), ("AL", "St. Clair"), ("AL", "Tuscaloosa")]),
    "Jacksonville": (["Jacksonville"], [("FL", "Duval"), ("FL", "Clay"), ("FL", "St. Johns"), ("FL", "Nassau")]),
    "Tampa": (["Tampa"], [("FL", "Hillsborough"), ("FL", "Pinellas"), ("FL", "Pasco"), ("FL", "Polk")]),
    "Orlando": (["Orlando"], [("FL", "Orange"), ("FL", "Seminole"), ("FL", "Osceola"), ("FL", "Lake")]),
    "Las Vegas": (["Las Vegas"], [("NV", "Clark"), ("NV", "Nye")]),
    "Reno": (["Reno"], [("NV", "Washoe"), ("NV", "Storey"), ("NV", "Lyon")]),
    "Sacramento": (["Sacramento"], [("CA", "Sacramento"), ("CA", "Placer"), ("CA", "El Dorado"), ("CA", "Yolo")]),
    "San Jose": (["San Jose"], [("CA", "Santa Clara"), ("CA", "San Mateo"), ("CA", "Alameda")]),
    "Boise": (["Boise"], [("ID", "Ada"), ("ID", "Canyon")]),
    "Albuquerque": (["Albuquerque"], [("NM", "Bernalillo"), ("NM", "Sandoval"), ("NM", "Valencia")]),
}

# Outlets that cover a metro but are not named after its core city. Outlets whose name contains a
# core city ("Kansas City Star", "KSHB 41 Kansas City") are matched automatically.
SOURCE_METROS = {
    "KCTV": "Kansas City", "KMBC": "Kansas City", "FOX4KC.com": "Kansas City", "KCUR": "Kansas City", "KSHB": "Kansas City",
    "The Business Journal": None, "Johnson County Post": "Kansas City", "The Kansas City Beacon": "Kansas City",
    "WSB-TV": "Atlanta", "11Alive.com": "Atlanta", "AJC.com": "Atlanta", "The Atlanta Journal-Constitution": "Atlanta",
    "WFAA": "Dallas-Fort Worth", "KXAS": "Dallas-Fort Worth", "Fort Worth Star-Telegram": "Dallas-Fort Worth",
    "WXYZ 7 News Detroit": "Detroit", "ClickOnDetroit | WDIV Local 4": "Detroit", "WFYI": "Indianapolis", "IndyStar": "Indianapolis",
    "WTHR": "Indianapolis", "wthr.com": "Indianapolis", "Mirror Indy": "Indianapolis", "10TV": "Columbus", "WSYX": "Columbus",
    "Star Tribune": "Minneapolis", "kare11.com": "Minneapolis", "MPR News": "Minneapolis", "Pioneer Press": "Minneapolis",
    "KSL News": "Salt Lake City", "ABC4 Utah": "Salt Lake City", "KUTV": "Salt Lake City", "WSMV": "Nashville", "The Tennessean": "Nashville",
    "WCNC": "Charlotte", "WBTV": "Charlotte", "WSOC TV": "Charlotte", "WTVR": "Richmond", "WWBT": "Richmond", "VPM": "Richmond",
    "WTAE": "Pittsburgh", "KDKA": "Pittsburgh", "News 5 Cleveland WEWS": "Cleveland", "Signal Cleveland": "Cleveland", "WLWT": "Cincinnati",
    "KSDK": "St. Louis", "STLtoday.com": "St. Louis", "KETV": "Omaha", "KOCO": "Oklahoma City", "KFOR": "Oklahoma City", "News 9": "Oklahoma City",
    "News On 6": "Tulsa", "KTUL": "Tulsa", "2 News Oklahoma KJRH Tulsa": "Tulsa", "Action News 5": "Memphis", "FOX13 Memphis": "Memphis",
    "WREG.com": "Memphis", "Daily Memphian": "Memphis", "WDRB": "Louisville", "WLKY": "Louisville", "The Courier-Journal": "Louisville",
    "WBRC 6 News": "Birmingham", "AL.com": None, "firstcoastnews.com": "Jacksonville", "WTSP": "Tampa", "wtsp.com": "Tampa",
    "Bay News 9": "Tampa", "WFTV": "Orlando", "Orlando Sentinel": "Orlando", "KTNV Las Vegas": "Las Vegas", "Las Vegas Review-Journal": "Las Vegas",
    "KLAS 8 News Now": "Las Vegas", "This Is Reno": "Reno", "Reno Gazette Journal": "Reno", "KTVN": "Reno", "KCRA": "Sacramento",
    "San José Spotlight": "San Jose", "The Mercury News": "San Jose", "Boise Dev": "Boise", "Idaho Statesman": "Boise", "KTVB": "Boise",
    "KOB 4": "Albuquerque", "KOAT": "Albuquerque", "Albuquerque Journal": "Albuquerque", "Houston Chronicle": "Houston",
    "ABC13 Houston": "Houston", "Houston Public Media": "Houston", "San Antonio Express-News": "San Antonio", "MySA": "San Antonio",
    "kens5.com": "San Antonio", "KXAN Austin": "Austin", "KUT": "Austin", "Austin American-Statesman": "Austin", "FOX 7 Austin": "Austin",
    "9News": "Denver", "Denver7": "Denver", "The Denver Post": "Denver", "Denverite": "Denver", "KING5.com": "Seattle",
    "The Seattle Times": "Seattle", "KIRO 7 News Seattle": "Seattle", "KGW": "Portland", "KATU": "Portland", "KOIN.com": "Portland",
    "Oregon Public Broadcasting - OPB": "Portland", "AZ Family": "Phoenix", "azcentral.com and The Arizona Republic": "Phoenix",
    "KJZZ": "Phoenix", "TMJ4 News": "Milwaukee", "WISN": "Milwaukee", "FOX6 News Milwaukee": "Milwaukee",
    "BizTimes - Milwaukee Business News": "Milwaukee", "InsideNoVa": "Northern Virginia", "Loudoun Times-Mirror": "Northern Virginia",
    "Prince William Times": "Northern Virginia", "FFXnow": "Northern Virginia", "Potomac Local News": "Northern Virginia",
}

# Places that are not towns but pin a story to a county.
LANDMARKS = {
    "Kansas City International Airport": ("MO", "Platte"), "Kansas City airport": ("MO", "Platte"), "KCI": ("MO", "Platte"),
    "Kansas City’s Northland": ("MO", "Platte"), "Kansas City's Northland": ("MO", "Platte"),
}

# Names that cross a state line. Each spelling maps to (state, GeoNames town) or (state, "X County").
SPLIT = {
    "Kansas City, Kansas": ("KS", "Wyandotte County"), "Kansas City, Kan.": ("KS", "Wyandotte County"),
    "Kansas City, KS": ("KS", "Wyandotte County"), "KCK": ("KS", "Wyandotte County"),
    "Texarkana, Texas": ("TX", "Texarkana"), "Texarkana, TX": ("TX", "Texarkana"),
    "Texarkana, Arkansas": ("AR", "Texarkana"), "Texarkana, Ark.": ("AR", "Texarkana"), "Texarkana, AR": ("AR", "Texarkana"),
    "Bristol, Tennessee": ("TN", "Bristol"), "Bristol, Tenn.": ("TN", "Bristol"), "Bristol, TN": ("TN", "Bristol"),
    "Bristol, Virginia": ("VA", "Bristol"), "Bristol, Va.": ("VA", "Bristol"), "Bristol, VA": ("VA", "Bristol"),
    "Sioux City": ("IA", "Sioux City"), "South Sioux City": ("NE", "South Sioux City"), "North Sioux City": ("SD", "North Sioux City"),
    "South Lake Tahoe": ("CA", "South Lake Tahoe"), "Stateline": ("NV", "Stateline"), "Incline Village": ("NV", "Incline Village"),
}
# Bare names that are candidates in both states (resolved by the story's state or metro).
SPLIT_BARE = {"Texarkana": [("TX", "Texarkana"), ("AR", "Texarkana")], "Lake Tahoe": [("CA", "South Lake Tahoe"), ("NV", "Incline Village")]}


def entry(c, name, state_name, metro=None):
    """A gazetteer entry for a GeoNames town, tagged with its metro."""
    e = [round(float(c["lat"]), 4), round(float(c["lng"]), 4), 3, f"{name}, {state_name}, US", "US"]
    return e + [metro] if metro else e


def main():
    """Build the metro additions and, with --write, merge them into scripts/gazetteer.json."""
    ap = argparse.ArgumentParser()
    ap.add_argument("cities_dir", help="the untarred cities.json package (cities.json and admin2.json)")
    ap.add_argument("words_json")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    code_state = {v: k for k, v in fn.STATE_CODES.items()}
    words = set(json.loads(Path(args.words_json).read_text()))
    all_cores = {core for cores, _ in METROS.values() for core in cores}
    # Organisation names are never towns here ("Oracle, Arizona" would catch every Oracle headline).
    orgs = set(fn.COMPANY_ORDER) | fn.CONTEXT_ONLY | {n for lst in (fn.INVESTORS, fn.BUILDERS, fn.SUPPLIERS, fn.UTILITIES) for n, _ in lst}
    # A name that was one well-known place before stays the default when a story gives no other clue.
    defaults = {k: v[3] for k, v in json.loads(fn.GAZ_FILE.read_text(encoding="utf-8")).items()
                if not k.startswith("_") and v and not isinstance(v[0], list) and v[2] == 3}
    cities = [c for c in json.loads((Path(args.cities_dir) / "cities.json").read_text()) if c["country"] == "US"]
    admin2 = {a["code"]: a["name"] for a in json.loads((Path(args.cities_dir) / "admin2.json").read_text()) if a["code"].startswith("US.")}
    county_code = {(code.split(".")[1], name.replace(" County", "").replace(" Parish", "").replace("Saint ", "St. ")): code.split(".")[2]
                   for code, name in admin2.items()}
    by_name_state = {(c["name"], c["admin1"]): c for c in cities}
    gaz = json.loads(fn.GAZ_FILE.read_text(encoding="utf-8"))
    prior = {k for k in gaz if not k.startswith("_")}
    word_names, new_names, context_names = set(), set(), set()
    geo_states = defaultdict(set)   # GeoNames: name -> the states that have a place of that name
    for c in cities:
        geo_states[c["name"]].add(c["admin1"])
    added, tagged, missing = defaultdict(list), 0, []

    def cands(key):
        v = gaz.get(key)
        return [] if v is None else fn.entry_candidates(v)

    def put(key, e):
        """Add a candidate under key, merging with what is there (one entry per display name)."""
        nonlocal tagged
        have = cands(key)
        for i, h in enumerate(have):
            # Same place, or another place of that name already listed in the same state: keep it, tag its metro.
            if h[3] == e[3] or (h[2] == 3 and fn.state_of({"name": h[3]}) == fn.state_of({"name": e[3]})):
                if len(e) > 5 and (len(h) < 6 or h[5] != e[5]):
                    have[i] = h[:5] + [e[5]]
                    tagged += 1
                gaz[key] = have[0] if len(have) == 1 else have
                return
        have.append(e)
        added[key].append(e[3])
        gaz[key] = have[0] if len(have) == 1 else have

    for metro, (cores, counties) in METROS.items():
        for st, county in counties:
            code = county_code.get((st, county))
            if not code:
                missing.append(f"{county} County, {st}")
                continue
            ckey = f"{county} County"
            for i, h in enumerate(cands(ckey)):          # tag the existing Census county centroid
                if h[3] == f"{ckey}, {code_state[st]}, US":
                    put(ckey, h[:5] + [metro])
            for c in cities:
                name = c["name"]
                if (c["admin1"] != st or c["admin2"] != code or name in all_cores or name in DENY or name in fn.STATE_CODES
                        or name in orgs):
                    continue
                if any(h[2] != 3 for h in cands(name)):     # never turn a state or country key into a town
                    continue
                new = name not in prior
                put(name, entry(c, name, code_state[st], metro))
                if new:
                    new_names.add(name)
                    if name.lower() in words and " " not in name:
                        word_names.add(name)
                    if len(geo_states[name]) > 1:
                        context_names.add(name)
                    if c["name"].lower() in words and " " not in c["name"]:
                        word_names.add(c["name"])
        for core in cores:
            for h in cands(core):
                if any(h[3] == f"{core}, {code_state[st]}, US" for st, _ in counties):
                    put(core, h[:5] + [metro])
            gaz.setdefault("_metro_cores", {})[core] = metro
    for name, (st, county) in LANDMARKS.items():
        base = next(h for h in cands(f"{county} County") if h[3] == f"{county} County, {code_state[st]}, US")
        gaz[name] = base[:5] + ([base[5]] if len(base) > 5 else [])
    for name, (st, target) in SPLIT.items():
        if target.endswith("County"):
            base = next(h for h in cands(target) if h[3] == f"{target}, {code_state[st]}, US")
            gaz[name] = list(base)
        else:
            c = by_name_state.get((target, st))
            if c:
                gaz[name] = entry(c, target, code_state[st])
    for name, pairs in SPLIT_BARE.items():
        gaz[name] = [entry(by_name_state[(t, st)], t, code_state[st]) for st, t in pairs if (t, st) in by_name_state]
    gaz["_word_names"] = sorted(word_names)
    gaz["_new_names"] = sorted(new_names)
    gaz["_context_names"] = sorted(context_names)
    gaz["_defaults"] = {k: v for k, v in defaults.items() if isinstance(gaz.get(k), list) and isinstance(gaz[k][0], list)}
    gaz["_source_metros"] = {k: v for k, v in SOURCE_METROS.items() if v}

    print(f"{sum(len(v) for v in added.values())} candidates added under {len(added)} names ({len(new_names)} new names, "
          f"{len(context_names)} needing context), {tagged} entries tagged with a metro, {len(word_names)} word names; "
          f"counties not found: {missing}")
    if args.write:
        gaz["_readme"] = gaz["_readme"].rstrip() + ("" if "metro" in gaz["_readme"] else
            " A sixth element names the metro a town, county or core city belongs to (scripts/gazetteer_metros.py); "
            "_metro_cores, _word_names, _new_names, _context_names, _source_metros and _defaults are used by the tagger to prefer suburbs and counties over a "
            "metro's core city, accept English-word town names only in sentence-case headlines, and resolve ambiguous "
            "names to the outlet's metro.")
        meta = {k: gaz.pop(k) for k in ("_readme", "_metro_cores", "_word_names", "_new_names", "_context_names",
                                        "_source_metros", "_defaults")}
        lines = [f"{json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}" for k, v in {**meta, **gaz}.items()]
        fn.GAZ_FILE.write_text("{\n" + ",\n".join(lines) + "\n}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
