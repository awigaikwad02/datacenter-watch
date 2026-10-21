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

Run locally:  python scripts/fetch_news.py
GitHub Actions runs it on a schedule (see .github/workflows/update.yml).
"""

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
    ("Policy & Community",
     r"\b(zoning|rezon\w*|city council|county council|council|commission(ers?)?|board of supervisors|supervisors|"
     r"moratorium|ordinance|permits?|permitting|lawsuit|sue[sd]?|residents?|neighbou?rs?|opposition|oppose[sd]?|"
     r"protest\w*|pushback|tax (break|incentive|abatement|exemption)s?|incentives?|regulat\w*|legislat\w*|"
     r"senate|governor|lawmakers?|approv\w*|reject\w*|denie[sd]|deny|vote[sd]?|hearing|referendum|noise|"
     r"environmental|water use|backlash)\b"),
    ("Construction",
     r"\b(break(s|ing)? ground|groundbreaking|ground-breaking|under construction|construction|"
     r"opens|opened|officially open|now open|grand opening|completes?|completed|completion|"
     r"goes live|comes online|now online|commissioned|topping out|contractor|crews|build-?out)\b"),
    ("Announcements",
     r"\b(announc\w*|plans?|planned|planning|propos\w*|unveil\w*|to build|will build|eyes|eyeing|"
     r"selects?|chooses?|picks?|lands|secures?|launch\w*|expan\w*|new campus|campus|mega|project)\b"),
    ("Deals & Investment",
     r"\b(acqui\w*|merger|buys?|bought|purchase\w*|invest\w*|funding|raises?|raised|financing|loan|debt|"
     r"bonds?|lease[sd]?|leasing|joint venture|partnership|stake|ipo|valuation|billion|million|\$\s?\d)\b"),
    ("Power & Energy",
     r"\b(power|grid|utilit(y|ies)|electric\w*|energy|megawatts?|gigawatts?|\d+\s?[MG]W|nuclear|reactors?|"
     r"smrs?|natural gas|gas turbines?|turbines?|solar|wind|batter(y|ies)|transmission|substation|"
     r"demand|load|rates?|ratepayers?|outage|blackout|cooling|water)\b"),
    ("AI & Hyperscale",
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
    ("Announced",
     re.compile(r"\b(announc\w*|plans?|planned|planning|propos\w*|unveil\w*|to build|will build|eyes|eyeing|"
                r"selects?|chooses?|picks?|lands|secures?|approv\w*|expan\w*|acquires? (land|site)|"
                r"buys? (land|site|acres)|\d[\d,]* acres)\b", re.I)),
]

MW_RE = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s?(?:MW|megawatts?)\b", re.I)
GW_RE = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s?(?:GW|gigawatts?)\b", re.I)
MONEY_RE = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)\s?(billion|million|bn|b|m)\b", re.I)
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
def main():
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

    log(f"Fetching {len(sources)} feeds")
    fresh = {}
    for label, url in sources:
        parsed = fetch_feed(url)
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
            primary, tags = classify(title)
            locs = find_locations(title + " " + snippet, gaz, patterns)
            item = {
                "id": key,
                "title": title,
                "link": link,
                "source": source,
                "published": dt.isoformat(timespec="seconds"),
                "category": primary,
                "tags": tags,
                "locations": locs[:3],
                "feed": label,
            }
            item.update(extract_numbers(title))
            fresh[key] = item
            n += 1
        log(f"  {label}: {n} items")

    # Merge with the existing news file so stories stay for NEWS_MAX_AGE_DAYS
    existing = load_json(NEWS_FILE, {}).get("items", [])
    merged = {it["id"]: it for it in existing if "id" in it}
    merged.update(fresh)
    cutoff = now - timedelta(days=NEWS_MAX_AGE_DAYS)
    items = [it for it in merged.values()
             if datetime.fromisoformat(it["published"]) >= cutoff]
    items.sort(key=lambda it: it["published"], reverse=True)
    items = items[:NEWS_MAX_ITEMS]

    NEWS_FILE.write_text(json.dumps({
        "updated": now.isoformat(timespec="seconds"),
        "count": len(items),
        "new_this_run": len([k for k in fresh if k not in {it["id"] for it in existing}]),
        "items": items,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"Wrote {NEWS_FILE.name}: {len(items)} items")

    # Project candidates: site + stage + place
    cand_existing = load_json(CAND_FILE, {}).get("projects", [])
    cands = {c["id"]: c for c in cand_existing if "id" in c}
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
    CAND_FILE.write_text(json.dumps({
        "updated": now.isoformat(timespec="seconds"),
        "count": len(cand_list),
        "projects": cand_list,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"Wrote {CAND_FILE.name}: {len(cand_list)} candidates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
