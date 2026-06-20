"""Memory MCP server.

Exposes the semantic memory as MCP tools:
    remember(file, summary, content)
    search_memory(query, n_results)
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "memory"))

import vector_store  # noqa: E402


def remember(file: str, summary: str, content: str = "") -> dict:
    """Store a file summary in semantic memory."""
    return vector_store.remember(filename=file, summary=summary, content=content)


def search_memory(query: str, n_results: int = 5) -> list[dict]:
    """Search semantic memory for files matching a query."""
    return vector_store.search_memory(query=query, n_results=n_results)


def _build_server():
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("repo-brain-memory")
    server.tool()(remember)
    server.tool()(search_memory)
    return server


if __name__ == "__main__":
    _build_server().run()
