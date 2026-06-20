"""Organizer agent.

Role: a repository architect. It inspects the files in the target repo and
returns a JSON plan classifying each into one of: docs/ src/ tests/ data/
archive/. It NEVER moves files itself - it only proposes a plan. The CLI applies
the plan after a dry-run + human approval, going through the Filesystem MCP.

Classification is done by Gemini (required). Protected and tool/ignored paths
are filtered out as defense in depth, regardless of what the model returns.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "mcp"))

import filesystem_server as fs  # noqa: E402
import llm  # noqa: E402
from config import is_protected, is_ignored  # noqa: E402

PROMPT = """You are a repository architect.
Classify each file into exactly one of: docs/ src/ tests/ data/ archive/.
- docs: documentation, notes, design (.md, .txt, .rst, .pdf)
- src: source code (.py, .js, .ts, .go ...) that is NOT a test
- tests: test files (test_*, *_test, files under tests)
- data: structured data (.json, .csv, .yaml, .parquet ...)
- archive: deprecated/old/temporary files
Return JSON only, shaped exactly like:
{"moves":[{"source":"a.md","destination":"docs/a.md","reason":"documentation"}]}
Do not include files that are already correctly placed.
"""


def _parse_plan(text: str) -> dict:
    """Parse the model's JSON response, tolerating code fences."""
    text = text.strip()
    if text.startswith("```"):
        # Strip a ```json ... ``` fence.
        inner = text.split("```", 2)
        text = inner[1] if len(inner) > 1 else text
        text = text.lstrip("json").strip()
    return json.loads(text)


def make_plan() -> dict:
    """Produce the organization plan for the target repo using Gemini."""
    files = fs.list_files(".")
    candidates = [e["name"] for e in files
                  if not e["is_dir"] and not e["protected"] and not e.get("ignored")]

    if not candidates:
        return {"moves": []}

    prompt = PROMPT + "\n\nFiles:\n" + "\n".join(candidates)
    response = llm.generate(prompt)
    plan = _parse_plan(response)

    # Defense in depth: never move protected or tool/ignored paths, and only
    # accept moves whose source is an actual candidate file.
    allowed = set(candidates)
    plan["moves"] = [
        m for m in plan.get("moves", [])
        if m.get("source") in allowed
        and not is_protected(m["source"]) and not is_protected(m["destination"])
        and not is_ignored(m["source"]) and not is_ignored(m["destination"])
    ]
    return plan


if __name__ == "__main__":
    print(json.dumps(make_plan(), indent=2))
