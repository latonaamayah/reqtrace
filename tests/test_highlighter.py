"""Tests for reqtrace.highlighter."""
from __future__ import annotations

import datetime
import pytest

from reqtrace.storage import RequestRecord
from reqtrace.highlighter import HighlightRule, HighlightResult, Highlighter


RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def make_record(
    method: str = "GET",
    path: str = "/api/test",
    status_code: int = 200,
    duration_ms: float = 50.0,
) -> RequestRecord:
    return RequestRecord(
        record_id="rec-1",
        timestamp=datetime.datetime(2024, 1, 1, 12, 0, 0),
        method=method,
        path=path,
        query_string="",
        request_headers={},
        request_body="",
        status_code=status_code,
        response_headers={},
        response_body="",
        duration_ms=duration_ms,
    )


def test_highlight_rule_matches_true():
    rule = HighlightRule("error", RED, lambda r: r.status_code >= 500)
    assert rule.matches(make_record(status_code=500))


def test_highlight_rule_matches_false():
    rule = HighlightRule("error", RED, lambda r: r.status_code >= 500)
    assert not rule.matches(make_record(status_code=200))


def test_highlight_rule_predicate_exception_returns_false():
    rule = HighlightRule("bad", RED, lambda r: 1 / 0)
    assert not rule.matches(make_record())


def test_highlighter_no_rules_returns_unhighlighted():
    h = Highlighter()
    result = h.highlight_record(make_record())
    assert not result.is_highlighted
    assert result.matched_rule is None


def test_highlighter_first_matching_rule_wins():
    h = Highlighter()
    h.add_rule(HighlightRule("slow", YELLOW, lambda r: r.duration_ms > 100))
    h.add_rule(HighlightRule("error", RED, lambda r: r.status_code >= 500))
    result = h.highlight_record(make_record(status_code=500, duration_ms=200))
    assert result.matched_rule is not None
    assert result.matched_rule.label == "slow"


def test_highlighter_second_rule_matches_when_first_does_not():
    h = Highlighter()
    h.add_rule(HighlightRule("slow", YELLOW, lambda r: r.duration_ms > 100))
    h.add_rule(HighlightRule("error", RED, lambda r: r.status_code >= 500))
    result = h.highlight_record(make_record(status_code=500, duration_ms=50))
    assert result.matched_rule is not None
    assert result.matched_rule.label == "error"


def test_highlight_result_format_label_no_match():
    result = HighlightResult(record=make_record())
    assert result.format_label() == ""


def test_highlight_result_format_label_with_match():
    rule = HighlightRule("error", RED, lambda r: True)
    result = HighlightResult(record=make_record(), matched_rule=rule)
    label = result.format_label()
    assert "error" in label
    assert RED in label
    assert RESET in label


def test_highlight_all_returns_one_result_per_record():
    h = Highlighter()
    h.add_rule(HighlightRule("error", RED, lambda r: r.status_code >= 500))
    records = [make_record(status_code=200), make_record(status_code=500)]
    results = h.highlight_all(records)
    assert len(results) == 2
    assert not results[0].is_highlighted
    assert results[1].is_highlighted


def test_highlighted_only_filters_unmatched():
    h = Highlighter()
    h.add_rule(HighlightRule("error", RED, lambda r: r.status_code >= 500))
    records = [
        make_record(status_code=200),
        make_record(status_code=500),
        make_record(status_code=404),
    ]
    results = h.highlighted_only(records)
    assert len(results) == 1
    assert results[0].record.status_code == 500
