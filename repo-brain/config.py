"""Shared configuration for repo-brain.

Central place for paths and the protected-paths security policy.
"""
from __future__ import annotations

import os
from pathlib import Path

# Project root = the directory containing this file (repo-brain/).
ROOT = Path(__file__).resolve().parent

# The repository that the agents organize. Defaults to the parent repo
# (RepoChange), since repo-brain lives inside it. Override with REPO_BRAIN_TARGET
# to point at any other repository.
TARGET_REPO = Path(os.environ.get("REPO_BRAIN_TARGET", ROOT.parent)).resolve()

# Storage locations.
MEMORY_DIR = ROOT / "memory"
CHROMA_DIR = MEMORY_DIR / "chroma"
LOGS_DIR = ROOT / "logs"
AUDIT_LOG = LOGS_DIR / "audit.jsonl"

# Canonical destination buckets the organizer sorts files into.
CATEGORIES = ("docs", "src", "tests", "data", "archive")

# Gemini model used by the agents. Override with REPO_BRAIN_MODEL.
MODEL = os.environ.get("REPO_BRAIN_MODEL", "gemini-3.1-flash-lite")

# Phase 9 - Protected paths. Any path whose name OR any path component matches
# one of these is never moved, renamed, or deleted by an agent.
PROTECTED = (
    ".env",
    ".git",
    "secrets",
    "credentials",
)

# Ignored paths: infrastructure and the tool's own files. These are not
# sensitive, but they are not "content" to organize or index either. The
# organizer skips them, the memory agent does not recurse into them, and the
# filesystem layer refuses to move them. This is what lets repo-brain run
# safely *inside* the repository it manages (RepoChange) without touching
# itself or its virtualenv.
IGNORE = (
    "repo-brain",
    ".venv",
    "__pycache__",
    ".DS_Store",
    ".gitignore",
    "README.md",
)


def is_ignored(path: str | os.PathLike) -> bool:
    """Return True if a path is tool/infrastructure rather than content."""
    p = Path(path)
    parts = set(p.parts) | {p.name}
    return any(token in parts for token in IGNORE)


def is_protected(path: str | os.PathLike) -> bool:
    """Return True if a path touches a protected file or directory.

    Matches on the basename and on any individual path component so that, for
    example, ``secrets/key.pem`` and ``.git/config`` are both protected.
    """
    p = Path(path)
    parts = set(p.parts) | {p.name}
    for token in PROTECTED:
        if token in parts:
            return True
        # Also guard files like ".env.local" or "my.credentials".
        if p.name == token or p.name.startswith(token + ".") or token in p.name.split("."):
            return True
    return False


def ensure_dirs() -> None:
    """Create the runtime directories if they do not exist."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
