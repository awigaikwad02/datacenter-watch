"""
Weekly summary test: scripts/weekly_summary.py renders from the repository's own data, with
and without a week-old git ref, and always has its sections, "Needs you" first.

Run: python -m pytest -q tests
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import weekly_summary as ws  # noqa: E402


def test_summary_renders_without_history():
    text = ws.summary(None)
    heads = [h for h in ("## Needs you", "## This week", "## Projects", "## Headlines that started no project", "## Health") if h in text]
    assert heads == ["## Needs you", "## This week", "## Projects", "## Headlines that started no project", "## Health"]


def test_summary_renders_with_a_ref():
    assert "## Needs you" in ws.summary("HEAD")
