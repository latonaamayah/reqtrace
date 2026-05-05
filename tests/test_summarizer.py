"""Tests for reqtrace.summarizer."""

import pytest
from reqtrace.storage import RequestRecord
from reqtrace.summarizer import summarize, format_summary


def make_record(method="GET", path="/api", status=200, duration=50.0):
    return RequestRecord(
        method=method,
        path=path,
        headers={},
        body=None,
        status_code=status,
        response_headers={},
        response_body=b"",
        duration_ms=duration,
        timestamp="2024-01-01T00:00:00",
    )


def test_summarize_empty():
    result = summarize([])
    assert result["total"] == 0
    assert result["avg_duration_ms"] is None
    assert result["error_rate"] == 0.0


def test_summarize_total():
    records = [make_record() for _ in range(5)]
    assert summarize(records)["total"] == 5


def test_summarize_methods():
    records = [make_record("GET"), make_record("POST"), make_record("GET")]
    s = summarize(records)
    assert s["methods"]["GET"] == 2
    assert s["methods"]["POST"] == 1


def test_summarize_status_codes():
    records = [make_record(status=200), make_record(status=404), make_record(status=200)]
    s = summarize(records)
    assert s["status_codes"]["200"] == 2
    assert s["status_codes"]["404"] == 1


def test_summarize_avg_duration():
    records = [make_record(duration=100.0), make_record(duration=200.0)]
    s = summarize(records)
    assert s["avg_duration_ms"] == 150.0


def test_summarize_slowest_and_fastest():
    records = [
        make_record(path="/fast", duration=10.0),
        make_record(path="/slow", duration=500.0),
        make_record(path="/mid", duration=100.0),
    ]
    s = summarize(records)
    assert s["slowest"]["path"] == "/slow"
    assert s["fastest"]["path"] == "/fast"


def test_summarize_error_rate():
    records = [make_record(status=200), make_record(status=500), make_record(status=404)]
    s = summarize(records)
    assert abs(s["error_rate"] - 2 / 3) < 0.001


def test_summarize_top_paths():
    records = [
        make_record(path="/a"),
        make_record(path="/a"),
        make_record(path="/b"),
    ]
    s = summarize(records)
    top = dict(s["top_paths"])
    assert top["/a"] == 2
    assert top["/b"] == 1


def test_format_summary_contains_key_info():
    records = [make_record(status=200, duration=42.0)]
    s = summarize(records)
    text = format_summary(s)
    assert "Total requests" in text
    assert "42.0" in text
    assert "Error rate" in text
