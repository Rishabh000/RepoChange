"""Tests for script.py."""
from script import normalize, summarize


def test_normalize_strips_and_lowercases():
    out = normalize([{"name": "  Alice  "}])
    assert out == [{"name": "alice"}]


def test_summarize_counts():
    assert summarize([{"a": 1}, {"a": 2}]) == {"count": 2}
