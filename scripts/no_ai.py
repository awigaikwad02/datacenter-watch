#!/usr/bin/env python3
"""
The Rack Report: enforce the "no AI in the pipeline" ground rule.

What it is for: the site must keep updating, tagging and deciding everything with plain,
deterministic code that GitHub Actions runs on its own (docs/DECISIONS.md, decision 2). This
module finds anything that would break that rule:

  - an import of an AI or LLM SDK (anthropic, openai, google.generativeai, and their JS packages)
  - a call to a model API host (api.anthropic.com, api.openai.com, generativelanguage.googleapis.com)
  - an API key name (ANTHROPIC_API_KEY, OPENAI_API_KEY, any *_API_KEY, an x-api-key header)
  - an AI package in scripts/requirements.txt or package.json
  - a workflow that uses a secret other than GITHUB_TOKEN

Company names are fine: OpenAI and Anthropic are tracked data center companies, so the words
alone are not flagged; only SDK imports, API hosts, keys and secrets are.

Used by: scripts/healthcheck.py (check "No AI services or API keys") and tests/test_no_ai.py.
Run on its own:  python scripts/no_ai.py   (prints findings, exits 1 if there are any)
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Files that describe the rule (and so contain the patterns) are not scanned.
SELF = {"scripts/no_ai.py", "tests/test_no_ai.py"}
CODE_SUFFIXES = (".py", ".js", ".mjs", ".sh", ".yml", ".yaml", ".html")

AI_CODE = re.compile(
    r"^\s*(import|from)\s+(anthropic|openai|google\.generativeai|google\.genai|langchain\w*|litellm|cohere|mistralai)\b"
    r"|require\(\s*['\"](@anthropic-ai/[\w-]+|openai|@google/generative-ai|@google/genai)['\"]"
    r"|from\s+['\"](@anthropic-ai/[\w-]+|openai|@google/generative-ai|@google/genai)['\"]"
    r"|api\.anthropic\.com|api\.openai\.com|generativelanguage\.googleapis\.com"
    r"|\b[A-Z][A-Z0-9_]*_API_KEY\b|x-api-key",
    re.I | re.M)
AI_PACKAGE = re.compile(r"^\s*['\"]?(anthropic|openai|google-generativeai|google-genai|langchain[\w-]*|litellm|cohere|mistralai"
                        r"|@anthropic-ai/[\w-]+|@google/generative-ai)\b", re.I | re.M)
# In package.json a dependency is a quoted key anywhere in the file: "openai": "^4.0.0"
AI_NPM = re.compile(r"[\"'](openai|@anthropic-ai/[\w-]+|@google/generative-ai|@google/genai|langchain[\w-]*|@langchain/[\w-]+|"
                    r"cohere-ai|@mistralai/[\w-]+|ai)[\"']\s*:", re.I)
SECRET_USE = re.compile(r"secrets\.([A-Za-z_][A-Za-z0-9_]*)")


def tracked_files(root=ROOT):
    """Files git tracks, or every file under root when git is not available."""
    r = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True)
    if r.returncode == 0:
        return [f for f in r.stdout.splitlines() if f]
    return [str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() and ".git" not in p.parts]


def findings(root=ROOT):
    """Every place that breaks the rule, as "path:line: reason" strings (empty list = clean)."""
    out = []
    for f in tracked_files(root):
        if f in SELF or f.startswith(("data/", "projects/", "node_modules/")):
            continue
        p = root / f
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if f.endswith(CODE_SUFFIXES):
            for m in AI_CODE.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                out.append(f"{f}:{line}: AI SDK, model API or API key reference ({m.group(0).strip()[:40]})")
        if Path(f).name == "requirements.txt":
            for m in AI_PACKAGE.finditer(text):
                out.append(f"{f}: AI package {m.group(1)}")
        if Path(f).name == "package.json":
            for m in AI_NPM.finditer(text):
                out.append(f"{f}: AI package {m.group(1)}")
        if f.startswith(".github/workflows/"):
            for m in SECRET_USE.finditer(text):
                if m.group(1) != "GITHUB_TOKEN":
                    line = text.count("\n", 0, m.start()) + 1
                    out.append(f"{f}:{line}: uses secret {m.group(1)} (only GITHUB_TOKEN is allowed)")
    return out


if __name__ == "__main__":
    found = findings()
    print("\n".join(found) or "No AI services, API keys or extra secrets found.")
    sys.exit(1 if found else 0)
