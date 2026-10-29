"""
Permanent project registry: data/registry.json.

Every project-shaped headline (a U.S. place, a site word and a stage word) is attached
to one record, and records are never deleted. A record keeps all of its headlines; its
status, status history, events, figures and confidence are rebuilt every run by
replaying those headlines in date order, so merges and splits from
data/project_overrides.json always produce a consistent history.

Curated projects come from data/projects.json (the human-edited source), re-imported
every run; their fields win over detected values.

Used by scripts/fetch_news.py (update) and runnable on its own for the one-time backfill:

    python scripts/registry.py --backfill
"""

import argparse
import html
import json
import math
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_news as fn  # noqa: E402

REGISTRY_FILE = fn.DATA / "registry.json"
OVERRIDES_FILE = fn.DATA / "project_overrides.json"
PROJECTS_FILE = fn.DATA / "projects.json"
PAGES_DIR = fn.ROOT / "projects"
SITEMAP_FILE = fn.ROOT / "sitemap.xml"
SITE = "https://therackreport.org"

CANCELLED = fn.CANCELLED
STAGE = {"Announced": 1, "Under construction": 2, "Operational": 3}
STATUSES = ("Announced", "Planned", "Under construction", "Operational", CANCELLED)
CODE_NAMES = ["Stargate", "Hyperion", "Prometheus", "Fairwater", "Project Rainier", "Colossus", "Project Matador"]
NO_COMPANY_JACCARD = 0.4
NO_COMPANY_DAYS = 60
MAX_PAGES_PER_RECORD = 2000      # above this many records, write one page per state instead
MAX_PAGES_BYTES = 5 * 1024 * 1024
SLUG_ALIAS = {"Amazon": "aws"}

APPROVAL_RE = re.compile(r"\b(approv(e|es|ed|al|als)|green-?lights?|green light|clears? (a |the |key |final )?(vote|hurdle|review|step)|"
                         r"grants? (a )?(permit|approval|rezoning)|signs? off|rezoning (passes|approved))\b", re.I)
POWER_RE = re.compile(r"\b(power (purchase|supply) agreements?|ppas?|power deals?|energy (deal|agreement|contract)s?|"
                      r"electric(ity)? (deal|agreement|contract|service agreement)s?|(utility|power) (deal|agreement|contract)s?)\b", re.I)


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse(s):
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")


def short_place(display):
    """'Richmond County, North Carolina, US' -> 'Richmond County'."""
    return (display or "").split(",")[0].strip()


# ---------------------------------------------------------------------------
# Loading and saving
# ---------------------------------------------------------------------------
def load(path=REGISTRY_FILE):
    doc = fn.load_json(path, {})
    return {r["id"]: r for r in doc.get("records", [])}


def save(records, path=REGISTRY_FILE):
    recs = sorted(records.values(), key=lambda r: (not r.get("curated"), r["id"]))
    doc = {
        "_readme": "Permanent project registry written by scripts/fetch_news.py. Never trimmed; records are hidden, not "
                   "deleted. Curated records come from data/projects.json; corrections go in data/project_overrides.json.",
        "updated": now_iso(),
        "count": len(recs),
        "visible": sum(1 for r in recs if not r.get("hidden")),
        "records": recs,
    }
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def load_overrides(path=None):
    """The operations in data/project_overrides.json (the module-level path is read at call time,
    so tests can point OVERRIDES_FILE somewhere else)."""
    return [op for op in fn.load_json(path or OVERRIDES_FILE, {}).get("operations", []) if isinstance(op, dict) and op.get("op")]


# ---------------------------------------------------------------------------
# Curated import
# ---------------------------------------------------------------------------
def place_fields(location, precision):
    """city/county strings in the same 'Name, State, US' form the tagger produces."""
    loc = location if not location or location.endswith(", US") else location + ", US"
    first = short_place(loc)
    county = loc if re.search(r" (County|Parish)$", first) else None
    city = loc if precision == "city" and not county else None
    return city, county


def import_curated(records):
    curated = fn.load_json(PROJECTS_FILE, {}).get("projects", [])
    for p in curated:
        r = records.get(p["id"]) or {"id": p["id"], "news": [], "first_seen": None}
        loc = p.get("location", "")
        loc = loc if loc.endswith(", US") else loc + ", US"
        city, county = place_fields(loc, "city")
        r.update({
            "name": p["name"], "company": p.get("company", ""), "companies": p.get("companies", []),
            "location": loc, "state": p.get("state"), "county": county, "city": city,
            "lat": p["lat"], "lon": p["lon"], "precision": "city",
            "curated": True, "verified": bool(p.get("verified")), "notes": p.get("notes", ""),
            "timeline": p.get("timeline", []), "announced": p.get("announced"),
            "curated_status": p["status"], "curated_capacity_mw": p.get("capacity_mw"),
            "curated_investment_usd_b": p.get("investment_usd_b"),
        })
        r.setdefault("imported", now_iso()[:10])  # first run that saw this curated project
        records[p["id"]] = r
    return {p["id"] for p in curated}


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------
def project_shaped(it):
    return bool(it.get("locations")) and bool(fn.PROJECT_WORDS.search(it["title"])) and bool(fn.guess_status(it["title"]))


class Matcher:
    def __init__(self, records, gaz):
        self.records = records
        self.gaz = gaz
        self.reindex()

    def reindex(self):
        self.by_news, self.by_cluster = {}, {}
        # Lookup indexes for rules c-e, so matching stays fast with tens of thousands of
        # headlines. Each list keeps record order, so the first match is the same as a scan.
        self.order, self.by_place, self.by_state, self.no_company, self.by_hint, self.by_any_place = {}, {}, {}, {}, {}, {}
        for r in self.records.values():
            self.index(r)
            for n in r["news"]:
                self.by_news[n["id"]] = r["id"]
                if n.get("cluster_id"):
                    self.by_cluster.setdefault(n["cluster_id"], r["id"])
        curated = [r["name"] for r in self.records.values() if r.get("curated") and len(r["name"]) >= 6]
        aliases = [a for r in self.records.values() for a in r.get("aliases", [])]
        names = sorted(set(CODE_NAMES + curated + aliases), key=len, reverse=True)
        self.code_rx = [(n, re.compile(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])", re.I)) for n in names]

    def index(self, r):
        self.order.setdefault(r["id"], len(self.order))
        places = [p for p in (r.get("county"), r.get("city")) if p]
        for p in places:
            self.by_any_place.setdefault(p, []).append(r["id"])
        for h in r.get("name_hints", []):
            self.by_hint.setdefault((h.lower(), r.get("state")), []).append(r["id"])
        for c in r.get("companies", []):
            for p in places:
                self.by_place.setdefault((c, p), []).append(r["id"])
            if r.get("precision") in ("state", "source"):
                self.by_state.setdefault((c, r.get("state")), []).append(r["id"])
        if not r.get("companies"):
            for p in places:
                self.no_company.setdefault(p, []).append(r["id"])

    def first(self, rids):
        live = [rid for rid in dict.fromkeys(rids) if rid in self.records and not self.records[rid].get("hidden")]
        return min(live, key=lambda rid: self.order.get(rid, 1e9)) if live else None

    def resolve(self, rid):
        seen = set()
        while rid in self.records and self.records[rid].get("merged_into") and rid not in seen:
            seen.add(rid)
            rid = self.records[rid]["merged_into"]
        return rid

    def live(self):
        return [r for r in self.records.values() if not r.get("hidden")]

    @staticmethod
    def info(it):
        locs = it.get("locations", [])
        city = next((l["name"] for l in locs if l.get("precision") == "city"), None)
        return {
            "companies": set(it.get("companies", [])), "state": it.get("state"), "county": it.get("county"),
            "city": city, "precision": it.get("location_precision") or (locs[0].get("precision") if locs else None),
            "words": fn.title_words(it["title"], it.get("source", "")), "t": parse(it["published"]),
            "hint": it.get("name_hint"),
            # Builders and suppliers never create a project (see process).
            "vendors_only": not it.get("companies") and bool(it.get("builders") or it.get("suppliers")),
        }

    def code_names(self, title):
        return [n for n, rx in self.code_rx if rx.search(title)]

    def match(self, it, inf):
        # a. a headline from the same story cluster is already attached
        rid = self.by_cluster.get(it.get("cluster_id"))
        if rid:
            return self.resolve(rid), "cluster"
        # b. a project code name in the title
        for code in self.code_names(it["title"]):
            c = code.lower()
            cands = [r for r in self.live() if c in r["name"].lower() or c in (a.lower() for a in r.get("aliases", []))]
            same = [r for r in cands if r.get("state") == inf["state"]] if inf["state"] else cands
            if same:
                same.sort(key=lambda r: (not r.get("curated"), -len(r["news"])))
                return same[0]["id"], "code name " + code
        # b2. the same project name ("Project Sail", "Wildcat Ridge Data Center") in the same state,
        #     when the operators agree or one side names none
        if inf["hint"] and inf["state"]:
            for rid in self.by_hint.get((inf["hint"].lower(), inf["state"]), []):
                r = self.records.get(rid)
                if r and not r.get("hidden") and (not inf["companies"] or not r.get("companies") or inf["companies"] & set(r["companies"])):
                    return self.resolve(rid), "name " + inf["hint"]
        # c. same company and same county or city (no time limit)
        places = [p for p in (inf["county"], inf["city"]) if p]
        if inf["companies"]:
            rid = self.first([x for c in inf["companies"] for p in places for x in self.by_place.get((c, p), [])])
            if rid:
                return rid, "company + place"
            # d. same company and state, existing record known only to the state (no time limit)
            rid = self.first([x for c in inf["companies"] for x in self.by_state.get((c, inf["state"]), [])
                              if self.records[x].get("precision") in ("state", "source")])
            if rid:
                return rid, "company + state"
        # e. no company on either side, same place and similar title within 60 days
        elif places:
            for rid in sorted(dict.fromkeys(x for p in places for x in self.no_company.get(p, [])), key=lambda x: self.order.get(x, 1e9)):
                r = self.records[rid]
                if r.get("hidden") or r.get("companies"):
                    continue
                for n in r["news"]:
                    t = parse(n["published"])
                    if t and inf["t"] and abs((inf["t"] - t).days) <= NO_COMPANY_DAYS and \
                            fn.jaccard(inf["words"], fn.title_words(n["title"], n.get("source", ""))) >= NO_COMPANY_JACCARD:
                        return r["id"], "place + similar title"
        # f. a builder or supplier headline ("Mortenson breaks ground in Hermantown") joins the one
        #    project already tracked at that place, whatever its operator; with two or more it joins none
        if inf["vendors_only"] and places:
            live = list(dict.fromkeys(x for p in places for x in self.by_any_place.get(p, [])
                                      if not self.records[x].get("hidden")))
            if len(live) == 1:
                return live[0], "vendor + place"
        return None, None

    # ------------------------------------------------------------------
    def new_id(self, base):
        rid, i = base, 2
        while rid in self.records:
            rid, i = f"{base}-{i}", i + 1
        return rid

    def create(self, it, inf, codes):
        loc = next((l for l in it["locations"] if l.get("precision") in ("city", "county")), it["locations"][0])
        company = sorted(inf["companies"], key=lambda n: fn.COMPANY_ORDER.get(n, 99))[0] if inf["companies"] else None
        place = short_place(loc["name"])
        year = it["published"][:4]
        co = SLUG_ALIAS.get(company, slug(company)) if company else "site"
        rid = self.new_id(f"{co}-{slug(place)}-{(inf['state'] or 'us').lower()}-{year}")
        name = (f"{codes[0]} ({place})" if codes else f"{company} {place} data center" if company
                else f"{inf['hint']} ({place})" if inf["hint"] else f"{place} data center")
        r = {
            "id": rid, "name": name, "company": ", ".join(sorted(inf["companies"], key=lambda n: fn.COMPANY_ORDER.get(n, 99))),
            "companies": sorted(inf["companies"], key=lambda n: fn.COMPANY_ORDER.get(n, 99)),
            "location": loc["name"], "state": inf["state"],
            "county": inf["county"] if loc.get("precision") in ("city", "county") else None,
            "city": inf["city"], "lat": loc["lat"], "lon": loc["lon"], "precision": loc.get("precision"),
            "curated": False, "verified": False, "notes": "", "news": [], "first_seen": it["published"],
            "name_hints": [inf["hint"]] if inf["hint"] else [],
        }
        self.records[rid] = r
        self.index(r)
        # An umbrella for the same company and state now has a named site: fold it in.
        for c in r["companies"]:
            u = self.umbrella(c, inf["state"])
            if u and not u.get("hidden"):
                self.merge(u["id"], rid)
        return rid

    def umbrella(self, company, state):
        return next((r for r in self.records.values() if r.get("umbrella") and r.get("umbrella_company") == company
                     and r.get("state") == state), None)

    def create_umbrella(self, company, state):
        name_state = next((n for n, c in fn.STATE_CODES.items() if c == state), state)
        entry = fn.entry_candidates(self.gaz.get(name_state, [0, 0, 2, name_state]))[0] if name_state in self.gaz else None
        co = SLUG_ALIAS.get(company, slug(company))
        rid = self.new_id(f"{co}-{state.lower()}-unnamed")
        self.records[rid] = {
            "id": rid, "name": f"{company}, {name_state} (site not yet named)", "company": company, "companies": [company],
            "location": f"{name_state}, US", "state": state, "county": None, "city": None,
            "lat": entry[0] if entry else None, "lon": entry[1] if entry else None, "precision": "state",
            "curated": False, "verified": False, "notes": "", "umbrella": True, "umbrella_company": company,
            "news": [], "first_seen": None,
        }
        self.index(self.records[rid])
        return rid

    def merge(self, src, dst, reason="merged"):
        s, d = self.records[src], self.records[dst]
        have = {n["id"] for n in d["news"]}
        d["news"].extend(n for n in s["news"] if n["id"] not in have)
        s["news"] = []
        s["hidden"], s["merged_into"] = True, dst
        for n in d["news"]:
            self.by_news[n["id"]] = dst

    def attach(self, rid, it, stage):
        r = self.records[rid]
        if any(n["id"] == it["id"] for n in r["news"]):
            return
        r["news"].append({"id": it["id"], "title": it["title"], "link": it["link"], "source": it.get("source", ""),
                          "published": it["published"], "stage_signal": stage, "cluster_id": it.get("cluster_id")})
        self.by_news[it["id"]] = rid
        if it.get("cluster_id"):
            self.by_cluster.setdefault(it["cluster_id"], rid)
        hint = it.get("name_hint")
        if hint and hint not in r.setdefault("name_hints", []):
            r["name_hints"].append(hint)
            self.by_hint.setdefault((hint.lower(), r.get("state")), []).append(rid)

    def process(self, it):
        """Attach one tagged headline. Returns (record id or None, how)."""
        if it["id"] in self.by_news or not project_shaped(it):
            return None, None
        inf = self.info(it)
        stage = fn.guess_status(it["title"])
        rid, how = self.match(it, inf)
        if not rid and inf["vendors_only"]:
            return None, None
        if not rid:
            codes = self.code_names(it["title"])
            figure = it.get("capacity_mw") or it.get("investment_usd_b")
            if inf["precision"] in ("city", "county") and (inf["companies"] or codes or figure):
                rid, how = self.create(it, inf, codes), "new"
            elif inf["companies"] and inf["precision"] in ("state", "source") and inf["state"]:
                company = sorted(inf["companies"], key=lambda n: fn.COMPANY_ORDER.get(n, 99))[0]
                u = self.umbrella(company, inf["state"])
                rid = self.resolve(u["id"]) if u else self.create_umbrella(company, inf["state"])
                how = "umbrella"
            else:
                return None, None
        self.attach(rid, it, stage)
        return rid, how


# ---------------------------------------------------------------------------
# Overrides
# ---------------------------------------------------------------------------
def apply_overrides(m, ops):
    applied, problems = 0, []
    for op in ops:
        kind, rec = op.get("op"), m.records
        try:
            if kind == "merge":
                if op["from"] in rec and op["into"] in rec and op["from"] != op["into"]:
                    m.merge(op["from"], op["into"])
                    applied += 1
                else:
                    problems.append(f"merge: unknown id in {op}")
            elif kind == "rename":
                rec[op["id"]]["name"] = op["name"]
                rec[op["id"]]["renamed"] = True
                applied += 1
            elif kind == "set_status":
                if op["status"] not in STATUSES:
                    problems.append(f"set_status: bad status {op['status']}")
                    continue
                rec[op["id"]]["status_override"] = {"status": op["status"], "date": op.get("date") or now_iso()[:10]}
                applied += 1
            elif kind == "set_location":
                r = rec[op["id"]]
                for k in ("lat", "lon", "location", "precision"):
                    if k in op:
                        r[k] = op[k]
                r["city"], r["county"] = place_fields(r["location"], r.get("precision"))
                if r.get("precision") in ("city", "county"):
                    r.pop("umbrella", None)
                applied += 1
            elif kind == "hide":
                rec[op["id"]]["hidden"] = True
                rec[op["id"]]["hidden_by_override"] = True
                applied += 1
            elif kind == "alias":
                r = rec[op["id"]]
                if op["alias"] not in r.setdefault("aliases", []):
                    r["aliases"].append(op["alias"])
                applied += 1
            elif kind == "split":
                src = rec[op["id"]]
                ids = set(op["headline_ids"])
                moving = [n for n in src["news"] if n["id"] in ids]
                if op["new_id"] not in rec:
                    skip = ("news", "hidden", "merged_into", "aliases", "curated", "timeline", "announced", "notes", "verified",
                            "imported", "renamed", "umbrella", "umbrella_company", "name_hints")
                    rec[op["new_id"]] = {k: v for k, v in src.items() if k not in skip and not k.startswith("curated_")}
                    # The new record's operators are the ones its own headlines name, else the source's.
                    named = [c for n in moving for c in fn.find_companies(n["title"])]
                    cos = sorted(set(named), key=lambda c: fn.COMPANY_ORDER.get(c, 99)) or list(src.get("companies", []))
                    rec[op["new_id"]].update({"id": op["new_id"], "name": src["name"] + " (split)", "news": [], "curated": False,
                                              "companies": cos, "company": ", ".join(cos)})
                rec[op["new_id"]]["news"].extend(moving)
                src["news"] = [n for n in src["news"] if n["id"] not in ids]
                for n in moving:
                    m.by_news[n["id"]] = op["new_id"]
                applied += 1
            else:
                problems.append(f"unknown op {kind}")
        except KeyError as e:
            problems.append(f"{kind}: missing {e} in {op}")
    m.reindex()
    return applied, problems


# ---------------------------------------------------------------------------
# Derived fields: replay the headlines in date order
# ---------------------------------------------------------------------------
def derive(r, resignal=True):
    """Rebuild status, history, events, figures and confidence from the record's headlines.
    With resignal (the default) every headline's stage signal is re-read with today's rules, so a
    rule fix in fetch_news.guess_status corrects old records too."""
    if resignal:
        for n in r["news"]:
            n["stage_signal"] = fn.guess_status(n["title"])
    news = sorted(r["news"], key=lambda n: (n["published"], n["id"]))
    history, events, status = [], [], None
    override = r.get("status_override")
    steps = [(n["published"], "news", n) for n in news]
    if override:
        steps.append((override["date"], "override", override))
    steps.sort(key=lambda s: s[0])
    for date, kind, x in steps:
        if kind == "override":
            if x["status"] != status:
                status = x["status"]
                history.append({"date": date, "status": status, "headline_id": None, "by": "override"})
            continue
        s, hid = x.get("stage_signal"), x["id"]
        if s == CANCELLED:
            if status != CANCELLED:
                status = CANCELLED
                history.append({"date": date, "status": status, "headline_id": hid})
                events.append({"date": date, "type": "Cancelled", "headline_id": hid})
        elif s in STAGE:
            if status is None:
                status = s
                history.append({"date": date, "status": s, "headline_id": hid})
            elif status == CANCELLED:
                if s in ("Under construction", "Operational"):
                    status = s
                    history.append({"date": date, "status": s, "headline_id": hid})
                    events.append({"date": date, "type": "Revived", "headline_id": hid})
            elif STAGE.get(s, 0) > STAGE.get(status, 0):
                status = s
                history.append({"date": date, "status": s, "headline_id": hid})
        elif s == "Expansion":
            if status is None:
                status = "Announced"
                history.append({"date": date, "status": status, "headline_id": hid})
            events.append({"date": date, "type": "Expansion", "headline_id": hid})
        if s != CANCELLED and APPROVAL_RE.search(x["title"]):
            events.append({"date": date, "type": "Approval", "headline_id": hid})
        if POWER_RE.search(x["title"]):
            events.append({"date": date, "type": "Power deal", "headline_id": hid})

    if r.get("curated"):
        # projects.json wins on status; headlines still add news and events.
        start = (r.get("announced") + "-01") if r.get("announced") else (news[0]["published"][:10] if news else r.get("imported"))
        status = r["curated_status"]
        history = [{"date": start, "status": status, "headline_id": None, "by": "curated"}]
        if override:
            status = override["status"]
            history.append({"date": override["date"], "status": status, "headline_id": None, "by": "override"})
    r["status"] = status or "Announced"
    r["status_history"] = history
    # One event of each type per day: several outlets reporting the same approval are one step.
    seen, r["events"] = set(), []
    for e in events:
        key = (e["type"], str(e["date"])[:10])
        if key not in seen:
            seen.add(key)
            r["events"].append(e)

    figs = [fn.extract_numbers(n["title"]) for n in news]
    mw = max((f.get("capacity_mw", 0) for f in figs), default=0)
    usd = max((f.get("investment_usd_b", 0) for f in figs), default=0)
    r["capacity_mw"] = r.get("curated_capacity_mw") or (mw if 0 < mw <= fn.MAX_PROJECT_MW else None)
    r["investment_usd_b"] = r.get("curated_investment_usd_b") or (usd or None)
    if news:
        r["first_seen"] = min(r.get("first_seen") or news[0]["published"], news[0]["published"]) if r.get("curated") else news[0]["published"]
        r["last_news"] = news[-1]["published"]
    else:
        r["last_news"] = None
        if r.get("curated") and not r.get("first_seen"):
            r["first_seen"] = (r["announced"] + "-01") if r.get("announced") else r.get("imported")
    r["sources_count"] = len({n.get("source") for n in news if n.get("source")})
    r["news"] = news

    if not r.get("curated"):
        # Operators only: a name that left the operator list (SoftBank is an investor) moves over.
        moved = [c for c in r.get("companies", []) if c not in fn.COMPANY_ORDER]
        if moved:
            r["investors"] = sorted(set(r.get("investors", [])) | {c for c in moved if c in dict(fn.INVESTORS)})
        r["companies"] = sorted((c for c in r.get("companies", []) if c in fn.COMPANY_ORDER), key=lambda n: fn.COMPANY_ORDER[n])
        r["company"] = ", ".join(r["companies"])
    company, local = bool(r.get("companies")), r.get("precision") in ("city", "county")
    figure = bool(r.get("capacity_mw") or r.get("investment_usd_b"))
    if r.get("umbrella"):
        r["confidence"] = "low"
    elif company and local and r["sources_count"] >= 2:
        r["confidence"] = "high"
    elif (company or figure) and local:
        r["confidence"] = "medium"
    else:
        r["confidence"] = "low"
    r.setdefault("hidden", False)
    for k in ("company", "notes", "verified", "name_hints") + ORG_FIELDS:
        r.setdefault(k, "" if k in ("company", "notes") else False if k == "verified" else [])
    return r


ORG_FIELDS = ("utilities", "investors", "builders", "suppliers")


def attach_orgs(records, items_by_id):
    """Add the organisations named in a record's headlines to the record: utilities, investors,
    builders and suppliers for every record, project name hints, and operators for a detected record
    that has none, so "Hermantown data center plan" gains Google when a later headline names it.
    Only headlines in this run are looked at; what earlier runs added is kept."""
    for r in records.values():
        news = [items_by_id[n["id"]] for n in r["news"] if n["id"] in items_by_id]
        for k in ORG_FIELDS:
            have = set(r.get(k, []))
            for it in news:
                have.update(it.get(k, []))
            r[k] = sorted(have)
        # A record with no operator yet takes the operators of its earliest headline that names one;
        # a record that has operators keeps them (a later "Meta and xAI" roundup does not add xAI).
        if not r.get("curated") and not r.get("umbrella") and not r.get("companies"):
            named = [it for it in sorted(news, key=lambda x: x["published"]) if it.get("companies")]
            if named:
                r["companies"] = list(named[0]["companies"])
        hints = list(r.get("name_hints", []))
        hints += [it["name_hint"] for it in news if it.get("name_hint") and it["name_hint"] not in hints]
        r["name_hints"] = list(dict.fromkeys(hints))


# ---------------------------------------------------------------------------
# One run
# ---------------------------------------------------------------------------
def update(items, gaz, registry_in=REGISTRY_FILE, registry_out=REGISTRY_FILE, log=print):
    """Attach new headlines, apply overrides, rebuild derived fields, save. Returns the records."""
    records = load(registry_in)
    before = len(records)
    import_curated(records)
    m = Matcher(records, gaz)
    counts = {}
    for it in sorted(items, key=lambda x: (x["published"], x["id"])):
        rid, how = m.process(it)
        if how:
            counts[how.split(" ")[0]] = counts.get(how.split(" ")[0], 0) + 1
    applied, problems = apply_overrides(m, load_overrides())
    for p in problems:
        log("  override problem: " + p)
    attach_orgs(records, {it["id"]: it for it in items})
    for r in records.values():
        derive(r)
    save(records, registry_out)
    log(f"Registry: {len(records)} records ({len(records) - before} new), attached {sum(counts.values())} headlines "
        f"{dict(sorted(counts.items()))}, {applied} overrides applied")
    return records


# ---------------------------------------------------------------------------
# Static project pages and the sitemap
# ---------------------------------------------------------------------------
BASE_PAGES = [("/", "hourly", "1.0"), ("/newsroom", "hourly", "0.9"), ("/radar", "daily", "0.9"),
              ("/companies", "daily", "0.8"), ("/learn", "monthly", "0.7"), ("/methodology", "monthly", "0.5")]
NAV = [("/", "Overview"), ("/newsroom", "Newsroom"), ("/radar", "Rack Radar"), ("/companies", "Companies"),
       ("/learn", "Learn"), ("/methodology", "Methodology")]
TONE = {"Announced": "--st-announced", "Planned": "--st-planned", "Under construction": "--st-construction",
        "Operational": "--st-operational", CANCELLED: "--st-cancelled"}


def page_mode(records):
    visible = [r for r in records.values() if not r.get("hidden")]
    return "state" if len(visible) > MAX_PAGES_PER_RECORD else "record"


def page_path(r, mode):
    return f"/projects/{r['id']}/" if mode == "record" else f"/projects/state-{(r.get('state') or 'us').lower()}/#{r['id']}"


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def fmt_date(s):
    d = parse(s) if s and len(s) > 7 else None
    if d:
        return d.strftime("%b %-d, %Y")
    if s and re.match(r"^\d{4}-\d{2}$", s):
        return datetime.strptime(s, "%Y-%m").strftime("%b %Y")
    return s or ""


def tile(lat, lon, z=9):
    """The OSM tile containing the point and the point's pixel offset inside it."""
    n = 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
    return z, int(x), int(y), round((x - int(x)) * 256), round((y - int(y)) * 256)


def orgs_html(r):
    """'Investors: Blackstone · Builders: Mortenson ...' for the organisations named in the record's news."""
    parts = [f"<b>{label}:</b> {esc(', '.join(r[k]))}" for k, label in
             (("investors", "Investors"), ("builders", "Builders"), ("suppliers", "Suppliers"), ("utilities", "Utilities"))
             if r.get(k)]
    return f'<p class="pp-orgs">{" · ".join(parts)}</p>' if parts else ""


def record_html(r):
    news = {n["id"]: n for n in r["news"]}
    steps = sorted([dict(h, kind="status") for h in r.get("status_history", [])] +
                   [dict(e, kind="event") for e in r.get("events", [])], key=lambda s: str(s.get("date")))
    def step(s):
        label = s["status"] if s["kind"] == "status" else s["type"]
        n = news.get(s.get("headline_id"))
        how = f' <a href="{esc(n["link"])}" rel="noopener">{esc(n["source"] or "source")}</a>' if n else \
            (" (curated)" if s.get("by") == "curated" else " (correction)" if s.get("by") == "override" else "")
        return f'<li><time>{esc(fmt_date(s.get("date")))}</time><span><b>{esc(label)}</b>{how}</span></li>'
    figures = [("Status", r["status"]), ("Capacity", f'{r["capacity_mw"]:,} MW' if r.get("capacity_mw") else "Not reported"),
               ("Investment", f'${r["investment_usd_b"]:g}B' if r.get("investment_usd_b") else "Not reported"),
               ("First seen", fmt_date(r.get("first_seen"))), ("Latest news", fmt_date(r.get("last_news"))),
               ("Confidence", r.get("confidence", ""))]
    thumb = ""
    if isinstance(r.get("lat"), (int, float)) and isinstance(r.get("lon"), (int, float)):
        z, x, y, px, py = tile(r["lat"], r["lon"], 9 if r.get("precision") in ("city", "county") else 6)
        thumb = (f'<div class="pp-map"><img class="rr-tiles" src="https://tile.openstreetmap.org/{z}/{x}/{y}.png" width="256" height="256" '
                 f'alt="Map around {esc(r["location"])}" loading="lazy"><span class="pp-pin" style="left:{px}px;top:{py}px"></span>'
                 f'<small>© <a href="https://www.openstreetmap.org/copyright" rel="noopener">OpenStreetMap</a> contributors</small></div>')
    items = "".join(f'<li><a href="{esc(n["link"])}" rel="noopener">{esc(n["title"])}</a><small>{esc(n["source"])} · '
                    f'{esc(fmt_date(n["published"]))}{" · " + esc(n["stage_signal"]) if n.get("stage_signal") else ""}</small></li>'
                    for n in sorted(r["news"], key=lambda n: n["published"], reverse=True))
    tone = TONE.get(r["status"], "--st-announced")
    return f"""
<article class="pp" id="{esc(r['id'])}" style="--tone:var({tone})">
  <span class="eyebrow">{"Curated project" if r.get("curated") else "Detected project"}</span>
  <h1>{esc(r['name'])}</h1>
  <p class="lede">{esc(r.get('company') or 'Company not named')} · {esc(r['location'].replace(', US', ''))}{" (approximate)" if r.get("precision") in ("state", "source") else ""}</p>
  <div class="pp-grid">
    <div>
      <div class="kv">{"".join(f'<div><span>{esc(k)}</span><b>{esc(v)}</b></div>' for k, v in figures)}</div>
      {f'<p>{esc(r["notes"])}</p>' if r.get("notes") else ""}
      {orgs_html(r)}
      <p><a class="btn sm primary" href="/radar#project={esc(r['id'])}">Open in Rack Radar</a></p>
    </div>
    {thumb}
  </div>
  <h2 class="sub-h">Status timeline</h2>
  <ol class="pp-steps">{"".join(step(s) for s in steps) or "<li>No status changes recorded yet.</li>"}</ol>
  <h2 class="sub-h">News about this project</h2>
  <ul class="pp-news">{items or "<li>No headlines attached yet.</li>"}</ul>
</article>"""


def page_shell(title, desc, canonical, body):
    nav = "".join(f'<a href="{u}">{t}</a>' for u, t in NAV)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>{esc(title)} · The Rack Report</title>
  <meta name="description" content="{esc(desc)}">
  <meta name="theme-color" content="#0c0c0d">
  <link rel="canonical" href="{SITE}{canonical}">
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="The Rack Report">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(desc)}">
  <meta property="og:url" content="{SITE}{canonical}">
  <meta property="og:image" content="{SITE}/assets/og.png">
  <link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap">
  <link rel="stylesheet" href="/assets/style.css?v=rr21">
</head>
<body class="static-page">
  <a class="skip" href="#main">Skip to content</a>
  <header class="static-top"><div class="page"><a class="brand" href="/" aria-label="The Rack Report home"><span>The <b>Rack</b> Report</span></a>
    <nav aria-label="Main">{nav}</nav></div></header>
  <main id="main" tabindex="-1"><div class="page">{body}</div></main>
  <footer class="static-foot"><div class="page"><p>Headlines link to the original publishers. Detected projects are built automatically from news and can be wrong; see the <a href="/methodology">Methodology</a>.</p></div></footer>
</body>
</html>
"""


def build_pages(records, out_dir=PAGES_DIR, sitemap=SITEMAP_FILE, log=print):
    """Write projects/<id>/index.html for every visible record (or one page per state when there
    are more than MAX_PAGES_PER_RECORD), remove pages for hidden records and rewrite the sitemap."""
    mode = page_mode(records)
    visible = sorted((r for r in records.values() if not r.get("hidden")), key=lambda r: r["id"])
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    pages = []
    if mode == "record":
        for r in visible:
            desc = f'{r["name"]}: {r["status"].lower()} data center project in {r["location"].replace(", US", "")}, with its status history and news.'
            path = f"/projects/{r['id']}/"
            (out_dir / r["id"]).mkdir(parents=True, exist_ok=True)
            (out_dir / r["id"] / "index.html").write_text(page_shell(r["name"], desc, path, record_html(r)), encoding="utf-8")
            pages.append((path, (r.get("last_news") or r.get("first_seen") or now_iso())[:10]))
    else:
        by_state = {}
        for r in visible:
            by_state.setdefault((r.get("state") or "us").lower(), []).append(r)
        for st, rs in sorted(by_state.items()):
            path = f"/projects/state-{st}/"
            body = "".join(record_html(r) for r in rs)
            (out_dir / f"state-{st}").mkdir(parents=True, exist_ok=True)
            (out_dir / f"state-{st}" / "index.html").write_text(
                page_shell(f"Data center projects in {st.upper()}", f"Every tracked data center project in {st.upper()}.", path, body), encoding="utf-8")
            pages.append((path, max((r.get("last_news") or "")[:10] for r in rs) or now_iso()[:10]))
    total = sum(p.stat().st_size for p in out_dir.rglob("*.html"))
    write_sitemap(pages, sitemap)
    log(f"Project pages: {len(pages)} ({mode} mode), {total / 1024:.0f} KB" + (" - OVER the 5 MB budget" if total > MAX_PAGES_BYTES else ""))
    return pages, total


def write_sitemap(pages, path=SITEMAP_FILE):
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    lastmods = dict(re.findall(r"<loc>([^<]+)</loc><lastmod>([^<]+)</lastmod>", old))
    rows = [f'  <url><loc>{SITE}{u}</loc><lastmod>{lastmods.get(SITE + u, now_iso()[:10])}</lastmod><changefreq>{f}</changefreq><priority>{p}</priority></url>'
            for u, f, p in BASE_PAGES]
    rows += [f'  <url><loc>{SITE}{u.split("#")[0]}</loc><lastmod>{d}</lastmod><changefreq>weekly</changefreq><priority>0.5</priority></url>'
             for u, d in pages]
    path.write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                    + "\n".join(rows) + "\n</urlset>\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# One-time backfill
# ---------------------------------------------------------------------------
def backfill(log=print):
    """Seed the registry from the whole archive in date order, then from the retired
    project_candidates.json for anything the archive misses."""
    gaz, geo = fn.load_gazetteer()
    items, seen = [], set()
    for path in sorted(fn.ARCHIVE_DIR.glob("*.json")):
        if not fn.MONTH_RE.match(path.stem):
            continue
        for it in fn.load_json(path, {}).get("items", []):
            if it.get("filtered") or it["id"] in seen:
                continue
            it = dict(it)
            if fn.tag_item(it, gaz, geo):
                it.setdefault("cluster_id", it["id"])
                items.append(it)
                seen.add(it["id"])
    cand_path = fn.DATA / "project_candidates.json"
    extra = 0
    for c in fn.load_json(cand_path, {}).get("projects", []):
        if c["id"] in seen:
            continue
        it = {"id": c["id"], "title": c["name"], "link": c["source_url"], "source": c.get("source", ""),
              "published": c["published"], "cluster_id": c.get("cluster_id", c["id"]), "_desc": ""}
        if fn.tag_item(it, gaz, geo):
            it.pop("_desc", None)
            items.append(it)
            seen.add(it["id"])
            extra += 1
    log(f"Backfill: {len(items)} headlines from the archive and {extra} more from project_candidates.json")
    return update(items, gaz, log=log)


SELFTEST = [("AWS announces North Carolina data center campus in Richmond County", 14),
            ("AWS breaks ground on Richmond County, North Carolina data center", 7),
            ("AWS opens Richmond County, North Carolina data center", 1)]


def selftest(log=lambda *_: None):
    """Replay three AWS headlines (announce, break ground, open) through tagging and three
    separate registry runs, without curated projects or overrides. Returns the records
    that took the headlines; a correct run gives one record moving Announced ->
    Under construction -> Operational with three news items."""
    import tempfile
    global PROJECTS_FILE, OVERRIDES_FILE
    saved = PROJECTS_FILE, OVERRIDES_FILE
    tmp = Path(tempfile.mkdtemp(prefix="rr-registry-"))
    try:
        (tmp / "projects.json").write_text('{"projects": []}')
        (tmp / "overrides.json").write_text('{"operations": []}')
        PROJECTS_FILE, OVERRIDES_FILE = tmp / "projects.json", tmp / "overrides.json"
        gaz, geo = fn.load_gazetteer()
        now = datetime.now(timezone.utc)
        for i, (title, days) in enumerate(SELFTEST, 1):
            it = {"id": f"selftest-{i}", "title": title, "link": f"https://example.com/{i}", "source": "Test Journal",
                  "published": (now - timedelta(days=days)).isoformat(timespec="seconds"), "_desc": ""}
            assert fn.tag_item(it, gaz, geo), title
            it.pop("_desc")
            it["cluster_id"] = it["id"]
            update([it], gaz, registry_in=tmp / "registry.json", registry_out=tmp / "registry.json", log=log)
        recs = [r for r in load(tmp / "registry.json").values() if r["news"]]
        return recs
    finally:
        PROJECTS_FILE, OVERRIDES_FILE = saved
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backfill", action="store_true", help="seed data/registry.json from the archive")
    ap.add_argument("--pages", action="store_true", help="rebuild projects/ pages and the sitemap from data/registry.json")
    ap.add_argument("--selftest", action="store_true", help="run the three-headline status machine test")
    args = ap.parse_args()
    if args.selftest:
        for r in selftest():
            print(r["id"], "|", r["status"], "|", len(r["news"]), "news")
            for h in r["status_history"]:
                print("   ", h["date"][:10], h["status"], "<-", h["headline_id"])
        return
    if args.backfill:
        records = backfill()
        build_pages(records)
    elif args.pages:
        build_pages(load())
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
