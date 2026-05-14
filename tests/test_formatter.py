"""Tests for reqtrace.formatter."""

from __future__ import annotations

import pytest

from reqtrace.storage import RequestRecord
from reqtrace.formatter import format_record, format_records


def make_record(
    method: str = "GET",
    path: str = "/api/v1/users",
    status: int = 200,
    duration_ms: float = 42.0,
    request_body: str = "",
    response_body: str = "",
    request_headers: dict | None = None,
    response_headers: dict | None = None,
) -> RequestRecord:
    return RequestRecord(
        method=method,
        path=path,
        request_headers=request_headers or {},
        request_body=request_body,
        response_status=status,
        response_headers=response_headers or {},
        response_body=response_body,
        duration_ms=duration_ms,
        timestamp="2024-01-15T10:00:00",
    )


def test_format_record_basic():
    record = make_record()
    output = format_record(record)
    assert "GET" in output
    assert "/api/v1/users" in output
    assert "200" in output
    assert "42.0 ms" in output


def test_format_record_includes_timestamp():
    record = make_record()
    output = format_record(record)
    assert "2024-01-15T10:00:00" in output


def test_format_record_no_headers_by_default():
    record = make_record(request_headers={"Authorization": "Bearer tok"})
    output = format_record(record, show_headers=False)
    assert "Authorization" not in output


def test_format_record_shows_headers_when_requested():
    record = make_record(
        request_headers={"Content-Type": "application/json"},
        response_headers={"X-Request-Id": "abc123"},
    )
    output = format_record(record, show_headers=True)
    assert "Content-Type" in output
    assert "X-Request-Id" in output


def test_format_record_shows_body_when_requested():
    record = make_record(request_body='{"name": "alice"}', response_body='{"id": 1}')
    output = format_record(record, show_body=True)
    assert '{"name": "alice"}' in output
    assert '{"id": 1}' in output


def test_format_record_body_truncated():
    long_body = "x" * 500
    record = make_record(response_body=long_body)
    output = format_record(record, show_body=True, max_body_len=100)
    assert "x" * 100 in output
    assert "\u2026" in output  # ellipsis
    assert "x" * 101 not in output


def test_format_record_color_contains_ansi():
    record = make_record(status=500)
    output = format_record(record, color=True)
    assert "\033[" in output


def test_format_record_no_color_no_ansi():
    record = make_record(status=500)
    output = format_record(record, color=False)
    assert "\033[" not in output


def test_format_records_empty():
    assert format_records([]) == "(no records)"


def test_format_records_multiple():
    records = [
        make_record(path="/a", status=200),
        make_record(path="/b", status=404),
    ]
    output = format_records(records)
    assert "/a" in output
    assert "/b" in output
    assert "200" in output
    assert "404" in output
