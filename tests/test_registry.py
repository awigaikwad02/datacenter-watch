"""
Registry tests: how scripts/registry.py turns headlines into permanent project records.

Each test runs registry.update() on a few tagged headlines in a temporary folder, with no curated
projects and its own overrides, exactly as the hourly run does. Covered: the status lifecycle,
never moving backward, cancellation and revival, merges and splits from overrides, an umbrella
("Amazon, Texas (site not yet named)") folding into a named site, builder-only headlines, project
name hints, and that no record is ever deleted.

Run: python -m pytest -q tests
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import fetch_news as fn  # noqa: E402
import registry as reg  # noqa: E402

GAZ, GEO = fn.load_gazetteer()
NOW = datetime.now(timezone.utc)


@pytest.fixture
def run(tmp_path, monkeypatch):
    """run(headlines, overrides=[]) -> records. headlines: (title, days_ago[, outlet]) tuples, each run separately
    in date order like successive hourly runs; the registry file persists between calls."""
    (tmp_path / "projects.json").write_text('{"projects": []}')
    monkeypatch.setattr(reg, "PROJECTS_FILE", tmp_path / "projects.json")
    monkeypatch.setattr(reg, "OVERRIDES_FILE", tmp_path / "overrides.json")
    path = tmp_path / "registry.json"

    def _run(headlines, overrides=()):
        """Tag the headlines and run the registry once per headline in date order; returns the records."""
        (tmp_path / "overrides.json").write_text(json.dumps({"operations": list(overrides)}))
        items = []
        for h in headlines:
            title, days, source = (h + ("Test Journal",))[:3]
            it = {"id": fn.make_id(title), "title": title, "link": "https://example.com/" + fn.make_id(title),
                  "source": source, "published": (NOW - timedelta(days=days)).isoformat(timespec="seconds")}
            assert fn.tag_item(it, GAZ, GEO), title
            it["cluster_id"] = it["id"]
            items.append(it)
        records = None
        for it in sorted(items, key=lambda x: x["published"]) or [None]:
            records = reg.update([it] if it else [], GAZ, registry_in=path, registry_out=path, log=lambda *_: None)
        return records

    return _run


def live(records):
    """Records that are not hidden."""
    return [r for r in records.values() if not r.get("hidden")]


def only(records):
    """The one visible record that has headlines (fails the test when there are several)."""
    rs = [r for r in live(records) if r["news"]]
    assert len(rs) == 1, [r["id"] for r in rs]
    return rs[0]


def test_lifecycle_announced_construction_operational(run):
    r = only(run([("AWS announces North Carolina data center campus in Richmond County", 14),
                  ("AWS breaks ground on Richmond County, North Carolina data center", 7),
                  ("AWS opens Richmond County, North Carolina data center", 1)]))
    assert [h["status"] for h in r["status_history"]] == ["Announced", "Under construction", "Operational"]
    assert r["status"] == "Operational" and len(r["news"]) == 3


def test_selftest_matches():
    recs = reg.selftest()
    assert len(recs) == 1 and recs[0]["status"] == "Operational"


def test_status_never_moves_backward(run):
    r = only(run([("AWS opens Richmond County, North Carolina data center", 20),
                  ("AWS announces expansion plans for Richmond County, North Carolina data center", 5),
                  ("AWS plans more buildings at Richmond County, North Carolina data center campus", 2)]))
    assert r["status"] == "Operational"
    assert [h["status"] for h in r["status_history"]] == ["Operational"]


def test_cancelled_then_revived_by_construction(run):
    r = only(run([("Google announces data center in Botetourt County, Virginia", 30),
                  ("Google withdraws plans for Botetourt County, Virginia data center", 20),
                  ("Google breaks ground on Botetourt County, Virginia data center", 3)]))
    assert [h["status"] for h in r["status_history"]] == ["Announced", reg.CANCELLED, "Under construction"]
    assert [e["type"] for e in r["events"] if e["type"] in ("Cancelled", "Revived")] == ["Cancelled", "Revived"]


def test_announcement_does_not_revive_a_cancelled_project(run):
    r = only(run([("Google withdraws plans for Botetourt County, Virginia data center", 20),
                  ("Google announces data center in Botetourt County, Virginia", 3)]))
    assert r["status"] == reg.CANCELLED


def test_future_groundbreaking_is_not_construction(run):
    r = only(run([("Google announces data center in Botetourt County, Virginia", 30),
                  ("Google could break ground on Botetourt County, Virginia data center this summer", 3)]))
    assert r["status"] == "Announced"


def test_merge_override_moves_news_and_keeps_both_ids(run):
    recs = run([("Google announces data center in Botetourt County, Virginia", 30),
                ("Amazon announces data center in Louisa County, Virginia", 20)])
    g = next(r for r in live(recs) if "Google" in r["companies"])
    a = next(r for r in live(recs) if "Amazon" in r["companies"])
    recs = run([], overrides=[{"op": "merge", "from": a["id"], "into": g["id"]}])
    assert recs[a["id"]]["hidden"] and recs[a["id"]]["merged_into"] == g["id"] and recs[a["id"]]["news"] == []
    assert len(recs[g["id"]]["news"]) == 2


def test_split_override_creates_record_with_its_own_operator(run):
    recs = run([("Google announces data center in Botetourt County, Virginia", 30),
                ("Google breaks ground on Botetourt County, Virginia data center", 10)])
    r = only(recs)
    moving = [n["id"] for n in r["news"] if "breaks ground" in n["title"]]
    recs = run([], overrides=[{"op": "split", "id": r["id"], "headline_ids": moving, "new_id": "split-test"}])
    assert recs["split-test"]["news"][0]["id"] == moving[0] and recs["split-test"]["status"] == "Under construction"
    assert recs[r["id"]]["status"] == "Announced" and not recs["split-test"].get("umbrella")


def test_umbrella_folds_into_named_site(run):
    recs = run([("Amazon announces data center investment in Texas", 30)])
    u = only(recs)
    assert u.get("umbrella") and u["precision"] == "state"
    recs = run([("Amazon announces data center campus in Abilene, Texas", 2)])
    named = only(recs)
    assert named["id"] != u["id"] and named["precision"] == "city"
    assert recs[u["id"]]["hidden"] and recs[u["id"]]["merged_into"] == named["id"]
    assert len(named["news"]) == 2


def test_builder_only_headline_never_creates_a_project(run):
    recs = run([("Mortenson breaks ground on data center in Hermantown", 2)])
    assert not [r for r in live(recs) if r["news"]]


def test_builder_headline_joins_the_one_project_at_its_place(run):
    recs = run([("Google announces data center in Hermantown, Minnesota", 30),
                ("Mortenson breaks ground on data center in Hermantown, Minnesota", 2)])
    r = only(recs)
    assert len(r["news"]) == 2 and r["builders"] == ["Mortenson"] and r["status"] == "Under construction"


def test_name_hint_matches_across_headlines(run):
    recs = run([("Plans for $17 billion 'Project Sail' data center proposed for Coweta County, Georgia", 30),
                ("Commissioners approve Project Sail data center in Georgia", 5)])
    r = only(recs)
    assert len(r["news"]) == 2 and "Project Sail" in r["name_hints"]


def test_records_are_never_deleted(run):
    first = run([("Google announces data center in Botetourt County, Virginia", 30)])
    ids = set(first)
    later = run([("Amazon announces data center in Louisa County, Virginia", 1)],
                overrides=[{"op": "hide", "id": next(iter(ids))}])
    assert ids <= set(later)
    assert later[next(iter(ids))]["hidden"]


# ---- Anonymous records, creation guards, relocation (Kansas City, 2026-11-01) ----
KC = "KSHB 41 Kansas City"


def test_anonymous_headlines_with_close_figures_are_one_record(run):
    r = only(run([("$2 billion data center planned in Olathe, Kansas", 40),
                  ("$2.2 billion data center approved in Olathe, Kansas", 5)]))
    assert len(r["news"]) == 2


def test_figures_far_apart_keep_anonymous_records_apart(run):
    recs = run([("$2 billion data center planned in Olathe, Kansas", 40),
                ("$9 billion data center proposed in Olathe, Kansas", 5)])
    assert len([r for r in live(recs) if r["news"]]) == 2


def test_only_anonymous_record_in_town_takes_a_figureless_headline(run):
    r = only(run([("$1 billion data center proposed in Lenexa, Kansas", 40),
                  ("Data center plan in Lenexa, Kansas moves forward with new site plan", 5)]))
    assert len(r["news"]) == 2


def test_anonymous_headline_joins_operator_record_with_same_figure(run):
    r = only(run([("Nebius breaks ground on $150 billion data center in Independence, Missouri", 40, KC),
                  ("Independence approves $150 billion data center bonds for hyperscale project", 5, KC)]))
    assert len(r["news"]) == 2 and r["companies"] == ["Nebius"]


def test_anonymous_record_takes_the_operator_of_a_later_headline(run):
    r = only(run([("Independence approves hyperscale AI data center, issues $150 billion in bonds", 40, KC),
                  ("$150 billion Independence AI data center breaks ground, barricades protesters", 30, KC),
                  ("Nebius breaks ground on AI data center in Independence amid community opposition", 30, KC)]))
    assert len(r["news"]) == 3 and r["companies"] == ["Nebius"] and r["status"] == "Under construction"


def test_question_headline_never_starts_a_project(run):
    recs = run([("Kansas City proposes new $2 billion water treatment plant. Is it connected to data center development?", 5, KC)])
    assert not [r for r in live(recs) if r["news"]]


def test_body_weighing_a_restriction_joins_the_project_instead(run):
    recs = run([("Miami County Commission considers pause on data center construction following nearby $1B proposal", 40, KC)])
    assert not [r for r in live(recs) if r["news"]]
    r = only(run([("Rural Miami County, Kansas, residents respond to $1 billion data center proposal", 41, KC)]))
    assert r["location"] == "Miami County, Kansas, US"


def test_not_a_data_center_never_starts_a_project(run):
    recs = run([("Entergy breaks ground on $800 million substation to serve data center in Olathe, Kansas", 5)])
    assert not [r for r in live(recs) if r["news"]]


def test_policy_story_without_operator_or_name_starts_nothing(run):
    recs = run([("De Soto, Kansas, approves $700m data center", 5)])
    assert not [r for r in live(recs) if r["news"]]


def test_anonymous_record_names_are_distinct(run):
    recs = run([("$2 billion data center planned in Olathe, Kansas", 40),
                ("$9 billion data center proposed in Olathe, Kansas", 5)])
    names = sorted(r["name"] for r in live(recs) if r["news"])
    assert names[0] != names[1] and all("Olathe data center ($" in n and "proposed" in n for n in names)


def test_relocate_moves_record_and_logs_an_event():
    it = {"id": "h1", "title": "Data center planned in Liberty", "published": "2026-03-24T00:00:00+00:00",
          "locations": [{"name": "Liberty, Missouri, US", "lat": 39.2, "lon": -94.4, "precision": "city", "country": "US"}]}
    rec = {"id": "x", "name": "x", "location": "Kansas City, Missouri, US", "lat": 39.1, "lon": -94.58, "precision": "city",
           "news": [{"id": "h1", "title": it["title"], "published": it["published"]}], "companies": []}
    assert reg.relocate({"x": rec}, {"h1": it}) == 1
    assert rec["location"] == "Liberty, Missouri, US" and rec["location_events"][0]["type"] == "Moved to Liberty"
    assert reg.relocate({"x": rec}, {"h1": it}) == 0   # nothing more to do the second time


def test_set_location_override_is_never_moved_back():
    it = {"id": "h1", "title": "t", "published": "2026-03-24T00:00:00+00:00",
          "locations": [{"name": "Liberty, Missouri, US", "lat": 39.2, "lon": -94.4, "precision": "city", "country": "US"}]}
    rec = {"id": "x", "location": "Platte County, Missouri, US", "precision": "county", "location_locked": True,
           "news": [{"id": "h1", "title": "t", "published": it["published"]}]}
    assert reg.relocate({"x": rec}, {"h1": it}) == 0
