"""ADK Coordinator.

Two things live here:

1. build_adk_pipeline(): constructs a real google-adk SequentialAgent wiring the
   organizer -> auditor -> memory agents as ADK sub-agents. This satisfies the
   ADK structural requirement and can be served/run when an API key is present.

2. run_pipeline(): the concrete orchestration the CLI executes. It runs the same
   logical workflow (organize -> audit + git commit -> memory index) and works
   fully offline so the demo is reliable.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "agents"))
sys.path.insert(0, str(ROOT / "mcp"))

import organizer  # noqa: E402
import auditor  # noqa: E402
import memory_agent  # noqa: E402
import filesystem_server as fs  # noqa: E402
from config import MODEL  # noqa: E402


def build_adk_pipeline():
    """Build the ADK SequentialAgent (organizer -> auditor -> memory).

    Returns the root agent, or None if google-adk is not importable in a
    compatible way. Kept import-guarded so the offline pipeline never breaks.
    """
    try:
        from google.adk.agents import LlmAgent, SequentialAgent
        from google.adk.tools import FunctionTool
    except Exception as exc:  # pragma: no cover
        print(f"[coordinator] ADK unavailable: {exc}", file=sys.stderr)
        return None

    model = MODEL

    organizer_agent = LlmAgent(
        name="organizer",
        model=model,
        instruction=organizer.PROMPT,
        tools=[FunctionTool(fs.list_files)],
    )
    auditor_agent = LlmAgent(
        name="auditor",
        model=model,
        instruction="Record every move action to the audit log, then commit via git.",
        tools=[FunctionTool(auditor.record), FunctionTool(auditor.commit)],
    )
    memory_agent_node = LlmAgent(
        name="memory",
        model=model,
        instruction="Summarize each file and store it in semantic memory.",
        tools=[FunctionTool(memory_agent.index_repo)],
    )

    return SequentialAgent(
        name="repo_brain_coordinator",
        sub_agents=[organizer_agent, auditor_agent, memory_agent_node],
    )


# Exposed for `adk web` / `adk run` discovery when a key is configured.
root_agent = None
try:  # pragma: no cover
    root_agent = build_adk_pipeline()
except Exception:
    root_agent = None


def run_pipeline(dry_run: bool = True, auto: bool = False, approver=None) -> dict:
    """Run organize -> audit/commit -> memory.

    - dry_run: only print/return the plan, change nothing.
    - auto: skip the interactive approval (used by cron).
    - approver: callable(plan) -> bool used to ask the human. If None and not
      auto, approval defaults to False (safe).
    """
    plan = organizer.make_plan()
    moves = plan.get("moves", [])

    result = {"plan": plan, "applied": False, "moved": [], "commit": None, "indexed": []}

    if dry_run:
        return result

    if not moves:
        return result

    approved = True if auto else (approver(plan) if approver else False)
    if not approved:
        result["applied"] = False
        return result

    # Apply moves through the Filesystem MCP (never shutil directly).
    moved = []
    for move in moves:
        outcome = fs.move_file(move["source"], move["destination"])
        moved.append(outcome)
    result["moved"] = moved

    # Audit + git commit (tracking layer).
    auditor.record_moves(moves)
    result["commit"] = auditor.commit("AI Cleanup: organized repository")

    # Build/refresh semantic memory.
    result["indexed"] = memory_agent.index_repo()
    result["applied"] = True
    return result
