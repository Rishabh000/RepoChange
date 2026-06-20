"""Git MCP server.

Exposes git operations as MCP tools. This is the tracking layer: every batch of
agent changes is recorded as a commit so the whole history is auditable.

    commit_changes(message)
    show_log(limit)
    rollback_last_commit()
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import TARGET_REPO  # noqa: E402


class GitError(Exception):
    """Raised when a git operation fails."""


def _repo():
    """Open (or initialize) the git repo at TARGET_REPO."""
    from git import Repo, InvalidGitRepositoryError

    try:
        return Repo(TARGET_REPO)
    except InvalidGitRepositoryError:
        repo = Repo.init(TARGET_REPO)
        # Make sure there is an author identity for commits in CI/demo envs.
        with repo.config_writer() as cw:
            cw.set_value("user", "name", "repo-brain")
            cw.set_value("user", "email", "repo-brain@local")
        return repo


def commit_changes(message: str) -> dict:
    """Stage everything and create a commit. Returns the new commit hash."""
    repo = _repo()
    repo.git.add(A=True)
    if not repo.is_dirty(untracked_files=True) and repo.head.is_valid():
        return {"committed": False, "reason": "nothing to commit"}
    commit = repo.index.commit(message)
    return {
        "committed": True,
        "hash": commit.hexsha[:8],
        "message": message,
    }


def show_log(limit: int = 10) -> list[dict]:
    """Return the most recent commits (like ``git log --oneline``)."""
    repo = _repo()
    if not repo.head.is_valid():
        return []
    out = []
    for commit in repo.iter_commits(max_count=limit):
        out.append({
            "hash": commit.hexsha[:8],
            "message": commit.message.strip(),
            "author": commit.author.name,
            "timestamp": commit.committed_datetime.isoformat(),
        })
    return out


def rollback_last_commit() -> dict:
    """Undo the last commit, keeping the working tree (``git reset --soft``)."""
    repo = _repo()
    if not repo.head.is_valid():
        raise GitError("No commits to roll back")
    last = repo.head.commit
    repo.git.reset("--soft", "HEAD~1")
    return {"rolled_back": last.hexsha[:8], "message": last.message.strip()}


def _build_server():
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("repo-brain-git")
    server.tool()(commit_changes)
    server.tool()(show_log)
    server.tool()(rollback_last_commit)
    return server


if __name__ == "__main__":
    _build_server().run()
