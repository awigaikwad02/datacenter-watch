#!/usr/bin/env python3
"""
One-off historical news backfill (run by hand or from the "Backfill news" workflow,
never on a schedule).

    python scripts/backfill_news.py --start 2024-10-01 --end today --window-days 14 --resume

For every window and each lifecycle query below it asks Google News RSS (U.S. edition,
the same google_news_url() builder as the hourly run) for headlines between two dates
using the after:/before: operators. Every headline takes exactly the hourly path
(fetch_news.entry_to_item: clean, safe link, blocklist, on-topic, U.S. filter, tagging,
figures), is clustered with its window, and is appended to data/archive/YYYY-MM.json by
published month. data/news.json is never touched. At the end of each chunk the new
headlines are attached to the registry and the project pages are rebuilt.

Progress is saved to data/backfill_progress.json after every window; --resume continues
from there. Exit codes: 0 finished, 10 stopped after --max-windows with windows left,
2 ten requests in a row failed, 3 the date operators returned nothing for the whole
first month (stop and look before trying anything else).
"""

import argparse
import json
import random
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import feedparser

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_news as fn  # noqa: E402
import registry as rg  # noqa: E402

PROGRESS_FILE = fn.DATA / "backfill_progress.json"
DELAY = (2.0, 3.0)            # seconds between requests
MAX_CONSECUTIVE_FAILURES = 10
TEST_DAYS = 30                # if the first month returns nothing at all, stop

# One query per lifecycle stage so each window stays under Google News' 100-result cap.
# The third value overrides the window length for that query (the busiest one).
# Google keeps only the first 32 words of a query, so the date operators go first and the
# operational query is asked in two halves (it is 32 words on its own); a window that still
# returns 100 results is split in half until it does not, down to one day.
RESULT_CAP = 100
QUERIES = [
    ("operational", '"data center" (opens OR opened OR "now open" OR "grand opening" OR "ribbon cutting" OR "goes live")', None),
    ("operational", '"data center" ("comes online" OR "now operational" OR "officially open" OR completes OR completed OR energized)', None),
    ("construction", '"data center" ("breaks ground" OR groundbreaking OR "under construction" OR "construction begins" OR '
                     '"construction underway" OR "topping out")', None),
    ("announced", '"data center" (announces OR announced OR plans OR proposed OR "to build" OR unveils OR approves OR approved)', 7),
    ("cancelled", '"data center" (cancels OR cancelled OR scraps OR withdraws OR rejects OR rejected OR denied OR halts OR moratorium)', None),
    ("hyperscaler", '(Microsoft OR Google OR Amazon OR AWS OR Meta OR Oracle OR OpenAI OR xAI OR CoreWeave) "data center" '
                    '(opens OR "breaks ground" OR announces OR expands)', None),
]


def log(msg):
    """Print a progress line immediately."""
    print(msg, flush=True)


def day(s):
    """A YYYY-MM-DD string, or 'today', as a date."""
    return date.today() if s == "today" else date.fromisoformat(s)


def archive_ids():
    """Every headline id already in data/archive, so a window's new headlines can be counted."""
    ids = set()
    for p in fn.ARCHIVE_DIR.glob("*.json"):
        if fn.MONTH_RE.match(p.stem):
            ids.update(x["id"] for x in fn.load_json(p, {}).get("items", []))
    return ids


def registry_snapshot():
    """Counts of the registry before the backfill (records, statuses, confidence, ids) for the report."""
    recs = [r for r in rg.load().values()]
    vis = [r for r in recs if not r.get("hidden")]
    count = lambda key: {k: sum(1 for r in vis if r.get(key) == k) for k in sorted({r.get(key) for r in vis})}
    return {"taken": datetime.now(timezone.utc).isoformat(timespec="seconds"), "count": len(recs), "visible": len(vis),
            "ids": sorted(r["id"] for r in recs), "status": count("status"), "confidence": count("confidence"),
            "news_ids": sorted({n["id"] for r in recs for n in r["news"]})}


def load_progress(args):
    """The saved progress for a resumed run with the same start, end and window, or a fresh one."""
    old = fn.load_json(PROGRESS_FILE, {})
    same = old.get("start") == args.start and old.get("end") == str(args.end) and old.get("window_days") == args.window_days
    if args.resume and same:
        return old
    prog = {"start": args.start, "end": str(args.end), "window_days": args.window_days, "next": args.start, "done": False,
            "windows_done": 0, "requests": 0, "failed_requests": 0, "consecutive_failures": 0,
            "fetched": 0, "passed": 0, "added": 0, "months": {}, "windows": [],
            # The registry and archive as they were before the first backfill run ever; kept across runs.
            "baseline": old.get("baseline") or {"registry": registry_snapshot(), "archive_ids": len(archive_ids())}}
    return prog


def save_progress(prog):
    """Write data/backfill_progress.json with the time it was saved."""
    prog["updated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    prog["_readme"] = fn.readme("backfill_progress.json")
    PROGRESS_FILE.write_text(json.dumps(prog, indent=1) + "\n", encoding="utf-8")


def fetch(url, prog, feed_file=None):
    """One polite request. Returns parsed entries or None on failure."""
    prog["requests"] += 1
    if feed_file:
        parsed = feedparser.parse(Path(feed_file).read_bytes())
    else:
        time.sleep(random.uniform(*DELAY))
        parsed = fn.fetch_feed(url)  # 3 tries with exponential backoff on 429, 5xx and network errors
    if parsed is None:
        prog["failed_requests"] += 1
        prog["consecutive_failures"] += 1
        return None
    prog["consecutive_failures"] = 0
    return parsed.entries


def run_window(a, b, prog, known, gaz, geo, feed_file=None):
    """Fetch every query for [a, b). Returns the new tagged headlines, or None if requests keep failing."""
    now = datetime.now(timezone.utc)
    month = a.strftime("%Y-%m")
    stats, new = {}, []
    def ask(name, query, lo, hi, st):
        """Run one query for one date window; returns the entries, or None when the feed failed."""
        url = fn.google_news_url(f"after:{lo.isoformat()} before:{hi.isoformat()} {query}")
        entries = fetch(url, prog, feed_file)
        if entries is None:
            log(f"    {name} {lo}..{hi}: request failed ({prog['consecutive_failures']} in a row)")
            return prog["consecutive_failures"] < MAX_CONSECUTIVE_FAILURES
        if len(entries) >= RESULT_CAP and (hi - lo).days > 1 and not feed_file:
            mid = lo + timedelta(days=(hi - lo).days // 2)
            st["split"] += 1
            return ask(name, query, lo, mid, st) and ask(name, query, mid, hi, st)
        st["capped"] += len(entries) >= RESULT_CAP
        st["fetched"] += len(entries)
        lo_ok, hi_ok = (lo - timedelta(days=7)).isoformat(), (hi + timedelta(days=7)).isoformat()
        for e in entries:
            item = fn.entry_to_item(e, "Backfill: " + name, now, gaz, geo, max_age_days=None)
            if not item:
                continue
            st["passed"] += 1
            # Google does not apply the date operators strictly; keep only headlines within a week of the window.
            if not (lo_ok <= item["published"][:10] < hi_ok):
                st["out_of_window"] += 1
                continue
            if item["id"] in known:
                continue
            known.add(item["id"])
            new.append(item)
            st["new"] += 1
        return True

    for name, query, sub_days in QUERIES:
        st = stats.setdefault(name, {"fetched": 0, "passed": 0, "new": 0, "out_of_window": 0, "split": 0, "capped": 0})
        step = timedelta(days=sub_days or (b - a).days)
        lo = a
        while lo < b:
            hi = min(lo + step, b)
            if not ask(name, query, lo, hi, st):
                return None, stats
            lo = hi
    m = prog["months"].setdefault(month, {})
    for name, st in stats.items():
        acc = m.setdefault(name, {})
        for k, v in st.items():
            acc[k] = acc.get(k, 0) + v
    return new, stats


def main():
    """Fetch every window from start to end for each backfill query, archive what is new and save
    progress; exits 10 after --max-windows windows so the workflow can commit and continue.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--start", default="2024-10-01")
    ap.add_argument("--end", default="today")
    ap.add_argument("--window-days", type=int, default=14)
    ap.add_argument("--resume", action="store_true", help="continue from data/backfill_progress.json")
    ap.add_argument("--max-windows", type=int, default=0, help="stop after this many windows (exit 10 if more remain)")
    ap.add_argument("--feed-file", help=argparse.SUPPRESS)  # offline testing: answer every query with this RSS file
    args = ap.parse_args()
    args.end = day(args.end)

    prog = load_progress(args)
    if prog.get("done"):
        log(f"Backfill {prog['start']} to {prog['end']} is already complete.")
        return 0
    gaz, geo = fn.load_gazetteer()
    known = archive_ids()
    cur, end = date.fromisoformat(prog["next"]), args.end
    first = date.fromisoformat(prog["start"])
    log(f"Backfill {prog['start']} to {end} in {args.window_days}-day windows, resuming at {cur}; archive holds {len(known)} headlines")
    chunk, windows = [], 0
    while cur < end:
        nxt = min(cur + timedelta(days=args.window_days), end)
        new, stats = run_window(cur, nxt, prog, known, gaz, geo, args.feed_file)
        if new is None:
            save_progress(prog)
            log(f"STOP: {MAX_CONSECUTIVE_FAILURES} requests in a row failed at window {cur}. Progress saved; re-run with --resume.")
            return 2
        fn.cluster_items(new)
        added = fn.archive_items(new, fn.ARCHIVE_DIR)
        chunk += new
        fetched = sum(s["fetched"] for s in stats.values())
        passed = sum(s["passed"] for s in stats.values())
        prog["fetched"] += fetched
        prog["passed"] += passed
        prog["added"] += added
        prog["windows"].append({"start": cur.isoformat(), "end": nxt.isoformat(), "fetched": fetched, "passed": passed, "added": added,
                                "queries": stats})
        prog["windows_done"] += 1
        prog["next"] = nxt.isoformat()
        save_progress(prog)
        log(f"  {cur}..{nxt}: fetched {fetched}, passed {passed}, archived {added}  " +
            "  ".join(f"{k} {v['fetched']}/{v['passed']}/{v['new']}" + (f" (split {v['split']}, capped {v['capped']})" if v["split"] or v["capped"] else "")
                      for k, v in stats.items()))
        windows += 1
        cur = nxt
        # The date operators must work: if the whole first month came back empty, stop.
        if (cur - first).days >= TEST_DAYS or cur >= end:
            first_month = [w for w in prog["windows"] if date.fromisoformat(w["start"]) < first + timedelta(days=TEST_DAYS)]
            if first_month and sum(w["fetched"] for w in first_month) == 0:
                save_progress(prog)
                log("STOP: Google News returned nothing for every window of the first month with after:/before: date "
                    "operators. Not trying any other source; check the queries by hand.")
                return 3
        if args.max_windows and windows >= args.max_windows and cur < end:
            break

    # Attach this chunk's headlines to the registry (hourly rules, published-date order) and rebuild pages.
    if chunk:
        records = rg.update(chunk, gaz, log=log)
        rg.build_pages(records, log=log)
    if cur >= end:
        prog["done"] = True
        save_progress(prog)
        log(f"Backfill complete: {prog['windows_done']} windows, {prog['requests']} requests, "
            f"{prog['fetched']} fetched, {prog['passed']} passed the filters, {prog['added']} added to the archive")
        return 0
    log(f"Stopped after {windows} windows; next window starts {cur}. Re-run with --resume.")
    return 10


if __name__ == "__main__":
    sys.exit(main())
