"""Filesystem MCP server.

Exposes safe filesystem operations as MCP tools:
    list_files(path)
    read_file(path)
    create_folder(path)
    move_file(src, dst)

Design note for the demo: agents NEVER call ``shutil`` directly. Every mutation
goes Agent -> Filesystem MCP -> move_file(). All paths are confined to the
target repository and protected paths are rejected here, at the boundary.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

# Allow running both as a module and as a standalone script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import TARGET_REPO, is_protected, is_ignored  # noqa: E402


class FilesystemError(Exception):
    """Raised when a filesystem operation is rejected or fails."""


def _resolve(path: str) -> Path:
    """Resolve a user-supplied path and confine it to TARGET_REPO."""
    p = Path(path)
    if not p.is_absolute():
        p = TARGET_REPO / p
    p = p.resolve()
    # Confinement: refuse anything outside the target repository.
    if TARGET_REPO != p and TARGET_REPO not in p.parents:
        raise FilesystemError(f"Path escapes target repo: {path}")
    return p


def list_files(path: str = ".") -> list[dict]:
    """List files and folders under ``path`` (relative to the target repo)."""
    base = _resolve(path)
    if not base.exists():
        raise FilesystemError(f"Not found: {path}")
    entries = []
    for child in sorted(base.iterdir()):
        entries.append({
            "name": child.name,
            "path": str(child.relative_to(TARGET_REPO)),
            "is_dir": child.is_dir(),
            "protected": is_protected(child),
            "ignored": is_ignored(child.relative_to(TARGET_REPO)),
            "size": child.stat().st_size if child.is_file() else None,
        })
    return entries


def read_file(path: str, max_bytes: int = 200_000) -> str:
    """Return the text content of a file (truncated to ``max_bytes``)."""
    p = _resolve(path)
    if not p.is_file():
        raise FilesystemError(f"Not a file: {path}")
    data = p.read_bytes()[:max_bytes]
    return data.decode("utf-8", errors="replace")


def create_folder(path: str) -> dict:
    """Create a folder (and parents) inside the target repo."""
    p = _resolve(path)
    if is_protected(p):
        raise FilesystemError(f"Refusing to create protected path: {path}")
    p.mkdir(parents=True, exist_ok=True)
    return {"created": str(p.relative_to(TARGET_REPO))}


def move_file(src: str, dst: str) -> dict:
    """Move/rename a file inside the target repo, honoring protected paths."""
    s = _resolve(src)
    d = _resolve(dst)
    if is_protected(s) or is_protected(d):
        raise FilesystemError(f"Refusing to move protected path: {src} -> {dst}")
    rel_s = s.relative_to(TARGET_REPO) if s != TARGET_REPO else s
    rel_d = d.relative_to(TARGET_REPO) if d != TARGET_REPO else d
    if is_ignored(rel_s) or is_ignored(rel_d):
        raise FilesystemError(f"Refusing to move tool/ignored path: {src} -> {dst}")
    if not s.exists():
        raise FilesystemError(f"Source not found: {src}")
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(s), str(d))
    return {
        "moved": str(s.relative_to(TARGET_REPO)),
        "to": str(d.relative_to(TARGET_REPO)),
    }


def _build_server():
    """Construct the FastMCP server, registering the tools above."""
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("repo-brain-filesystem")
    server.tool()(list_files)
    server.tool()(read_file)
    server.tool()(create_folder)
    server.tool()(move_file)
    return server


if __name__ == "__main__":
    _build_server().run()
