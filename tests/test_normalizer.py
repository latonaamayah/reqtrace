"""Tests for reqtrace.normalizer."""
import pytest

from reqtrace.storage import RequestRecord
from reqtrace.normalizer import (
    normalize,
    normalize_record,
    _normalize_path,
    _normalize_headers,
    NormalizeResult,
)


def make_record(
    path="/api/v1",
    method="GET",
    req_headers=None,
    resp_headers=None,
    req_body="",
    resp_body="",
    status_code=200,
    duration_ms=50.0,
) -> RequestRecord:
    return RequestRecord(
        id="test-id",
        timestamp="2024-01-01T00:00:00",
        method=method,
        path=path,
        request_headers=req_headers or {"Content-Type": "application/json"},
        request_body=req_body,
        status_code=status_code,
        response_headers=resp_headers or {"Content-Type": "application/json"},
        response_body=resp_body,
        duration_ms=duration_ms,
    )


def test_normalize_path_collapses_slashes():
    assert _normalize_path("/api//v1///users") == "/api/v1/users"


def test_normalize_path_strips_trailing_slash():
    assert _normalize_path("/api/v1/") == "/api/v1"


def test_normalize_path_preserves_root():
    assert _normalize_path("/") == "/"


def test_normalize_headers_lowercases_keys():
    result = _normalize_headers({"Content-Type": "application/json", "X-Token": " abc "})
    assert "content-type" in result
    assert "x-token" in result
    assert result["x-token"] == "abc"


def test_normalize_record_no_change_when_already_clean():
    record = make_record(path="/api/v1", req_headers={"content-type": "application/json"})
    normalized, changed = normalize_record(record)
    assert not changed
    assert normalized.path == "/api/v1"


def test_normalize_record_fixes_path():
    record = make_record(path="/api//v1/")
    normalized, changed = normalize_record(record)
    assert changed
    assert normalized.path == "/api/v1"


def test_normalize_record_lowercases_headers():
    record = make_record(req_headers={"Authorization": "Bearer token"})
    normalized, changed = normalize_record(record)
    assert changed
    assert "authorization" in normalized.request_headers
    assert "Authorization" not in normalized.request_headers


def test_normalize_record_strips_body_whitespace():
    record = make_record(req_body="  hello  ", resp_body="\nworld\n")
    normalized, changed = normalize_record(record)
    assert changed
    assert normalized.request_body == "hello"
    assert normalized.response_body == "world"


def test_normalize_empty_list():
    result = normalize([])
    assert result.total == 0
    assert result.changed == 0
    assert result.unchanged == 0
    assert result.records == []


def test_normalize_counts_changed_records():
    records = [
        make_record(path="/clean", req_headers={"content-type": "application/json"}),
        make_record(path="/dirty//path/"),
    ]
    result = normalize(records)
    assert result.total == 2
    assert result.changed == 1
    assert result.unchanged == 1


def test_normalize_result_str():
    result = NormalizeResult(total=5, changed=3)
    assert "3/5" in str(result)
    assert "2 unchanged" in str(result)
