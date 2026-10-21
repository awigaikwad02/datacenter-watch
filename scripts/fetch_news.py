#!/usr/bin/env python3
"""
Data Center Watch: feed updater.

Pulls the Google News RSS searches and Google Alerts RSS feeds listed in
data/feeds.json, cleans and dedupes the headlines, tags each one with a
category, detects place names, and writes:

  data/news.json                the feed shown on index.html
  data/project_candidates.json  announced / under construction / opened
                                projects detected from headlines, shown on
                                the map next to the curated projects.json

The site covers the United States only: stories that are clearly about
another country are dropped, and every kept story is tagged with the U.S.
states it mentions.

Run locally:  python scripts/fetch_news.py
Re-tag the existing files without fetching:  python scripts/fetch_news.py --no-fetch
Test offline against a saved RSS file, writing somewhere else:
  python scripts/fetch_news.py --sample scripts/sample_feed.xml --out /tmp/rack-test
GitHub Actions runs it on a schedule (see .github/workflows/update.yml).
"""

import argparse
import calendar
import hashlib
import html
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote_plus

import feedparser
import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
FEEDS_FILE = DATA / "feeds.json"
NEWS_FILE = DATA / "news.json"
CAND_FILE = DATA / "project_candidates.json"
GAZ_FILE = Path(__file__).resolve().parent / "gazetteer.json"

NEWS_MAX_AGE_DAYS = 60
NEWS_MAX_ITEMS = 600
CAND_MAX_AGE_DAYS = 180
CAND_MAX_ITEMS = 400
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; DataCenterWatch/1.0; +https://github.com)"}
TIMEOUT = 25

# ---------------------------------------------------------------------------
# Classification rules. Order matters: the first rule that matches a headline
# becomes its primary category. Every matching rule is also kept as a tag.
# ---------------------------------------------------------------------------
CATEGORY_RULES = [
    ("Policy / Permits",
     r"\b(zoning|rezon\w*|city council|county council|council|commission(ers?)?|board of supervisors|supervisors|"
     r"moratorium|ordinance|permits?|permitting|lawsuit|sue[sd]?|residents?|neighbou?rs?|opposition|oppose[sd]?|"
     r"protest\w*|pushback|tax (break|incentive|abatement|exemption)s?|incentives?|regulat\w*|legislat\w*|"
     r"senate|governor|lawmakers?|approv\w*|reject\w*|denie[sd]|deny|vote[sd]?|hearing|referendum|noise|"
     r"environmental|water use|backlash|bans?|banned)\b"),
    ("Land Acquisition",
     r"(\b\d[\d,]*[- ]acres?\b|\bacres\b|\bparcels?\b|\bland (purchase|deal|sale|buy)\b|\b(buys?|bought|purchases?|"
     r"purchased|acquires?|acquired) (\w+ ){0,2}(land|site|property|acreage|farmland)\b|\bsite acquisition\b)"),
    ("Expansion",
     r"\b(expands?|expanding|expanded|expansion|adds|second phase|phase (2|ii|two)|"
     r"additional buildings?|more buildings)\b"),
    ("Construction",
     r"\b(break(s|ing)? ground|groundbreaking|ground-breaking|under construction|construction|"
     r"topping out|contractor|crews|build-?out|begins? building|starts? building)\b"),
    ("Operations",
     r"\b(opens|opened|officially open|now open|grand opening|goes live|went live|comes online|now online|"
     r"online|commissioned|energized|outages?|downtime|hiring|job fair|jobs fair|ribbon)\b"),
    ("New Announcement",
     r"\b(announc\w*|plans?|planned|planning|propos\w*|unveil\w*|to build|will build|eyes|eyeing|"
     r"selects?|chooses?|picks?|lands|secures?|launch\w*|new campus|campus|mega|project)\b"),
    ("Deals / Investment",
     r"\b(acqui\w*|merger|buys?|bought|purchase\w*|invest\w*|funding|raises?|raised|financing|loan|debt|"
     r"bonds?|lease[sd]?|leasing|joint venture|partnership|stake|ipo|valuation|billion|million|\$\s?\d)\b"),
    ("Power / Utility",
     r"\b(power|grid|utilit(y|ies)|electric\w*|energy|megawatts?|gigawatts?|\d+\s?[MG]W|nuclear|reactors?|"
     r"smrs?|natural gas|gas turbines?|turbines?|solar|wind|batter(y|ies)|transmission|substation|"
     r"demand|load|rates?|ratepayers?|blackout|cooling|water)\b"),
    ("AI Infrastructure",
     r"\b(ai|a\.i\.|artificial intelligence|gpus?|nvidia|hyperscal\w*|openai|microsoft|amazon|aws|google|"
     r"alphabet|meta|oracle|xai|anthropic|stargate|crusoe|coreweave|supercomputer|cloud)\b"),
]
COMPILED_RULES = [(name, re.compile(pat, re.I)) for name, pat in CATEGORY_RULES]

# Project detection: headline must be about a site and describe a stage.
PROJECT_WORDS = re.compile(r"\b(data\s?cent(er|re)s?|campus|hyperscale|facility|facilities)\b", re.I)
STATUS_RULES = [
    ("Under construction",
     re.compile(r"\b(break(s|ing)? ground|groundbreaking|ground-breaking|under construction|"
                r"construction (begins|starts|underway|begun|started|kicks off)|begins? construction|"
                r"starts? construction|topping out|crews)\b", re.I)),
    ("Operational",
     re.compile(r"\b(opens|opened|officially open|now open|grand opening|goes live|comes online|now online|"
                r"completes?|completed|completion|commissioned|energized|ribbon)\b", re.I)),
    ("Expansion",
     re.compile(r"\b(expands?|expanding|expanded|expansion|adds|second phase|phase (2|ii|two)|"
                r"additional buildings?)\b", re.I)),
    ("Announced",
     re.compile(r"\b(announc\w*|plans?|planned|planning|propos\w*|unveil\w*|to build|will build|eyes|eyeing|"
                r"selects?|chooses?|picks?|lands|secures?|approv\w*|acquires? (land|site)|"
                r"buys? (land|site|acres)|\d[\d,]* acres)\b", re.I)),
]

# Companies tracked across news and projects. Patterns are case sensitive
# whole words. A pattern can map to several companies (Stargate).
COMPANIES = [
    ("Google", r"Google|Alphabet"),
    ("Microsoft", r"Microsoft|Azure"),
    ("Meta", r"Meta|Facebook"),
    ("Amazon", r"Amazon|AWS"),
    ("Oracle", r"Oracle|OCI"),
    ("OpenAI", r"OpenAI|ChatGPT"),
    ("xAI", r"xAI"),
    ("Anthropic", r"Anthropic"),
    ("CoreWeave", r"CoreWeave"),
    ("Crusoe", r"Crusoe"),
    ("QTS", r"QTS"),
    ("Equinix", r"Equinix"),
    ("Digital Realty", r"Digital Realty"),
    ("Switch", r"Switch(?= (Inc|data cent|campus|Citadel))|Switch's"),
    ("CyrusOne", r"CyrusOne"),
    ("Compass Datacenters", r"Compass Data ?[Cc]enters"),
    ("Vantage", r"Vantage"),
    ("Aligned", r"Aligned Data Centers|Aligned(?= (Data|data))"),
    ("STACK", r"STACK Infrastructure|STACK"),
    ("EdgeCore", r"EdgeCore"),
    ("NTT", r"NTT"),
    ("Iron Mountain", r"Iron Mountain"),
    ("DataBank", r"DataBank"),
    ("Flexential", r"Flexential"),
    ("Applied Digital", r"Applied Digital"),
    ("Core Scientific", r"Core Scientific"),
    ("Fermi America", r"Fermi America|Fermi|Project Matador"),
    ("SoftBank", r"SoftBank"),
    ("Apple", r"Apple"),
    ("Related Digital", r"Related Digital"),
    ("Tallgrass", r"Tallgrass"),
]
ALIASES = [("Stargate", ["OpenAI", "Oracle", "SoftBank"])]
COMPANY_RULES = [(name, re.compile(r"(?<![\w-])(" + pat + r")(?![\w-])")) for name, pat in COMPANIES]
COMPANY_RULES += [(names, re.compile(r"(?<![\w-])" + a + r"(?![\w-])")) for a, names in ALIASES]
COMPANY_ORDER = {name: i for i, (name, _) in enumerate(COMPANIES)}

MW_RE = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s?(?:MW|megawatts?)\b", re.I)
GW_RE = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s?(?:GW|gigawatts?)\b", re.I)
MONEY_RE = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)\s?(billion|million|bn|b|m)\b", re.I)
# U.S.-only filter. A story is dropped when it names a non-U.S. place and no
# U.S. place, uses a foreign marker below, or comes from a foreign outlet.
FOREIGN_RE = re.compile(
    r"\b(data centres?|UK|U\.K\.|Britain|British|England|Europe|European|EU|India|Indian|China|Chinese|"
    r"Japan|Japanese|Korea|Korean|Australia|Australian|Canada|Canadian|Mexico|Mexican|Brazil|Brazilian|"
    r"Saudi|Emirati|Gulf|Africa|African|Asia|Asian|APAC|EMEA|LATAM|Indonesia|Malaysia|Malaysian|Thailand|"
    r"Vietnam|Philippines|Singapore|Ireland|Irish|Germany|German|France|French|Spain|Spanish|Italy|Italian|"
    r"Nordic|Norway|Sweden|Finland|Denmark|Dutch|Netherlands|Poland|Polish|Israel|Israeli|Pakistan|"
    r"Bangladesh|Sri Lanka|Nepal|Kenya|Nigeria|Egypt|Morocco|Turkey|Russia|Russian|Ukraine|Kazakhstan|"
    r"Chile|Colombia|Argentina|Peru|New Zealand|Taiwan|Taiwanese|Hong Kong|Scotland|Scottish|Welsh|Wales|"
    r"Türkiye|Turkiye|Ankara|Istanbul|Lagos|Nairobi|Seoul|Tokyo|Mumbai|Jakarta|Bangkok|Manila|Hanoi|"
    r"Qatar|Kuwait|Oman|Bahrain|UAE|Abu Dhabi|Dubai|Telangana|Maharashtra|Tamil Nadu|Karnataka|Gujarat|"
    r"Uttar Pradesh|Andhra|Odisha|Kerala|Johor|Ontario|Quebec|Alberta|British Columbia|Nova Scotia|"
    r"New Brunswick|Saskatchewan|Manitoba|Cape Breton|Melbourne|Rs|crore|lakh|"
    r"[£€₹¥])(?![\w])", re.I)
FOREIGN_SOURCES = {
    "cbc", "cbc.ca", "global news", "ctv news", "the globe and mail", "toronto star", "financial post",
    "data centre magazine", "data centre solutions", "data centre review", "datacentre solutions",
    "computer weekly", "uktn", "the times", "the telegraph", "the independent", "bbc", "sky news",
    "the irish times", "silicon republic", "rte", "times of india", "the economic times", "economic times",
    "the hindu", "business standard", "moneycontrol", "mint", "livemint", "hindustan times", "ndtv",
    "the financial express", "financial express", "the new indian express", "deccan herald", "business today",
    "the straits times", "south china morning post", "the edge malaysia", "the star", "bernama",
    "the sydney morning herald", "the australian", "abc (australia)", "itnews", "the japan times",
    "nikkei asia", "the korea herald", "the korea times", "gulf news", "khaleej times", "arab news",
    "the national", "zawya", "techcentral", "businesstech", "mybroadband", "techcabal", "lusa",
    "nz herald", "rnz", "stuff", "beinsure", "capacity media", "w.media", "dcd asia", "datacenter forum",
}
STATE_CODES = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO",
    "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA",
    "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT",
    "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM",
    "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def log(msg):
    print(msg, flush=True)


def clean_text(s):
    if not s:
        return ""
    s = html.unescape(TAG_RE.sub(" ", s))
    return WS_RE.sub(" ", s).strip()


def norm_key(title):
    return re.sub(r"[^a-z0-9]+", "", title.lower())


def make_id(title):
    return hashlib.sha1(norm_key(title).encode("utf-8")).hexdigest()[:16]


def parse_dt(entry):
    for key in ("published_parsed", "updated_parsed"):
        st = entry.get(key)
        if st:
            try:
                return datetime.fromtimestamp(calendar.timegm(st), tz=timezone.utc)
            except Exception:
                pass
    return None


def load_json(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            log(f"  warning: could not read {path.name}: {e}")
    return default


def google_news_url(query):
    return ("https://news.google.com/rss/search?q=" + quote_plus(query) +
            "&hl=en-US&gl=US&ceid=US:en")


def fetch_feed(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return feedparser.parse(r.content)
    except Exception as e:
        log(f"  warning: fetch failed for {url[:90]}... ({e})")
        return None


# ---------------------------------------------------------------------------
# Gazetteer / location detection
# ---------------------------------------------------------------------------
def load_gazetteer():
    gaz = {k: v for k, v in load_json(GAZ_FILE, {}).items() if not k.startswith("_")}
    names = sorted(gaz.keys(), key=len, reverse=True)
    patterns = []
    for n in names:
        if re.fullmatch(r"[A-Z]{2}", n):
            # Two-letter codes only count after a comma: "Abilene, TX"
            pat = re.compile(r"(?<=, )" + re.escape(n) + r"(?![A-Za-z])")
        else:
            pat = re.compile(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])")
        patterns.append((n, pat))
    return gaz, patterns


def find_locations(text, gaz, patterns):
    found = []
    work = text
    for name, pat in patterns:
        m = pat.search(work)
        if not m:
            continue
        lat, lon, level, display = gaz[name]
        found.append({"name": display, "lat": lat, "lon": lon, "level": level})
        # blank out the match so shorter names inside it do not re-match
        work = work[:m.start()] + (" " * (m.end() - m.start())) + work[m.end():]
    found.sort(key=lambda f: -f["level"])
    seen, out = set(), []
    for f in found:
        if f["name"] in seen:
            continue
        seen.add(f["name"])
        out.append(f)
    return out


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------
def country_of(loc):
    """Gazetteer display strings end in ', US' for U.S. places; anything else is foreign."""
    return "US" if loc["name"].endswith(", US") else loc["name"].split(",")[-1].strip()


def is_us(loc):
    return country_of(loc) == "US"


def find_companies(text):
    found = set()
    for names, rx in COMPANY_RULES:
        if rx.search(text):
            found.update([names] if isinstance(names, str) else names)
    return sorted(found, key=lambda n: COMPANY_ORDER.get(n, 99))


def state_of(loc):
    """'Abilene, Texas, US' -> 'TX'; 'Washington, D.C., US' -> 'DC'."""
    parts = [p.strip() for p in loc["name"].split(",")]
    if "D.C." in parts or "DC" in parts:
        return "DC"
    for p in reversed(parts[:-1]):
        if p in STATE_CODES:
            return STATE_CODES[p]
    return None


def us_filter(item, all_locs):
    """Return True when the story belongs on a U.S. site."""
    us_locs = [l for l in all_locs if is_us(l)]
    if us_locs:
        return True
    if any(not is_us(l) for l in all_locs):
        return False
    if item.get("source", "").strip().lower() in FOREIGN_SOURCES:
        return False
    if FOREIGN_RE.search(item["title"]):
        return False
    return True


def tag_item(item, gaz, patterns):
    """(Re)compute category, tags, locations and states. Returns False to drop."""
    text = item["title"] + " " + item.get("snippet", "")
    locs = find_locations(text, gaz, patterns)
    if not us_filter(item, locs):
        return False
    us_locs = [l for l in locs if is_us(l)]
    item["category"], item["tags"] = classify(item["title"])
    item["locations"] = us_locs[:3]
    states = [s for s in (state_of(l) for l in us_locs) if s]
    item["states"] = sorted(set(states))
    item["state"] = states[0] if states else None
    item["companies"] = find_companies(text)
    item.update(extract_numbers(item["title"]))
    return True


def classify(title):
    tags = [name for name, rx in COMPILED_RULES if rx.search(title)]
    primary = tags[0] if tags else "General"
    return primary, tags


def extract_numbers(title):
    out = {}
    m = GW_RE.search(title)
    if m:
        out["capacity_mw"] = round(float(m.group(1).replace(",", "")) * 1000)
    else:
        m = MW_RE.search(title)
        if m:
            out["capacity_mw"] = round(float(m.group(1).replace(",", "")))
    m = MONEY_RE.search(title)
    if m:
        val = float(m.group(1).replace(",", ""))
        unit = m.group(2).lower()
        out["investment_usd_b"] = round(val if unit in ("billion", "bn", "b") else val / 1000, 3)
    return out


def guess_status(title):
    for status, rx in STATUS_RULES:
        if rx.search(title):
            return status
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def parse_args():
    ap = argparse.ArgumentParser(description="Refresh data/news.json and data/project_candidates.json")
    ap.add_argument("--no-fetch", action="store_true", help="re-tag the stored items without fetching feeds")
    ap.add_argument("--sample", metavar="RSS_FILE", help="read this local RSS file instead of the network")
    ap.add_argument("--out", metavar="DIR", help="write the JSON files here instead of data/ (existing data/ files are read as the starting point)")
    return ap.parse_args()


def main():
    args = parse_args()
    no_fetch = args.no_fetch
    news_out = Path(args.out) / NEWS_FILE.name if args.out else NEWS_FILE
    cand_out = Path(args.out) / CAND_FILE.name if args.out else CAND_FILE
    if args.out:
        Path(args.out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    cfg = load_json(FEEDS_FILE, {})
    gaz, patterns = load_gazetteer()

    sources = []
    for f in cfg.get("google_news", []):
        if isinstance(f, dict) and f.get("query"):
            sources.append(("Google News: " + f.get("name", f["query"]), google_news_url(f["query"])))
    for url in cfg.get("google_alerts", []):
        if isinstance(url, str) and url.startswith("http"):
            sources.append(("Google Alerts", url))
    if no_fetch:
        sources = []
    if args.sample:
        sources = [("Sample: " + Path(args.sample).name, args.sample)]

    log(f"Fetching {len(sources)} feeds")
    fresh = {}
    for label, url in sources:
        parsed = feedparser.parse(Path(url).read_bytes()) if args.sample else fetch_feed(url)
        if not parsed:
            continue
        n = 0
        for e in parsed.entries:
            raw_title = clean_text(e.get("title", ""))
            if not raw_title:
                continue
            source = ""
            src = e.get("source")
            if isinstance(src, dict):
                source = clean_text(src.get("title", ""))
            # Google News titles end with " - Source"
            title = raw_title
            if " - " in raw_title:
                head, _, tail = raw_title.rpartition(" - ")
                if (source and tail.strip().lower() == source.lower()) or (not source and len(tail) < 40):
                    title = head.strip()
                    source = source or tail.strip()
            link = e.get("link", "")
            dt = parse_dt(e) or now
            if (now - dt).days > NEWS_MAX_AGE_DAYS:
                continue
            key = make_id(title)
            if key in fresh:
                continue
            snippet = clean_text(e.get("summary", ""))[:300] if label == "Google Alerts" else ""
            item = {
                "id": key,
                "title": title,
                "link": link,
                "source": source,
                "published": dt.isoformat(timespec="seconds"),
                "feed": label,
            }
            if snippet:
                item["snippet"] = snippet
            if not tag_item(item, gaz, patterns):
                continue
            fresh[key] = item
            n += 1
        log(f"  {label}: {n} items")

    # Merge with the existing news file so stories stay for NEWS_MAX_AGE_DAYS
    existing = load_json(NEWS_FILE, {}).get("items", [])
    merged = {it["id"]: it for it in existing if "id" in it}
    merged.update(fresh)
    cutoff = now - timedelta(days=NEWS_MAX_AGE_DAYS)
    # Re-tag stored stories too, so rule and gazetteer edits apply to old items
    items = [it for it in merged.values()
             if datetime.fromisoformat(it["published"]) >= cutoff and tag_item(it, gaz, patterns)]
    items.sort(key=lambda it: it["published"], reverse=True)
    items = items[:NEWS_MAX_ITEMS]

    news_out.write_text(json.dumps({
        "updated": now.isoformat(timespec="seconds"),
        "count": len(items),
        "new_this_run": len([k for k in fresh if k not in {it["id"] for it in existing}]),
        "items": items,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"Wrote {news_out}: {len(items)} items")

    # Project candidates: site + stage + place
    cand_existing = load_json(CAND_FILE, {}).get("projects", [])
    cands = {c["id"]: c for c in cand_existing if "id" in c and c.get("location", "").endswith(", US")}
    for c in cands.values():
        c["state"] = c.get("state") or state_of({"name": c["location"]})
        c["companies"] = find_companies(c["name"])
    for it in items:
        if it["id"] in cands:
            continue
        if not it["locations"] or not PROJECT_WORDS.search(it["title"]):
            continue
        status = guess_status(it["title"])
        if not status:
            continue
        loc = it["locations"][0]
        c = {
            "id": it["id"],
            "name": it["title"],
            "status": status,
            "location": loc["name"],
            "lat": loc["lat"],
            "lon": loc["lon"],
            "state": state_of(loc),
            "companies": it.get("companies", []),
            "precision": {3: "city", 2: "state", 1: "country"}.get(loc["level"], "unknown"),
            "source": it["source"],
            "source_url": it["link"],
            "published": it["published"],
            "detected": "auto",
        }
        for k in ("capacity_mw", "investment_usd_b"):
            if k in it:
                c[k] = it[k]
        cands[it["id"]] = c
    cutoff_c = now - timedelta(days=CAND_MAX_AGE_DAYS)
    cand_list = [c for c in cands.values()
                 if datetime.fromisoformat(c["published"]) >= cutoff_c]
    cand_list.sort(key=lambda c: c["published"], reverse=True)
    cand_list = cand_list[:CAND_MAX_ITEMS]
    cand_out.write_text(json.dumps({
        "updated": now.isoformat(timespec="seconds"),
        "count": len(cand_list),
        "projects": cand_list,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"Wrote {cand_out}: {len(cand_list)} candidates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
