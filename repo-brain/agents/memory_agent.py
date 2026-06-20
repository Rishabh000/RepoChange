"""Memory agent.

For each file in the repo: read it, summarize it with Gemini (required), and
store the summary + content in semantic memory through the Memory MCP. This
builds the searchable "second brain".
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "mcp"))

import filesystem_server as fs  # noqa: E402
import memory_server  # noqa: E402
import llm  # noqa: E402
from config import is_protected  # noqa: E402

_TEXT_EXT = {".md", ".txt", ".rst", ".py", ".js", ".ts", ".json", ".yaml",
             ".yml", ".csv", ".toml", ".cfg", ".ini", ".sh", ".go", ".rs"}


def _summarize(name: str, content: str) -> str:
    """Summarize a file in two sentences using Gemini."""
    if not content.strip():
        return f"{name}: (empty file)"
    return llm.generate(
        f"Summarize this file in 2 sentences.\n\nFile: {name}\n\n{content[:6000]}"
    )


def _iter_files(path: str = "."):
    """Yield (relative_path, name) for every text file, recursing into folders."""
    for entry in fs.list_files(path):
        if entry["protected"] or entry.get("ignored") or is_protected(entry["path"]):
            continue
        if entry["is_dir"]:
            yield from _iter_files(entry["path"])
            continue
        if Path(entry["name"]).suffix.lower() in _TEXT_EXT:
            yield entry["path"], entry["name"]


def index_repo() -> list[dict]:
    """Summarize and store every text file. Returns what was indexed."""
    indexed = []
    for rel_path, name in _iter_files("."):
        content = fs.read_file(rel_path)
        summary = _summarize(name, content)
        memory_server.remember(file=rel_path, summary=summary, content=content)
        indexed.append({"file": rel_path, "summary": summary})
    return indexed


if __name__ == "__main__":
    import json

    print(json.dumps(index_repo(), indent=2))
