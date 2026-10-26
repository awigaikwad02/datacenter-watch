#!/usr/bin/env python3
"""
Health check for The Rack Report: everything that does not need a browser.

    python scripts/healthcheck.py                    # full check, writes data/health.json
    python scripts/healthcheck.py --context update   # gate used by the hourly fetch workflow
    python scripts/healthcheck.py --render-md FILE   # write data/health.json as a Markdown table

Checks pipeline freshness, data integrity, internal links, the sitemap, page
metadata, CNAME and basic security hygiene. Prints a table, writes
data/health.json (unless --no-write) and exits 1 when any check fails.

--context update is for the fetch workflow, which runs this on the freshly
written data before committing it. It runs only the pipeline and data checks
(site and security checks test code, which a data update cannot change), skips
the checks that look at git history or the GitHub API, and treats quality
measures (a feed that returned nothing, category balance, location coverage,
non-U.S. leaks) as warnings: those should not freeze the hourly updates, while
corrupt or malformed data still fails the run so it is never committed.
"""

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITE = "https://therackreport.org"
PAGES = {"index.html": "/", "newsroom.html": "/newsroom", "atlas.html": "/atlas",
         "companies.html": "/companies", "learn.html": "/learn", "methodology.html": "/methodology"}
MAX_AGE = timedelta(hours=2)
MAX_CATEGORY_SHARE = 0.30
MIN_LOCATED_SHARE = 0.50
MAX_PAGE_BYTES = 300 * 1024
MAX_NEWS_BYTES = 3 * 1024 * 1024
STATUSES = {"Announced", "Planned", "Under construction", "Operational", "Expansion", "Cancelled / Blocked"}
CANCELLED = "Cancelled / Blocked"
# U.S. boxes: lower 48, Alaska (both sides of the antimeridian), Hawaii, Puerto Rico and USVI, Guam.
US_BOXES = [(24.3, 49.5, -125.0, -66.8), (51.0, 71.6, -180.0, -129.9), (51.0, 53.1, 172.0, 180.0),
            (18.8, 22.4, -160.4, -154.7), (17.6, 18.6, -67.4, -64.5), (13.2, 13.7, 144.6, 145.0)]
NOW = datetime.now(timezone.utc)

checks = []


def check(name, status, value="", detail=""):
    checks.append({"name": name, "status": status, "value": str(value), "detail": str(detail)})


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def iso(s):
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def ago(d):
    m = int((NOW - d).total_seconds() // 60)
    return f"{m // 60}h {m % 60}m ago" if m >= 60 else f"{m}m ago"


def git(*args):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
def pipeline(ctx):
    if ctx == "update":
        check("Last data commit within 2h", "skip", "", "not checked while the update itself runs")
        check("Workflow runs (last 10)", "skip", "", "not checked while the update itself runs")
    else:
        last = git("log", "-1", "--format=%cI", "--grep=Update news data")
        d = iso(last) if last else None
        if not d:
            check("Last data commit within 2h", "fail", "none", "no 'Update news data' commit found")
        else:
            check("Last data commit within 2h", "pass" if NOW - d <= MAX_AGE else "fail", ago(d), last)
        runs(ctx)

    st_path = DATA / "status.json"
    if not st_path.exists():
        check("Feeds all returned data (status.json)", "fail", "missing", "data/status.json not found")
    else:
        st = load(st_path)
        ok = st.get("feeds_total") and st.get("feeds_ok") == st.get("feeds_total")
        bad = "warn" if ctx == "update" else "fail"
        check("Feeds all returned data (status.json)", "pass" if ok else bad,
              f"{st.get('feeds_ok')}/{st.get('feeds_total')}", f"run at {st.get('updated')}, {st.get('items_new')} new")

    tmp = Path(tempfile.mkdtemp(prefix="rr-health-"))
    try:
        r = subprocess.run([sys.executable, str(ROOT / "scripts/fetch_news.py"), "--sample",
                            str(ROOT / "scripts/sample_feed.xml"), "--out", str(tmp)],
                           capture_output=True, text=True, timeout=300)
        valid = all(_parses(tmp / f) for f in ("news.json", "registry.json", "status.json"))
        check("Fetcher runs on sample feed", "pass" if r.returncode == 0 and valid else "fail",
              f"exit {r.returncode}", "outputs parse as JSON" if valid else (r.stderr or r.stdout)[-300:])
        hostile(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def runs(ctx):
    if not shutil.which("gh"):
        check("Workflow runs (last 10)", "skip", "", "gh CLI not available")
        return
    repo = os.environ.get("GITHUB_REPOSITORY", "awigaikwad02/datacenter-watch")
    r = subprocess.run(["gh", "run", "list", "-R", repo, "-L", "10", "--json",
                        "workflowName,conclusion,status,startedAt,updatedAt"], capture_output=True, text=True)
    if r.returncode != 0:
        check("Workflow runs (last 10)", "skip", "", "gh run list failed: " + r.stderr.strip()[:120])
        return
    # The health check's own runs are left out: their failures are already reported in its issue.
    rows = [x for x in json.loads(r.stdout) if x["status"] == "completed" and x["workflowName"] != "Health check"]
    ok = sum(x["conclusion"] == "success" for x in rows)
    # A Pages deploy cancelled because a newer push superseded it is normal, not a failure.
    cancelled = sum(x["conclusion"] == "cancelled" for x in rows)
    failed = [x["workflowName"] for x in rows if x["conclusion"] not in ("success", "skipped", "cancelled")]
    secs = [(iso(x["updatedAt"]) - iso(x["startedAt"])).total_seconds() for x in rows]
    avg = round(sum(secs) / len(secs)) if secs else 0
    check("Workflow runs (last 10)", "pass" if not failed else "fail",
          f"{ok}/{len(rows)} succeeded, {cancelled} superseded, avg {avg}s", "failed: " + ", ".join(failed) if failed else "")


def _parses(p):
    try:
        load(p)
        return True
    except (OSError, ValueError):
        return False


def hostile(tmp):
    """Feed the fetcher a javascript: link and control characters; both must be dropped."""
    feed = tmp / "hostile.xml"
    feed.write_text("""<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
<item><title>Evil data center campus in Abilene, Texas - Bad Outlet</title><link>javascript:alert(1)</link>
<pubDate>%s</pubDate><source url="https://x">Bad Outlet</source></item>
<item><title>Data center\x07 campus planned\x1b in Waco, Texas - Good Outlet</title><link>https://example.com/a</link>
<pubDate>%s</pubDate><source url="https://y">Good Outlet</source></item>
</channel></rss>""" % ((NOW.strftime("%a, %d %b %Y %H:%M:%S GMT"),) * 2), encoding="utf-8")
    out = tmp / "hostile"
    subprocess.run([sys.executable, str(ROOT / "scripts/fetch_news.py"), "--sample", str(feed), "--out", str(out)],
                   capture_output=True, text=True, timeout=300)
    try:
        items = load(out / "news.json")["items"]
    except (OSError, ValueError, KeyError):
        check("Fetcher drops non-http links and control characters", "fail", "", "sample run produced no news.json")
        return
    js = [i for i in items if not str(i.get("link", "")).startswith(("http://", "https://"))]
    ctrl = [i for i in items if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", i.get("title", "") + i.get("source", ""))]
    waco = any("Waco" in i["title"] for i in items)
    good = not js and not ctrl and waco
    check("Fetcher drops non-http links and control characters", "pass" if good else "fail",
          f"{len(js)} bad links, {len(ctrl)} with control chars",
          "clean item kept" if waco else "the clean test item was dropped too")


# ---------------------------------------------------------------------------
# Data integrity
# ---------------------------------------------------------------------------
def data(ctx):
    files = ["news.json", "registry.json", "project_overrides.json", "projects.json", "status.json"] + \
            [os.path.relpath(p, DATA) for p in sorted(glob.glob(str(DATA / "archive/*.json")))]
    broken = [f for f in files if not _parses(DATA / f)]
    check("Data files parse as JSON", "fail" if broken else "pass", f"{len(files) - len(broken)}/{len(files)}",
          ", ".join(broken))
    if broken:
        return

    news = load(DATA / "news.json")
    items = news.get("items", [])
    size = (DATA / "news.json").stat().st_size
    check("news.json under 3 MB", "pass" if size <= MAX_NEWS_BYTES else "fail", f"{size / 1024:.0f} KB")

    up = iso(news.get("updated"))
    check("news.json updated within 2h", "pass" if up and NOW - up <= MAX_AGE else "fail",
          ago(up) if up else "missing", news.get("updated"))

    need = ("id", "title", "link", "source", "published", "category", "cluster_id")
    problems, future = [], []
    for it in items:
        miss = [k for k in need if not it.get(k)]
        if miss:
            problems.append(f"{it.get('id')}: missing {','.join(miss)}")
        if it.get("link") and not str(it["link"]).startswith(("http://", "https://")):
            problems.append(f"{it.get('id')}: link scheme")
        d = iso(it.get("published"))
        if not d:
            problems.append(f"{it.get('id')}: bad published")
        elif d > NOW + timedelta(minutes=10):
            future.append(it["id"])
    dupes = [k for k, n in Counter(i.get("id") for i in items).items() if n > 1]
    check("News items well formed", "fail" if problems else "pass", f"{len(items)} items, {len(problems)} problems",
          "; ".join(problems[:5]))
    check("News ids unique", "fail" if dupes else "pass", f"{len(dupes)} duplicates", ", ".join(dupes[:5]))
    check("No future publish dates", "fail" if future else "pass", f"{len(future)} in the future", ", ".join(future[:5]))

    soft = "warn" if ctx == "update" else "fail"
    n = len(items) or 1
    cats = Counter(i.get("category") for i in items)
    top, top_n = cats.most_common(1)[0] if cats else ("", 0)
    check("No category above 30%", "pass" if top_n / n <= MAX_CATEGORY_SHARE else soft,
          f"top: {top} {100 * top_n / n:.1f}%", ", ".join(f"{k} {v}" for k, v in cats.most_common()))
    located = sum(1 for i in items if i.get("state"))
    check("At least 50% of headlines located", "pass" if located / n >= MIN_LOCATED_SHARE else soft,
          f"{located}/{len(items)} ({100 * located / n:.1f}%)",
          f"with a company: {sum(1 for i in items if i.get('companies'))}")

    leaks = [i for i in items for l in i.get("locations", [])
             if (l.get("country") or ("US" if str(l.get("name", "")).endswith(", US") else "?")) != "US"]
    check("No non-U.S. locations in headlines", soft if leaks else "pass", f"{len(leaks)} items",
          "; ".join(i["title"][:60] for i in leaks[:3]))

    archive(items, ctx)
    registry(ctx)
    curated()
    announced_metric()


def archive(items, ctx="full"):
    idx = load(DATA / "archive/index.json")
    on_disk = {Path(p).stem for p in glob.glob(str(DATA / "archive/*.json")) if re.match(r"\d{4}-\d{2}$", Path(p).stem)}
    listed = {m["month"] for m in idx.get("months", [])}
    archived, dup_months, cross = set(), [], []
    for m in sorted(on_disk):
        ids = [i["id"] for i in load(DATA / f"archive/{m}.json").get("items", [])]
        if len(ids) != len(set(ids)):
            dup_months.append(m)
        cross += [i for i in set(ids) if i in archived]
        archived.update(ids)
    check("Archive ids unique across all months", "fail" if cross else "pass", f"{len(archived)} ids, {len(cross)} in two months",
          ", ".join(cross[:5]))
    # Every month from the earliest archived one to the current month has a file.
    if on_disk:
        y, mo = map(int, min(on_disk).split("-"))
        expected = []
        while (y, mo) <= (NOW.year, NOW.month):
            expected.append(f"{y:04d}-{mo:02d}")
            y, mo = (y + 1, 1) if mo == 12 else (y, mo + 1)
        gaps = [m for m in expected if m not in on_disk]
        # A gap is a coverage problem, not bad data: it warns in the hourly gate and fails the daily check.
        check("Archive months contiguous to now", ("warn" if ctx == "update" else "fail") if gaps else "pass", f"{min(on_disk)} to {expected[-1]}, {len(gaps)} missing",
              ", ".join(gaps[:8]))
    missing = [i["id"] for i in items if i["id"] not in archived]
    ok = listed == on_disk and not dup_months and not missing
    check("Archive consistent with news.json", "pass" if ok else "fail",
          f"{len(on_disk)} month(s), {idx.get('total')} headlines, earliest {str(idx.get('earliest'))[:10]}",
          "; ".join(filter(None, [
              f"index/disk mismatch {sorted(listed ^ on_disk)}" if listed != on_disk else "",
              f"duplicate ids in {dup_months}" if dup_months else "",
              f"{len(missing)} news ids not archived" if missing else ""])))


def in_us(lat, lon):
    return any(a <= lat <= b and c <= lon <= d for a, b, c, d in US_BOXES)


def registry(ctx):
    """data/registry.json: ids unique, nothing lost since the last commit, valid statuses and
    history dates, every record inside the U.S., every attached headline in the archive."""
    reg = load(DATA / "registry.json")
    recs = reg.get("records", [])
    ids = [r.get("id") for r in recs]
    dupes = [k for k, n in Counter(ids).items() if n > 1]
    check("Registry ids unique", "fail" if dupes else "pass", f"{len(recs)} records, {sum(1 for r in recs if not r.get('hidden'))} visible",
          ", ".join(map(str, dupes[:5])))

    prev = git("show", "HEAD:data/registry.json")
    if prev:
        try:
            old_ids = {r["id"] for r in json.loads(prev).get("records", [])}
        except ValueError:
            old_ids = set()
        lost = sorted(old_ids - set(ids))
        check("No registry record lost since the last commit", "fail" if lost else "pass",
              f"{len(old_ids)} -> {len(ids)}", ", ".join(lost[:5]))
    else:
        check("No registry record lost since the last commit", "skip", "", "no committed registry yet")

    archived = set()
    for p in glob.glob(str(DATA / "archive/*.json")):
        if re.match(r"\d{4}-\d{2}$", Path(p).stem):
            archived.update(i["id"] for i in load(p).get("items", []))
    bad_status, bad_dates, outside, orphans = [], [], [], []
    for r in recs:
        if r.get("status") not in STATUSES:
            bad_status.append(f"{r['id']}: {r.get('status')}")
        for h in r.get("status_history", []):
            if not h.get("date") or not (iso(h["date"]) or re.match(r"^\d{4}-\d{2}(-\d{2})?$", str(h["date"]))):
                bad_dates.append(f"{r['id']}: {h.get('date')}")
        if not (isinstance(r.get("lat"), (int, float)) and isinstance(r.get("lon"), (int, float)) and in_us(r["lat"], r["lon"])):
            outside.append(f"{r['id']}: {r.get('lat')},{r.get('lon')}")
        orphans += [f"{r['id']}: {n['id']}" for n in r.get("news", []) if n["id"] not in archived and not n["id"].startswith("selftest-")]
    check("Registry statuses and history dates valid", "fail" if bad_status or bad_dates else "pass",
          f"{len(bad_status)} bad statuses, {len(bad_dates)} bad dates", "; ".join((bad_status + bad_dates)[:5]))
    check("Registry records inside the U.S.", "fail" if outside else "pass", f"{len(outside)} outside", "; ".join(outside[:5]))
    unbacked = [r["id"] for r in recs if not r.get("hidden") and not r.get("curated") and r.get("status") == "Operational"
                and not r.get("status_override") and not any(n.get("stage_signal") == "Operational" for n in r.get("news", []))]
    check("Operational records backed by an operational headline", "fail" if unbacked else "pass",
          f"{sum(1 for r in recs if r.get('status') == 'Operational' and not r.get('curated'))} detected operational, {len(unbacked)} without one",
          ", ".join(unbacked[:5]) + ("" if not unbacked else " (curated records take their status from projects.json)"))
    check("Registry news all in the archive", "fail" if orphans else "pass",
          f"{sum(len(r.get('news', [])) for r in recs)} attached headlines, {len(orphans)} missing", "; ".join(orphans[:5]))

    sys.path.insert(0, str(ROOT / "scripts"))
    import registry as rg
    got = rg.selftest()
    ok = len(got) == 1 and len(got[0]["news"]) == 3 and [h["status"] for h in got[0]["status_history"]] == ["Announced", "Under construction", "Operational"]
    check("Registry status machine self-test", "pass" if ok else "fail",
          " -> ".join(h["status"] for h in got[0]["status_history"]) if len(got) == 1 else f"{len(got)} records",
          f"{got[0]['id']}, {len(got[0]['news'])} news" if got else "")

def curated():
    projects = load(DATA / "projects.json").get("projects", [])
    need = ("id", "name", "company", "status", "location", "lat", "lon", "state")
    bad = []
    for p in projects:
        miss = [k for k in need if p.get(k) in (None, "")]
        if miss:
            bad.append(f"{p.get('id')}: missing {','.join(miss)}")
        if p.get("status") not in STATUSES:
            bad.append(f"{p.get('id')}: status {p.get('status')}")
        if isinstance(p.get("lat"), (int, float)) and isinstance(p.get("lon"), (int, float)) and not in_us(p["lat"], p["lon"]):
            bad.append(f"{p.get('id')}: outside the U.S.")
        for t in p.get("timeline", []):
            if not (t.get("date") and t.get("event") and str(t.get("url", "")).startswith("https://")):
                bad.append(f"{p.get('id')}: timeline entry {t.get('date')}")
    names = [k for k, n in Counter(p.get("name") for p in projects).items() if n > 1]
    ids = [k for k, n in Counter(p.get("id") for p in projects).items() if n > 1]
    if names or ids:
        bad.append(f"duplicates: {names + ids}")
    check("Curated projects valid", "fail" if bad else "pass", f"{len(projects)} projects, {len(bad)} problems",
          "; ".join(bad[:5]))


PRECISION = {"city": 4, "county": 3, "state": 2, "source": 1}


def states_in_app():
    js = (ROOT / "assets/app.js").read_text(encoding="utf-8")
    block = js[js.index("const STATES"):js.index("};", js.index("const STATES"))]
    return set(re.findall(r"\b([A-Z]{2}):", block))


def announced_metric():
    """Recompute the Overview's "Projects announced this month" the way assets/app.js and
    overview.js do from the registry: visible records first seen this month (curated: their
    announced month), status Announced or Planned, pinned to a place, not low confidence.
    Cancelled / Blocked never counts. The browser check compares this number with the page."""
    states = states_in_app()
    month_start = NOW.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    counted, cancelled_now = 0, 0
    for r in load(DATA / "registry.json").get("records", []):
        if r.get("hidden") or r.get("state") not in states:
            continue
        t = iso(r["announced"] + "-15T12:00:00+00:00") if r.get("curated") and r.get("announced") else iso(r.get("first_seen") or "")
        if not t or t < month_start:
            continue
        if r.get("status") == CANCELLED:
            cancelled_now += 1
        elif r.get("status") in ("Announced", "Planned") and r.get("precision") not in ("state", "source") and r.get("confidence") != "low":
            counted += 1
    check("Overview 'announced' excludes Cancelled / Blocked", "pass", counted,
          f"{cancelled_now} cancelled or blocked records this month are left out")

# ---------------------------------------------------------------------------
# Site: links, sitemap, metadata, assets
# ---------------------------------------------------------------------------
HREF = re.compile(r"""\b(?:href|src)=["']([^"'#]+)""")
JS_PATH = re.compile(r"""["'](/(?:[a-z][a-z0-9-]*)?)(?:#[^"']*)?["']""")


def resolve(path):
    """Map a root-relative URL to a file the way GitHub Pages does."""
    path = path.split("?")[0].split("#")[0]
    if path in ("", "/"):
        return ROOT / "index.html"
    p = ROOT / path.lstrip("/")
    if p.is_file():
        return p
    if p.is_dir() and (p / "index.html").is_file():
        return p / "index.html"
    if (ROOT / (path.lstrip("/") + ".html")).is_file():
        return ROOT / (path.lstrip("/") + ".html")
    return None


def sitemap_paths():
    tree = ET.parse(ROOT / "sitemap.xml")
    locs = [e.text.strip() for e in tree.iter() if e.tag.endswith("loc")]
    return locs


def site():
    html_files = sorted(glob.glob(str(ROOT / "*.html"))) + sorted(glob.glob(str(ROOT / "projects/*/index.html")))
    js_files = sorted(glob.glob(str(ROOT / "assets/*.js")))
    links, broken, with_html = set(), [], []
    for f in html_files:
        for u in HREF.findall(Path(f).read_text(encoding="utf-8")):
            if re.match(r"^(https?:|mailto:|data:|javascript:)", u):
                continue
            base = "/" + u if not u.startswith("/") else u
            links.add(base.split("?")[0])
    for f in js_files:
        for u in JS_PATH.findall(Path(f).read_text(encoding="utf-8")):
            links.add(u)
    pages = set()
    for u in sorted(links):
        if ".html" in u:
            with_html.append(u)
        if not resolve(u):
            broken.append(u)
        if not u.startswith("/assets/") and not u.startswith("/data/") and resolve(u) and resolve(u).suffix == ".html":
            pages.add(u)
    check("Internal links resolve", "fail" if broken else "pass", f"{len(links)} links, {len(broken)} broken", ", ".join(broken[:8]))
    check("Internal links use clean URLs", "fail" if with_html else "pass", f"{len(with_html)} with .html", ", ".join(with_html[:8]))

    locs = sitemap_paths()
    sm_paths = {l.replace(SITE, "") or "/" for l in locs}
    off = sorted(p for p in pages if p not in sm_paths and p != "/projects")
    missing = sorted(p for p in sm_paths if not resolve(p))
    reg = load(DATA / "registry.json").get("records", []) if (DATA / "registry.json").is_file() else []
    project_pages = {p.parent.name for p in (ROOT / "projects").glob("*/index.html")}
    want_pages = {f"/projects/{d}/" for d in project_pages}
    base = {"/", "/newsroom", "/atlas", "/companies", "/learn", "/methodology"}
    missing_base = sorted(base - sm_paths)
    unlisted = sorted(want_pages - sm_paths)
    hidden_pages = sorted(r["id"] for r in reg if r.get("hidden") and r["id"] in project_pages)
    check("Sitemap matches pages", "fail" if off or missing or missing_base or unlisted or hidden_pages else "pass",
          f"{len(locs)} entries (6 site pages + {len(want_pages)} project pages)",
          "; ".join(filter(None, [f"linked but not in sitemap: {off}" if off else "",
                                  f"sitemap entry without a page: {missing[:5]}" if missing else "",
                                  f"site pages missing: {missing_base}" if missing_base else "",
                                  f"project pages not in sitemap: {unlisted[:5]}" if unlisted else "",
                                  f"pages for hidden records: {hidden_pages[:5]}" if hidden_pages else ""])))
    pages_bytes = sum(p.stat().st_size for p in (ROOT / "projects").rglob("*.html"))
    check("Project pages under 5 MB", "pass" if pages_bytes <= 5 * 1024 * 1024 else "fail",
          f"{len(project_pages)} pages, {pages_bytes / 1024:.0f} KB")

    bad_meta = []
    for f, clean in PAGES.items():
        s = (ROOT / f).read_text(encoding="utf-8")
        want = SITE + clean
        can = re.search(r'<link rel="canonical" href="([^"]+)"', s)
        og = re.search(r'<meta property="og:url" content="([^"]+)"', s)
        if not can or can.group(1) != want:
            bad_meta.append(f"{f} canonical {can.group(1) if can else 'missing'}")
        if not og or og.group(1) != want:
            bad_meta.append(f"{f} og:url {og.group(1) if og else 'missing'}")
    check("Canonical and og:url are clean", "fail" if bad_meta else "pass", f"{len(PAGES)} pages", "; ".join(bad_meta))
    og_png = ROOT / "assets/og.png"
    check("og.png present", "pass" if og_png.is_file() and og_png.stat().st_size > 1000 else "fail",
          f"{og_png.stat().st_size // 1024} KB" if og_png.is_file() else "missing")

    cname = (ROOT / "CNAME").read_text(encoding="utf-8") if (ROOT / "CNAME").is_file() else ""
    check("CNAME is exactly therackreport.org", "pass" if cname.strip() == "therackreport.org" and len(cname.split()) == 1 else "fail",
          repr(cname))
    robots = (ROOT / "robots.txt").read_text(encoding="utf-8") if (ROOT / "robots.txt").is_file() else ""
    check("robots.txt and sitemap.xml present", "pass" if robots and "Sitemap: " + SITE + "/sitemap.xml" in robots and locs else "fail",
          "robots.txt points at the sitemap" if robots else "robots.txt missing")

    insecure = []
    for f in html_files + js_files:
        for i, line in enumerate(Path(f).read_text(encoding="utf-8").splitlines(), 1):
            for u in re.findall(r"""(?:src|href)=["'](http://[^"']+)|["'](http://[^"']+)["']""", line):
                url = u[0] or u[1]
                if "www.w3.org" not in url:
                    insecure.append(f"{Path(f).name}:{i}")
    check("External resources use https", "fail" if insecure else "pass", f"{len(insecure)} http URLs", ", ".join(insecure[:5]))

    app = (ROOT / "assets/app.js").read_text(encoding="utf-8")
    cdn = [l for l in app.splitlines() if "https://unpkg.com/" in l]
    unpinned = [l.strip()[:60] for l in cdn if "sha384-" not in l]
    check("Leaflet and markercluster carry SRI", "pass" if cdn and not unpinned and "el.integrity = sri" in app else "fail",
          f"{len(cdn) - len(unpinned)}/{len(cdn)} with integrity")

    risky = unescaped_html(js_files)
    check("No unescaped data fields in HTML strings", "fail" if risky else "pass", f"{len(risky)} spots", "; ".join(risky[:5]))

    heavy, sizes = [], []
    for f in PAGES.keys() | {"404.html"}:
        s = (ROOT / f).read_text(encoding="utf-8")
        total = len(s.encode())
        for u in re.findall(r"""(?:src|href)=["'](/?assets/[^"'?]+\.(?:js|css))""", s):
            p = ROOT / u.lstrip("/")
            total += p.stat().st_size if p.is_file() else 0
        sizes.append(f"{f} {total // 1024} KB")
        if total > MAX_PAGE_BYTES:
            heavy.append(f)
    check("Pages under 300 KB (HTML+CSS+JS)", "fail" if heavy else "pass",
          max(sizes, key=lambda x: int(x.split()[1])), ", ".join(sorted(sizes)))

    fresh_ok = all(k in app for k in ('cache: "no-store"', "POLL_MS = 10 * 60e3", "setUpdated(d.updated)", 'fresh("data/news.json")'))
    check("Freshness badge and 10-minute no-store poller", "pass" if fresh_ok else "fail",
          "found in assets/app.js" if fresh_ok else "expected code not found")


FIELDS = "title|source|name|link|place|location|snippet|notes|company|event|url|source_url|category|status|cluster_title|desc|label"
UNESC = re.compile(r"\+\s*(?![\w$.]*(?:esc|encodeURIComponent|fmt\w*|ago|icon|tone|toLocale\w*)\()"
                   r"([A-Za-z_$][\w$]*(?:\.[\w$]+|\[[^\]]+\])*\.(?:%s))\b(?!\s*[\(\.])" % FIELDS)


def unescaped_html(js_files):
    """Heuristic: a data field concatenated straight into a line that builds HTML tags."""
    out = []
    for f in js_files:
        for i, line in enumerate(Path(f).read_text(encoding="utf-8").splitlines(), 1):
            if "<" not in line or not re.search(r"""["']\s*<|<[a-z]+[ >]""", line):
                continue
            for m in UNESC.finditer(line):
                out.append(f"{Path(f).name}:{i} {m.group(1)}")
    return out


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
SECRET = re.compile(r"(?i)(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|gh[ousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|"
                    r"sk-[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
                    r"(?:api[_-]?key|token|password|passwd|secret)[\"']?\s*[:=]\s*[\"'][^\"'\s]{12,}[\"'])")


def security():
    tracked = git("ls-files").splitlines()
    hits = []
    for f in tracked:
        if f.startswith("data/") or f == "scripts/healthcheck.py" or f.endswith((".png", ".ico", ".jpg", ".svg")):
            continue
        p = ROOT / f
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if SECRET.search(line) and "SECRET =" not in line:
                hits.append(f"{f}:{i}")
    check("No secrets in the repo", "fail" if hits else "pass", f"{len(hits)} matches in {len(tracked)} files", ", ".join(hits[:5]))

    unpinned, perms = [], []
    for wf in sorted(glob.glob(str(ROOT / ".github/workflows/*.yml"))):
        text = Path(wf).read_text(encoding="utf-8")
        for u in re.findall(r"uses:\s*([^\s#]+)", text):
            if not re.search(r"@[0-9a-f]{40}$", u):
                unpinned.append(f"{Path(wf).name}: {u}")
        block = re.search(r"^permissions:\n((?:[ \t]+.+\n)+)", text, re.M)
        got = sorted(l.strip() for l in block.group(1).splitlines()) if block else []
        # The data job only commits; the health job also manages its issue and reads run history.
        want = ["contents: write"] + (["actions: read", "issues: write"] if Path(wf).name == "healthcheck.yml" else [])
        if got != sorted(want):
            perms.append(f"{Path(wf).name}: {got or 'none'}")
    check("Workflow actions pinned to commit SHAs", "fail" if unpinned else "pass", f"{len(unpinned)} unpinned", "; ".join(unpinned[:6]))
    check("Workflow permissions minimal", "fail" if perms else "pass",
          "update: contents: write; health: + issues: write, actions: read", "; ".join(perms))
    check("SECURITY.md present", "pass" if (ROOT / "SECURITY.md").is_file() else "fail", "")


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
def overall(rows):
    return "fail" if any(c["status"] == "fail" for c in rows) else "pass"


def table(rows):
    w = max(len(c["name"]) for c in rows)
    lines = [f"{'CHECK'.ljust(w)}  STATUS  VALUE"]
    for c in rows:
        lines.append(f"{c['name'].ljust(w)}  {c['status'].upper().ljust(6)}  {c['value']}" + (f"  ({c['detail']})" if c["detail"] and c["status"] != "pass" else ""))
    return "\n".join(lines)


def markdown(doc):
    out = [f"**Overall: {doc['overall'].upper()}** · checked {doc['checked_at']}", "",
           "| Check | Status | Value | Detail |", "|---|---|---|---|"]
    for c in doc["checks"]:
        cell = lambda s: str(s).replace("|", "\\|").replace("\n", " ")[:300]
        out.append(f"| {cell(c['name'])} | {c['status'].upper()} | {cell(c['value'])} | {cell(c['detail'])} |")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--context", choices=["full", "update"], default="full")
    ap.add_argument("--no-write", action="store_true", help="do not write data/health.json")
    ap.add_argument("--render-md", metavar="FILE", help="render data/health.json as Markdown and exit")
    args = ap.parse_args()
    if args.render_md:
        Path(args.render_md).write_text(markdown(load(DATA / "health.json")), encoding="utf-8")
        return 0

    sections = [("pipeline", lambda: pipeline(args.context)), ("data", lambda: data(args.context))]
    if args.context == "full":
        sections += [("site", site), ("security", security)]
    for name, section in sections:
        try:
            section()
        except Exception as e:  # a crashing section is itself a failure, keep checking the rest
            check(f"Check crashed: {name}", "fail", type(e).__name__, str(e)[:200])

    doc = {"checked_at": NOW.isoformat(timespec="seconds"), "overall": overall(checks), "context": args.context, "checks": checks}
    print(table(checks))
    print(f"\nOverall: {doc['overall'].upper()} ({sum(c['status'] == 'fail' for c in checks)} failing)")
    if not args.no_write and args.context == "full":
        (DATA / "health.json").write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    return 1 if doc["overall"] == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
