"""
Ground-rule tests: the site never depends on an AI or LLM service (docs/DECISIONS.md, decision 1).

The first test scans the real repository with scripts/no_ai.py and must find nothing. The others
plant violations in a throwaway folder to prove the scanner catches each kind: an SDK import, a
model API host, an API key name, an AI package in requirements.txt, and a workflow secret other
than GITHUB_TOKEN. Company names alone (OpenAI and Anthropic are tracked operators) are fine.

Run: python -m pytest -q tests
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import no_ai  # noqa: E402


def test_repository_is_clean():
    assert no_ai.findings() == []


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A folder that no_ai scans file by file (no git), with a clean script in it."""
    monkeypatch.setattr(no_ai, "tracked_files", lambda root: [str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()])
    (tmp_path / "scripts").mkdir()
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / "scripts" / "ok.py").write_text('COMPANIES = [("OpenAI", r"OpenAI|ChatGPT"), ("Anthropic", r"Anthropic")]\n')
    return tmp_path


def test_company_names_are_allowed(repo):
    assert no_ai.findings(repo) == []


@pytest.mark.parametrize("path,text", [
    ("scripts/a.py", "import anthropic\n"),
    ("scripts/b.py", "from openai import OpenAI\n"),
    ("scripts/c.py", "import google.generativeai as genai\n"),
    ("scripts/d.py", 'key = os.environ["ANTHROPIC_API_KEY"]\n'),
    ("scripts/e.py", 'requests.post("https://api.openai.com/v1/chat/completions")\n'),
    ("assets/f.js", 'const Anthropic = require("@anthropic-ai/sdk");\n'),
    ("assets/g.js", 'fetch(url, { headers: { "x-api-key": k } });\n'),
    ("scripts/requirements.txt", "feedparser>=6.0\nopenai>=1.0\n"),
    ("package.json", '{"dependencies": {"@anthropic-ai/sdk": "^0.30.0"}}\n'),
    (".github/workflows/x.yml", "env:\n  KEY: ${{ secrets.OPENAI_KEY }}\n"),
])
def test_violation_is_caught(repo, path, text):
    p = repo / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    assert no_ai.findings(repo), f"{path} should be flagged"


def test_github_token_is_the_one_allowed_secret(repo):
    (repo / ".github" / "workflows" / "ok.yml").write_text("env:\n  GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}\n")
    assert no_ai.findings(repo) == []
