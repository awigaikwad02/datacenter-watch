"""
Documentation tests: every field in the data files is described, and the docs the README
promises exist and are linked.

scripts/data_readme.py describes every file and field (and generates docs/DATA_DICTIONARY.md).
A field that appears in the data without a description fails here, so the dictionary never
falls behind the code.

Run: python -m pytest -q tests
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import data_readme as dr  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def keys(path):
    return {k for k in json.loads(path.read_text(encoding="utf-8")) if not k.startswith("_")}


def test_top_level_fields_described():
    for name, f in dr.FILES.items():
        path = ROOT / f["path"]
        if "(" in f["path"] or "YYYY" in f["path"] or not path.exists() or name in ("gazetteer.json",):
            continue
        missing = keys(path) - set(f["fields"])
        assert not missing, f"{f['path']}: describe {sorted(missing)} in scripts/data_readme.py"


def test_headline_fields_described():
    seen = set()
    for p in sorted((DATA / "archive").glob("2*.json")):
        for it in json.loads(p.read_text(encoding="utf-8"))["items"]:
            seen |= set(it)
    for it in json.loads((DATA / "news.json").read_text(encoding="utf-8"))["items"]:
        seen |= set(it)
    assert not seen - set(dr.HEADLINE), f"describe {sorted(seen - set(dr.HEADLINE))} in data_readme.HEADLINE"


def test_registry_record_fields_described():
    seen = set()
    for r in json.loads((DATA / "registry.json").read_text(encoding="utf-8"))["records"]:
        seen |= set(r)
    described = set(dr.FILES["registry record fields"]["fields"])
    assert not seen - described, f"describe {sorted(seen - described)} in data_readme.FILES['registry record fields']"


def test_data_dictionary_is_current():
    path = ROOT / "docs" / "DATA_DICTIONARY.md"
    assert path.read_text(encoding="utf-8") == dr.dictionary(), "run: python scripts/data_readme.py"


def test_readme_links_the_docs():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for doc in ("ARCHITECTURE.md", "DATA_DICTIONARY.md", "RUNBOOK.md", "DECISIONS.md", "CONTRIBUTING.md"):
        assert (ROOT / "docs" / doc).exists(), doc
        assert f"docs/{doc}" in readme, f"README.md should link docs/{doc}"


def test_ground_rule_is_written_down():
    for doc in ("README.md", "docs/DECISIONS.md"):
        text = (ROOT / doc).read_text(encoding="utf-8")
        assert re.search(r"no (AI|artificial intelligence)", text, re.I) and "GITHUB_TOKEN" in text, doc
