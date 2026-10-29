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
    """run(headlines, overrides=[]) -> records. headlines: (title, days_ago) pairs, each run separately
    in date order like successive hourly runs; the registry file persists between calls."""
    (tmp_path / "projects.json").write_text('{"projects": []}')
    monkeypatch.setattr(reg, "PROJECTS_FILE", tmp_path / "projects.json")
    monkeypatch.setattr(reg, "OVERRIDES_FILE", tmp_path / "overrides.json")
    path = tmp_path / "registry.json"

    def _run(headlines, overrides=()):
        (tmp_path / "overrides.json").write_text(json.dumps({"operations": list(overrides)}))
        items = []
        for title, days in headlines:
            it = {"id": fn.make_id(title), "title": title, "link": "https://example.com/" + fn.make_id(title),
                  "source": "Test Journal", "published": (NOW - timedelta(days=days)).isoformat(timespec="seconds")}
            assert fn.tag_item(it, GAZ, GEO), title
            it["cluster_id"] = it["id"]
            items.append(it)
        records = None
        for it in sorted(items, key=lambda x: x["published"]) or [None]:
            records = reg.update([it] if it else [], GAZ, registry_in=path, registry_out=path, log=lambda *_: None)
        return records

    return _run


def live(records):
    return [r for r in records.values() if not r.get("hidden")]


def only(records):
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
