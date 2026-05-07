"""Tests for reqtrace.truncator."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from reqtrace.storage import RequestRecord
from reqtrace.truncator import (
    _TRUNCATION_MARKER,
    TruncationResult,
    truncate_record,
    truncate_all,
)


def make_record(
    request_body: str = "",
    response_body: str = "",
    method: str = "GET",
    path: str = "/test",
    status_code: int = 200,
) -> RequestRecord:
    return RequestRecord(
        record_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        method=method,
        path=path,
        query_string="",
        request_headers={},
        request_body=request_body,
        status_code=status_code,
        response_headers={},
        response_body=response_body,
        duration_ms=10.0,
    )


def test_truncate_record_no_change_when_small():
    record = make_record(request_body="hello", response_body="world")
    new_record, changed = truncate_record(record, max_bytes=100)
    assert not changed
    assert new_record is record


def test_truncate_record_request_body_truncated():
    big_body = "x" * 200
    record = make_record(request_body=big_body)
    new_record, changed = truncate_record(record, max_bytes=50)
    assert changed
    assert new_record.request_body.endswith(_TRUNCATION_MARKER)
    assert len(new_record.request_body.encode()) <= 50 + len(_TRUNCATION_MARKER.encode())


def test_truncate_record_response_body_truncated():
    big_body = "y" * 300
    record = make_record(response_body=big_body)
    new_record, changed = truncate_record(record, max_bytes=64)
    assert changed
    assert new_record.response_body.endswith(_TRUNCATION_MARKER)


def test_truncate_record_preserves_other_fields():
    record = make_record(request_body="a" * 200, method="POST", path="/submit", status_code=201)
    new_record, _ = truncate_record(record, max_bytes=10)
    assert new_record.method == "POST"
    assert new_record.path == "/submit"
    assert new_record.status_code == 201
    assert new_record.record_id == record.record_id


def test_truncate_all_empty():
    result = truncate_all([], max_bytes=100)
    assert isinstance(result, TruncationResult)
    assert result.original_count == 0
    assert result.truncated_count == 0
    assert result.records == []


def test_truncate_all_counts_correctly():
    small = make_record(request_body="hi")
    big = make_record(response_body="z" * 500)
    result = truncate_all([small, big], max_bytes=100)
    assert result.original_count == 2
    assert result.truncated_count == 1
    assert result.unchanged_count == 1
    assert len(result.records) == 2


def test_truncate_all_str_output():
    records = [make_record(response_body="a" * 200)]
    result = truncate_all(records, max_bytes=50)
    text = str(result)
    assert "1/1" in text


def test_truncate_all_no_truncation_needed():
    records = [make_record(request_body="tiny") for _ in range(5)]
    result = truncate_all(records, max_bytes=1024)
    assert result.truncated_count == 0
    assert all(r.request_body == "tiny" for r in result.records)
