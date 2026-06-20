"""Central Gemini client for repo-brain.

Gemini is required. The API key is read from the environment or a .env file
(GOOGLE_API_KEY or GEMINI_API_KEY). If it is missing, calls raise
GeminiNotConfigured with a clear message rather than silently falling back.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from config import MODEL, ROOT as CONFIG_ROOT, TARGET_REPO  # noqa: E402

# Load .env files so the key can live next to the project (gitignored).
try:
    from dotenv import load_dotenv

    load_dotenv(CONFIG_ROOT / ".env")
    load_dotenv(TARGET_REPO / ".env")
except Exception:  # pragma: no cover - dotenv is optional at import time
    pass


class GeminiNotConfigured(RuntimeError):
    """Raised when no Gemini API key is available."""


_client = None


def _api_key() -> str | None:
    return os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")


def get_client():
    """Return a cached google-genai client, or raise if no key is configured."""
    global _client
    if _client is not None:
        return _client
    key = _api_key()
    if not key:
        raise GeminiNotConfigured(
            "Gemini API key required. Set GOOGLE_API_KEY (or GEMINI_API_KEY) "
            "in your environment or in a .env file at the repo root."
        )
    from google import genai

    _client = genai.Client(api_key=key)
    return _client


def generate(prompt: str) -> str:
    """Run a single-shot generation against the configured model."""
    client = get_client()
    resp = client.models.generate_content(model=MODEL, contents=prompt)
    return (resp.text or "").strip()
