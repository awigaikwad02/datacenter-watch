#!/usr/bin/env python3
"""
The Rack Report: feed updater.

Pulls the Google News RSS searches and Google Alerts RSS feeds listed in
data/feeds.json, cleans and dedupes the headlines, tags each one with a
category, detects place names, and writes:

  data/news.json                the feed shown on index.html
  data/registry.json            permanent project registry (scripts/registry.py):
                                curated projects plus projects detected from
                                headlines, never trimmed
  projects/<id>/index.html      one static page per visible project
  sitemap.xml                   the six site pages plus the project pages
  data/status.json              a short report of the run
  data/archive/YYYY-MM.json     permanent monthly archive; headlines are only
                                ever appended, never trimmed or deleted
  data/archive/index.json       months available and item counts

The site covers the United States only: stories that are clearly about
another country are dropped, and every kept story is tagged with the U.S.
states it mentions. Headlines must be about data centers (see is_on_topic),
sources in data/feeds.json "blocked_sources" are dropped, and related
headlines are grouped with a shared cluster_id.

Run locally:  python scripts/fetch_news.py
Re-tag the existing files without fetching:  python scripts/fetch_news.py --no-fetch
Test offline against a saved RSS file, writing somewhere else:
  python scripts/fetch_news.py --sample scripts/sample_feed.xml --out /tmp/rack-test
GitHub Actions runs it on a schedule (see .github/workflows/update.yml).
"""

import argparse
import calendar
import shutil
import time
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
STATUS_FILE = DATA / "status.json"
GAZ_FILE = Path(__file__).resolve().parent / "gazetteer.json"
ARCHIVE_DIR = DATA / "archive"
MONTH_RE = re.compile(r"^\d{4}-\d{2}$")

NEWS_MAX_AGE_DAYS = 90
NEWS_MAX_ITEMS = 3000
# Capacity figures above this are grid-wide totals ("474 GW of requests"), not one project.
MAX_PROJECT_MW = 20000
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; TheRackReport/1.0; +https://therackreport.org)"}
TIMEOUT = 25
FETCH_TRIES = 3          # retry 429 and 5xx responses with exponential backoff
CLUSTER_DAYS = 5         # related headlines must be this close in time
CLUSTER_STRONG = 0.5     # title-word Jaccard that clusters on its own
CLUSTER_WEAK = 0.3       # Jaccard that clusters with a shared city/county, or a shared company and state

# ---------------------------------------------------------------------------
# Classification rules. Order matters: the first rule that matches a headline
# becomes its primary category. Every matching rule is also kept as a tag.
# ---------------------------------------------------------------------------
# Cancellations and blocks are checked before everything else, so "Amazon drops
# data center plan" is never read as an announcement. CANCEL_NOT catches the
# opposite case: a vote against a moratorium or ban is not a blocked project.
CANCEL_PAT = (
    r"\b(drops|dropped|withdraw|withdraws|withdrew|withdrawn|scraps|scrapped|cancels|cancell?ed|abandons|abandoned|"
    r"(?:pulls|pulled) (?:out|back|the plug|plans?|its|application|proposal|request)|rejects|rejected|"
    r"denies|denied|blocks|blocked|halts|halted|pauses|paused|votes? down|voted down|votes? against|"
    r"voted against|court rules against|rules against|(?:puts?|putting|placed?) a pause|"
    r"moratorium (?:passed|passes|approved|adopted|enacted|extended|imposed)|"
    r"(?:pass|passes|passed|approve|approves|approved|adopts|adopted|enacts|enacted|extends|extended|extending|"
    r"expands|expanded|imposes|imposed|signs|signed|finalizes|finalized|starts|started) "
    r"(?:a |an |the )?(?:[\w$-]+ ){0,4}(?:moratoriums?|pause))\b")
CANCEL_RE = re.compile(CANCEL_PAT, re.I)
# Not a cancellation: proposals and calls for one, or a vote against a restriction rather than a project.
CANCEL_HEDGE = re.compile(
    r"\b(calls? for|called for|considers?|considering|weighs?|weighing|to debate|debates?|would|could|should|"
    r"to vote|vote on whether|set to|seeks?|urges?|pushes? for|proposal to|proposes?|wants?|won['’]t)\b", re.I)
CANCEL_NOT = re.compile(
    r"\b(?:votes? down|voted down|rejects?|rejected|denies|denied|blocks?|blocked|drops?|dropped|withdraws?|withdrew|"
    r"withdrawn|halts?|halted|pauses?|paused|votes? against|voted against|scraps?|scrapped|cancels?|cancell?ed)"
    r" (?:[\w$’'.,-]+ ){0,6}?(?:moratorium|ban|freeze|pause|restrictions?|ordinance|regulations?|rules|guardrails|"
    r"limits|lawsuit|suit|challenge|appeal|petition|referendum|opposition|tax|bill|plan to|plan that|meeting|"
    r"hearing|session|vote)\b|\b(?:blocks?|blocked) \w+ from\b|\b(?:rejects?|rejected) \$\d|"
    r"\b(?:shares|stocks?|prices?|demand|revenue|profits?) (?:drops?|dropped)\b", re.I)
CANCELLED = "Cancelled / Blocked"


def is_cancelled(title):
    return bool(CANCEL_RE.search(title)) and not CANCEL_HEDGE.search(title) and not CANCEL_NOT.search(title)


# Checked in this order after Cancelled / Blocked; the first match wins. Policy / Permits is
# last and needs a governance phrase, so a vote or a county name alone does not make a story policy.
CATEGORY_RULES = [
    ("New Announcement",
     r"\b(announc\w*|plans?|planned|propos\w*|unveil\w*|to build|will build|eyes|eyeing|"
     r"selects?|chooses?|picks?|lands|secures?|launch\w*|new campus|mega)\b"),
    ("Construction",
     r"\b(break(s|ing)? ground|groundbreaking|ground-breaking|under construction|construction|"
     r"topping out|contractor|crews|build-?out|begins? building|starts? building)\b"),
    ("Expansion",
     r"\b(expands?|expanding|expanded|expansion|adds|second phase|phase (2|ii|two)|"
     r"additional buildings?|more buildings)\b"),
    ("Land Acquisition",
     r"(\b\d[\d,]*[- ]acres?\b|\bacres\b|\bparcels?\b|\bland (purchase|deal|sale|buy)\b|\b(buys?|bought|purchases?|"
     r"purchased|acquires?|acquired) (\w+ ){0,2}(land|site|property|acreage|farmland)\b|\bsite acquisition\b)"),
    ("Operations",
     r"\b(opens|opened|officially open|now open|grand opening|goes live|went live|comes online|now online|"
     r"online|commissioned|energized|outages?|downtime|hiring|job fair|jobs fair|ribbon)\b"),
    ("Deals / Investment",
     r"\b(acqui\w*|merger|buys?|bought|purchase\w*|invest\w*|funding|raises?|raised|financing|financed|loan|debt|"
     r"bonds?|reits?|lease[sd]?|leasing|joint venture|partnership|stake|ipo|valuation|billion|million|\$\s?\d)\b"),
    ("Power / Utility",
     r"\b(power|grid|utilit(y|ies)|utility bills?|electric\w*|electricity rates?|energy|megawatts?|gigawatts?|\d+\s?[MG]W|"
     r"nuclear|reactors?|smrs?|natural gas|gas plants?|gas-fired|power plants?|gas turbines?|turbines?|solar|wind|"
     r"batter(y|ies)|transmission|substations?|demand|load|rates?|ratepayers?|blackout|cooling|water)\b"),
    ("AI Infrastructure",
     r"\b(ai|a\.i\.|artificial intelligence|gpus?|nvidia|compute|computing|ai factor(y|ies)|supercomputers?|"
     r"hyperscal\w*|openai|microsoft|amazon|aws|google|alphabet|meta|oracle|xai|anthropic|stargate|crusoe|coreweave|cloud)\b"),
    ("Policy / Permits",
     r"\b(zoning|rezon(e|es|ed|ing)|moratoriums?|ordinances?|permits?|permitting|planning (commission|board)|"
     r"board of supervisors|city council|county commission(ers?)?|public hearings?|lawsuits?|referendums?|"
     r"tax (breaks?|incentives?)|abatements?|opposition|residents? oppose[sd]?|pushback|"
     # Also governance, though not a vote or a county name on its own:
     r"bans?|banned|banning|pauses?|regulat\w*|restrictions?|crackdown|lawmakers?|legislat\w*|legislature|"
     r"senate|governor|ballots?|elections?|midterms?|voters|town hall|council|commissioners?|ndas?|"
     r"(public|community) (input|forum|meeting)s?|transparency)\b"),
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
    ("Microsoft", r"Microsoft|Azure|Fairwater"),
    ("Meta", r"Meta|Facebook|Hyperion|Prometheus"),
    ("Amazon", r"Amazon Web Services|Amazon|AWS|Project Rainier"),
    ("Oracle", r"Oracle|OCI"),
    ("OpenAI", r"OpenAI|ChatGPT"),
    ("xAI", r"xAI|Colossus"),
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
    ("STACK", r"STACK Infrastructure|STACK|Stack(?= (Infrastructure|data cent))"),
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
    # Developers
    ("Tract", r"Tract(?=('s| (Inc|Capital|data|Data|plans|Plans|buys|Buys|acquires|Acquires|proposes|Proposes|files|Files|campus|Campus|park|Park)\b))"),
    ("Hillwood", r"Hillwood"),
    ("PowerHouse", r"PowerHouse Data Centers|PowerHouse"),
    ("Sabey", r"Sabey Data Centers|Sabey"),
    ("T5", r"T5 Data Centers|T5"),
    ("Stream", r"Stream Data Centers"),
    ("Prime Data Centers", r"Prime Data Centers"),
    ("Skybox", r"Skybox Datacenters|Skybox Data Centers|Skybox"),
    ("Novva", r"Novva Data Centers|Novva"),
]
ALIASES = [("Stargate", ["OpenAI", "Oracle", "SoftBank"])]
COMPANY_RULES = [(name, re.compile(r"(?<![\w-])(" + pat + r")(?![\w-])")) for name, pat in COMPANIES]
COMPANY_RULES += [(names, re.compile(r"(?<![\w-])" + a + r"(?![\w-])")) for a, names in ALIASES]
COMPANY_ORDER = {name: i for i, (name, _) in enumerate(COMPANIES)}

# Utilities and grid operators, written to a separate "utilities" field.
UTILITIES = [
    ("Entergy", r"Entergy"),
    ("Dominion Energy", r"Dominion Energy|Dominion"),
    ("Georgia Power", r"Georgia Power"),
    ("Duke Energy", r"Duke Energy|Duke's"),
    ("AEP", r"AEP|American Electric Power"),
    ("Xcel Energy", r"Xcel Energy|Xcel"),
    ("Oncor", r"Oncor"),
    ("PG&E", r"PG&E|Pacific Gas and Electric"),
    ("APS", r"APS|Arizona Public Service"),
    ("SRP", r"SRP|Salt River Project"),
    ("Ameren", r"Ameren"),
    ("Evergy", r"Evergy"),
    ("TVA", r"TVA|Tennessee Valley Authority"),
    ("PJM", r"PJM"),
    ("ERCOT", r"ERCOT"),
    ("MISO", r"MISO"),
]
UTILITY_RULES = [(name, re.compile(r"(?<![\w-])(" + pat + r")(?![\w-])")) for name, pat in UTILITIES]

# A headline is on topic when it names data centers, or a tracked company together with a site word.
ON_TOPIC_RE = re.compile(r"\b(data[\s-]?cent(er|re)s?|datacent(er|re)s?|hyperscal\w*|colocation|ai factor(y|ies)|supercomputers?|server farms?|data halls?|computing (site|campus|facility|facilities))\b", re.I)
SITE_RE = re.compile(r"\b(campus(es)?|facilit(y|ies)|sites?|megawatts?|gigawatts?|\d[\d,.]*\s?[MG]W)\b", re.I)


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
    "bbc news", "the guardian", "guardian", "telegraph", "irish times", "abc australia", "abc news (australia)",
    "abc news australia", "cbc news", "globe and mail", "the economic times", "the times of india", "straits times",
    "scmp", "south china morning post",
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


CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u2028\u2029]")
INVISIBLE_RE = re.compile(r"[\u200b-\u200f\ufeff]")


def clean_text(s):
    """Plain text from feed markup: tags, entities and control or invisible characters removed."""
    if not s:
        return ""
    s = html.unescape(TAG_RE.sub(" ", s))
    return WS_RE.sub(" ", CONTROL_RE.sub(" ", INVISIBLE_RE.sub("", s))).strip()


def safe_link(url):
    """Only plain http(s) links are kept; javascript:, data: and anything else is dropped."""
    url = INVISIBLE_RE.sub("", CONTROL_RE.sub("", (url or "").strip()))
    return url if re.match(r"^https?://[^\s]+$", url, re.I) else ""


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
    """Fetch one feed, retrying 429 and 5xx responses (and network errors) with exponential backoff."""
    for attempt in range(1, FETCH_TRIES + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(f"HTTP {r.status_code}", response=r)
            r.raise_for_status()
            return feedparser.parse(r.content)
        except requests.RequestException as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            retryable = status is None or status == 429 or status >= 500
            if attempt < FETCH_TRIES and retryable:
                wait = 2 ** attempt
                log(f"  retry {attempt}/{FETCH_TRIES - 1} in {wait}s for {url[:70]}... ({e})")
                time.sleep(wait)
                continue
            log(f"  warning: fetch failed for {url[:90]}... ({e})")
            return None


# ---------------------------------------------------------------------------
# Gazetteer / location detection
# ---------------------------------------------------------------------------
class Geo:
    """Everything location and source handling needs, loaded once per run."""

    def __init__(self, patterns, areas, source_states, blocked):
        self.patterns = patterns            # [(name, regex)] for cities, states, countries
        self.areas = areas                  # "Mason County" -> [candidates]
        self.source_states = source_states  # outlet name -> two-letter state
        self.blocked = blocked              # outlet names (lowercase) that are dropped


# "Mason County", "St. Louis County", "Van Buren Township", "Richland Parish"
AREA_RE = re.compile(r"((?:(?:St\.|Saint|[A-Z][a-zA-Z'’-]+) )+)(County|Parish|Township)\b")
PRECISION_RANK = {"city": 4, "county": 3, "state": 2, "source": 1}


def entry_candidates(value):
    """A gazetteer value is one [lat, lon, level, display] entry or a list of them."""
    return value if value and isinstance(value[0], list) else [value]


def load_gazetteer():
    raw = {k: v for k, v in load_json(GAZ_FILE, {}).items() if not k.startswith("_")}
    areas, gaz = {}, {}
    for k, v in raw.items():
        if re.search(r" (County|Parish|Township)$", k):
            areas[k] = entry_candidates(v)
        else:
            gaz[k] = entry_candidates(v)[0]
    patterns = []
    for n in sorted(gaz.keys(), key=len, reverse=True):
        if re.fullmatch(r"[A-Z]{2}", n):
            # Two-letter codes only count after a comma: "Abilene, TX"
            pat = re.compile(r"(?<=, )" + re.escape(n) + r"(?![A-Za-z])")
        else:
            pat = re.compile(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])")
        patterns.append((n, pat))
    cfg = load_json(FEEDS_FILE, {})
    source_states = {k: v for k, v in cfg.get("source_states", {}).items() if not k.startswith("_")}
    blocked = {s.strip().lower() for s in cfg.get("blocked_sources", []) if isinstance(s, str) and not s.startswith("#")}
    return gaz, Geo(patterns, areas, source_states, blocked)


def loc_from(entry, precision):
    lat, lon, level, display = entry[:4]
    country = entry[4] if len(entry) > 4 else ("US" if display.endswith(", US") else display.split(",")[-1].strip())
    return {"name": display, "lat": lat, "lon": lon, "level": level, "precision": precision, "country": country}


def find_locations(text, gaz, geo, context_states=()):
    """Places named in the text, most precise first. Ambiguous county names are
    resolved with the states found elsewhere in the text or the outlet's state."""
    found = []
    work = text
    # A city name inside "Richmond County" or "Van Buren Township" is not that city:
    # blank the matched county/parish/township names before looking for cities.
    for m in AREA_RE.finditer(text):
        words, kind = m.group(1).split(), m.group(2)
        for k in range(len(words), 0, -1):
            key = " ".join(words[-k:]) + " " + kind
            if key in geo.areas:
                start = m.end() - len(key)
                work = work[:start] + " " * len(key) + work[m.end():]
                break
    for name, pat in geo.patterns:
        m = pat.search(work)
        if not m:
            continue
        entry = gaz[name]
        found.append(loc_from(entry, "city" if entry[2] >= 3 else "state" if entry[2] == 2 else "country"))
        # blank out the match so shorter names inside it do not re-match
        work = work[:m.start()] + (" " * (m.end() - m.start())) + work[m.end():]
    known_states = {state_of(f) for f in found} | set(context_states)
    for m in AREA_RE.finditer(text):
        words, kind = m.group(1).split(), m.group(2)
        for k in range(len(words), 0, -1):  # "Proposed Mason County" -> "Mason County"
            key = " ".join(words[-k:]) + " " + kind
            if key in geo.areas:
                cands = geo.areas[key]
                pick = cands[0] if len(cands) == 1 else next((c for c in cands if state_of({"name": c[3]}) in known_states), None)
                if pick:
                    found.append(loc_from(pick, "city" if kind == "Township" else "county"))
                break
    found.sort(key=lambda f: (-PRECISION_RANK.get(f["precision"], 0), -f["level"]))
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
    """The gazetteer's country code; older entries fall back to the display string."""
    return loc.get("country") or ("US" if loc["name"].endswith(", US") else loc["name"].split(",")[-1].strip())


def is_us(loc):
    return country_of(loc) == "US"


def find_companies(text):
    found = set()
    for names, rx in COMPANY_RULES:
        if rx.search(text):
            found.update([names] if isinstance(names, str) else names)
    return sorted(found, key=lambda n: COMPANY_ORDER.get(n, 99))


def find_utilities(text):
    return [name for name, rx in UTILITY_RULES if rx.search(text)]


def is_on_topic(text, companies):
    return bool(ON_TOPIC_RE.search(text) or (companies and SITE_RE.search(text)))


def state_of(loc):
    """'Abilene, Texas, US' -> 'TX'; 'Washington, D.C., US' -> 'DC'."""
    parts = [p.strip() for p in loc["name"].split(",")]
    if "D.C." in parts or "DC" in parts:
        return "DC"
    for p in reversed(parts[:-1]):
        if p in STATE_CODES:
            return STATE_CODES[p]
    return None


def us_filter(item, all_locs, title_locs=()):
    """Return True when the story belongs on a U.S. site. A non-U.S. outlet needs
    a U.S. place or state in the title itself, not just in the description."""
    if item.get("source", "").strip().lower() in FOREIGN_SOURCES:
        return any(is_us(l) for l in title_locs)
    us_locs = [l for l in all_locs if is_us(l)]
    if us_locs:
        return True
    if any(not is_us(l) for l in all_locs):
        return False
    if FOREIGN_RE.search(item["title"]):
        return False
    return True


def tag_item(item, gaz, geo):
    """(Re)compute topic, places, companies and figures. Returns False to drop the headline."""
    if item.get("source", "").strip().lower() in geo.blocked:
        return False
    text = item["title"] + " " + item.get("snippet", "") + " " + item.get("_desc", "")
    companies = find_companies(text)
    if not is_on_topic(text, companies):
        return False
    source_state = geo.source_states.get(item.get("source", ""))
    locs = find_locations(text, gaz, geo, [source_state] if source_state else ())
    title_locs = find_locations(item["title"], gaz, geo) if item.get("source", "").strip().lower() in FOREIGN_SOURCES else ()
    if not us_filter(item, locs, title_locs):
        return False
    us_locs = [l for l in locs if is_us(l)]
    if not us_locs and source_state:
        # A local outlet with no place in the headline: use its home state, flagged as such
        name = next((n for n, c in STATE_CODES.items() if c == source_state), None)
        if name in gaz:
            us_locs = [loc_from(gaz[name], "source")]
    item["category"], item["tags"] = classify(item["title"])
    item["locations"] = us_locs[:3]
    states = [s for s in (state_of(l) for l in us_locs) if s]
    item["states"] = sorted(set(states))
    item["state"] = states[0] if states else None
    item["county"] = next((l["name"] for l in us_locs if l["precision"] == "county"), None)
    item["location_precision"] = us_locs[0]["precision"] if us_locs else None
    item["companies"] = companies
    item["utilities"] = find_utilities(text)
    item.pop("capacity_mw", None)
    item.pop("investment_usd_b", None)
    item.update(extract_numbers(item["title"]))
    return True


# ---------------------------------------------------------------------------
# Clustering: one story told by several outlets
# ---------------------------------------------------------------------------
STOP = set("""a an and the of in on at to for by with from as is are be was were will has have had it its this that
these those new data center centers centre centres datacenter datacenters plan plans says say said could would
after over into about amid more than up out not no but or if he she they we you their our his her who what why how
county city state township parish us u.s""".split())


def title_words(title, source=""):
    """Title tokens without stopwords or the outlet's own name ("... - Reuters")."""
    drop = set(re.findall(r"[a-z0-9]+", source.lower()))
    return {w for w in re.findall(r"[a-z0-9$][a-z0-9$'.-]*", title.lower()) if len(w) > 2 and w not in STOP and w not in drop}


def jaccard(a, b):
    return len(a & b) / len(a | b) if a and b else 0.0


def cluster_items(items):
    """Set cluster_id and cluster_title on every item. Two headlines published within
    CLUSTER_DAYS join when their title-word Jaccard is >= CLUSTER_STRONG, or >= CLUSTER_WEAK
    and they share a city or county, or >= CLUSTER_WEAK and they share a company and a
    state. Union-find lets clusters chain through intermediate headlines."""
    parent = {it["id"]: it["id"] for it in items}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def places(it):
        return {l["name"] for l in it.get("locations", []) if l.get("precision") in ("city", "county")}

    rows = sorted(({"id": it["id"], "t": datetime.fromisoformat(it["published"]),
                    "w": title_words(it["title"], it.get("source", "")), "p": places(it),
                    "c": set(it.get("companies", [])), "s": set(it.get("states", []))} for it in items),
                  key=lambda r: r["t"])
    # Each root carries its cluster's states and places: two clusters that both name
    # places but none in common never merge, so a placeless headline cannot bridge them.
    geo = {r["id"]: (set(r["s"]), set(r["p"])) for r in rows}

    def conflict(ra, rb):
        (sa, pa), (sb, pb) = geo[ra], geo[rb]
        return bool((sa and sb and not sa & sb) or (pa and pb and not pa & pb))

    window = timedelta(days=CLUSTER_DAYS)
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if b["t"] - a["t"] > window:
                break
            j = jaccard(a["w"], b["w"])
            if j < CLUSTER_WEAK:
                continue
            if j >= CLUSTER_STRONG or (a["p"] & b["p"]) or ((a["c"] & b["c"]) and (a["s"] & b["s"])):
                ra, rb = find(a["id"]), find(b["id"])
                if ra != rb and not conflict(ra, rb):
                    parent[rb] = ra
                    geo[ra] = (geo[ra][0] | geo[rb][0], geo[ra][1] | geo[rb][1])
    groups = {}
    for it in sorted(items, key=lambda x: x["published"]):
        groups.setdefault(find(it["id"]), []).append(it)
    for members in groups.values():
        # Named after the earliest headline so the id stays stable as stories join;
        # shown with the headline that has the most precise place, else the earliest.
        best = max(members, key=lambda m: PRECISION_RANK.get(m.get("location_precision"), 0))
        for it in members:
            it["cluster_id"] = members[0]["id"]
            it["cluster_title"] = best["title"]
    return len(groups)


def classify(title):
    tags = [name for name, rx in COMPILED_RULES if rx.search(title)]
    if is_cancelled(title):
        tags.insert(0, CANCELLED)
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
    if out.get("capacity_mw", 0) > MAX_PROJECT_MW:
        del out["capacity_mw"]
    return out


def guess_status(title):
    if is_cancelled(title):
        return CANCELLED
    for status, rx in STATUS_RULES:
        if rx.search(title):
            return status
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Permanent archive
# ---------------------------------------------------------------------------
def archive_items(new_items, archive_dir):
    """Append headlines to data/archive/YYYY-MM.json by published month.

    Entries already in a month file are left exactly as they are; nothing is
    ever trimmed or deleted. Returns the number of headlines added.
    """
    archive_dir.mkdir(parents=True, exist_ok=True)
    by_month = {}
    for it in new_items:
        month = it.get("published", "")[:7]
        if MONTH_RE.match(month):
            by_month.setdefault(month, []).append(it)
    added = 0
    for month, its in sorted(by_month.items()):
        path = archive_dir / (month + ".json")
        current = load_json(path, {}).get("items", [])
        known = {x["id"] for x in current}
        fresh = []
        for it in its:
            if it["id"] not in known:
                known.add(it["id"])
                fresh.append(it)
        if not fresh:
            continue
        items = current + fresh
        items.sort(key=lambda x: x["published"], reverse=True)
        path.write_text(json.dumps({"month": month, "count": len(items), "items": items},
                                   ensure_ascii=False, indent=1), encoding="utf-8")
        added += len(fresh)
    write_archive_index(archive_dir)
    return added


def write_archive_index(archive_dir):
    months = []
    for path in sorted(archive_dir.glob("*.json"), reverse=True):
        if not MONTH_RE.match(path.stem):
            continue
        items = load_json(path, {}).get("items", [])
        if not items:
            continue
        months.append({
            "month": path.stem, "count": len(items), "file": "data/archive/" + path.name,
            "earliest": min(x["published"] for x in items), "latest": max(x["published"] for x in items),
        })
    index = {
        "total": sum(m["count"] for m in months),
        "earliest": min((m["earliest"] for m in months), default=None),
        "latest": max((m["latest"] for m in months), default=None),
        "months": months,
    }
    path = archive_dir / "index.json"
    old = load_json(path, {})
    old.pop("updated", None)
    if old == index:
        return  # nothing changed; keep the file (and git) quiet
    path.write_text(json.dumps(dict({"updated": datetime.now(timezone.utc).isoformat(timespec="seconds")}, **index),
                               ensure_ascii=False, indent=1), encoding="utf-8")


def parse_args():
    ap = argparse.ArgumentParser(description="Refresh data/news.json, data/registry.json and the project pages")
    ap.add_argument("--no-fetch", action="store_true", help="re-tag the stored items without fetching feeds")
    ap.add_argument("--sample", metavar="RSS_FILE", help="read this local RSS file instead of the network")
    ap.add_argument("--out", metavar="DIR", help="write the JSON files here instead of data/ (existing data/ files are read as the starting point)")
    return ap.parse_args()


def main():
    args = parse_args()
    no_fetch = args.no_fetch
    news_out = Path(args.out) / NEWS_FILE.name if args.out else NEWS_FILE
    status_out = Path(args.out) / STATUS_FILE.name if args.out else STATUS_FILE
    archive_out = Path(args.out) / "archive" if args.out else ARCHIVE_DIR
    if args.out:
        Path(args.out).mkdir(parents=True, exist_ok=True)
        # Test runs start from a copy of the real archive and never touch it.
        if ARCHIVE_DIR.exists():
            shutil.copytree(ARCHIVE_DIR, archive_out, dirs_exist_ok=True)
    now = datetime.now(timezone.utc)
    cfg = load_json(FEEDS_FILE, {})
    gaz, geo = load_gazetteer()

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
    raw_total = 0
    feeds_ok = 0
    for label, url in sources:
        parsed = feedparser.parse(Path(url).read_bytes()) if args.sample else fetch_feed(url)
        if not parsed:
            continue
        raw_total += len(parsed.entries)
        feeds_ok += bool(parsed.entries)
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
            link = safe_link(e.get("link", ""))
            if not link:
                continue
            dt = parse_dt(e) or now
            if (now - dt).days > NEWS_MAX_AGE_DAYS:
                continue
            key = make_id(title)
            if key in fresh:
                continue
            # Google News descriptions repeat the title and outlet; Alerts carry a real snippet.
            desc = clean_text(e.get("summary", "") or e.get("description", ""))
            snippet = desc[:300] if desc and not desc.startswith(title[:40]) else ""
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
            item["_desc"] = desc  # scanned for places and companies, never stored
            ok = tag_item(item, gaz, geo)
            item.pop("_desc", None)
            if not ok:
                continue
            fresh[key] = item
            n += 1
        log(f"  {label}: {n} items")
    if sources and raw_total == 0:
        log("ERROR: every feed returned zero items; leaving the data files unchanged")
        return 1

    # Merge with the existing news file so stories stay for NEWS_MAX_AGE_DAYS
    existing = load_json(NEWS_FILE, {}).get("items", [])
    merged = {it["id"]: it for it in existing if "id" in it}
    cutoff = now - timedelta(days=NEWS_MAX_AGE_DAYS)
    # Refill from the archive, so stories trimmed by an older, smaller limit come back
    for path in sorted(archive_out.glob("*.json")):
        if MONTH_RE.match(path.stem) and path.stem >= cutoff.strftime("%Y-%m"):
            for it in load_json(path, {}).get("items", []):
                if it["id"] not in merged and datetime.fromisoformat(it["published"]) >= cutoff:
                    merged[it["id"]] = dict(it)
    merged.update(fresh)
    # Re-tag stored stories too, so rule and gazetteer edits apply to old items
    kept = [it for it in merged.values() if tag_item(it, gaz, geo)]
    kept.sort(key=lambda it: it["published"], reverse=True)
    clusters = cluster_items(kept)
    log(f"Clusters: {len(kept)} headlines in {clusters} stories")

    # Every kept headline goes into the permanent archive before the recent file is trimmed
    added = archive_items(kept, archive_out)
    log(f"Archive: {added} new headlines added under {archive_out}")

    items = [it for it in kept if datetime.fromisoformat(it["published"]) >= cutoff][:NEWS_MAX_ITEMS]

    known = {it["id"] for it in existing}
    new_this_run = len([k for k in fresh if k not in known])
    news_out.write_text(json.dumps({
        "updated": now.isoformat(timespec="seconds"),
        "count": len(items),
        "new_this_run": new_this_run,
        "items": items,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"Wrote {news_out}: {len(items)} items")

    # Permanent project registry: attach project-shaped headlines to records, apply
    # data/project_overrides.json, rebuild statuses, then the static project pages and sitemap.
    import registry
    reg_out = Path(args.out) / "registry.json" if args.out else registry.REGISTRY_FILE
    reg_in = reg_out if reg_out.exists() else registry.REGISTRY_FILE
    records = registry.update(kept, gaz, registry_in=reg_in, registry_out=reg_out, log=log)
    registry.build_pages(records, out_dir=Path(args.out) / "projects" if args.out else registry.PAGES_DIR,
                         sitemap=Path(args.out) / "sitemap.xml" if args.out else registry.SITEMAP_FILE, log=log)

    # A small run report for the Methodology page.
    status_out.write_text(json.dumps({
        "updated": now.isoformat(timespec="seconds"),
        "feeds_total": len(sources),
        "feeds_ok": feeds_ok,
        "items_total": len(items),
        "items_new": new_this_run,
    }, indent=1) + "\n", encoding="utf-8")
    log(f"Wrote {status_out}: {feeds_ok} of {len(sources)} feeds returned data, {new_this_run} new headlines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
