"""Auditor agent.

Records every action the system takes as a JSON line in logs/audit.jsonl, then
commits the change set through the Git MCP so there is a durable, reviewable
history. Nothing mutates the repo without leaving an audit trail.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "mcp"))

import git_server  # noqa: E402
from config import AUDIT_LOG, ensure_dirs  # noqa: E402


def record(action: str, **fields) -> dict:
    """Append a single audit entry and return it."""
    ensure_dirs()
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        **fields,
    }
    with open(AUDIT_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    return entry


def record_moves(moves: list[dict]) -> list[dict]:
    """Record a batch of move actions from an organizer plan."""
    entries = []
    for move in moves:
        entries.append(record(
            "move",
            source=move.get("source"),
            destination=move.get("destination"),
            reason=move.get("reason", ""),
        ))
    return entries


def commit(message: str) -> dict:
    """Commit the current repo state via the Git MCP (the tracking layer)."""
    result = git_server.commit_changes(message)
    record("commit", message=message, result=result)
    return result


def read_log(limit: int | None = None) -> list[dict]:
    """Read back audit entries (most recent last)."""
    if not Path(AUDIT_LOG).exists():
        return []
    lines = Path(AUDIT_LOG).read_text(encoding="utf-8").splitlines()
    if limit:
        lines = lines[-limit:]
    return [json.loads(line) for line in lines if line.strip()]
