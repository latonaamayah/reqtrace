"""Tests for reqtrace.deduplicator."""
from __future__ import annotations

import datetime
from typing import Any, Dict

import pytest

from reqtrace.deduplicator import (
    DeduplicationResult,
    deduplicate,
    find_duplicate_groups,
    _record_fingerprint,
)
from reqtrace.storage import RequestRecord


def make_record(
    method: str = "GET",
    path: str = "/api/test",
    status: int = 200,
    body: str = "",
    query: str = "",
    ts: str = "2024-01-01T00:00:00",
) -> RequestRecord:
    return RequestRecord(
        timestamp=ts,
        method=method,
        path=path,
        query_string=query,
        request_headers={"host": "localhost"},
        request_body=body,
        response_status=status,
        response_headers={},
        response_body="ok",
        duration_ms=10.0,
    )


def test_fingerprint_same_for_identical_requests():
    r1 = make_record(ts="2024-01-01T00:00:00")
    r2 = make_record(ts="2024-01-01T12:00:00")  # different timestamp
    assert _record_fingerprint(r1) == _record_fingerprint(r2)


def test_fingerprint_differs_for_different_method():
    r1 = make_record(method="GET")
    r2 = make_record(method="POST")
    assert _record_fingerprint(r1) != _record_fingerprint(r2)


def test_fingerprint_differs_for_different_path():
    r1 = make_record(path="/a")
    r2 = make_record(path="/b")
    assert _record_fingerprint(r1) != _record_fingerprint(r2)


def test_deduplicate_empty():
    result = deduplicate([])
    assert result.unique == []
    assert result.duplicates == []
    assert result.unique_count == 0
    assert result.duplicate_count == 0


def test_deduplicate_no_duplicates():
    records = [make_record(path=f"/api/{i}") for i in range(5)]
    result = deduplicate(records)
    assert result.unique_count == 5
    assert result.duplicate_count == 0


def test_deduplicate_removes_duplicates():
    r1 = make_record(ts="2024-01-01T00:00:00")
    r2 = make_record(ts="2024-01-01T01:00:00")  # same fingerprint
    r3 = make_record(path="/other")
    result = deduplicate([r1, r2, r3])
    assert result.unique_count == 2
    assert result.duplicate_count == 1
    assert r2 in result.duplicates


def test_deduplicate_first_occurrence_wins():
    r1 = make_record(ts="2024-01-01T00:00:00")
    r2 = make_record(ts="2024-01-01T01:00:00")
    result = deduplicate([r1, r2])
    assert result.unique[0] is r1


def test_find_duplicate_groups_empty():
    assert find_duplicate_groups([]) == []


def test_find_duplicate_groups_returns_only_multi_member_groups():
    r1 = make_record(ts="T1")
    r2 = make_record(ts="T2")  # duplicate of r1
    r3 = make_record(path="/unique")
    groups = find_duplicate_groups([r1, r2, r3])
    assert len(groups) == 1
    assert len(groups[0]) == 2


def test_deduplication_result_str():
    result = DeduplicationResult(unique=[make_record()], duplicates=[make_record()])
    s = str(result)
    assert "1 unique" in s
    assert "1 duplicates" in s
