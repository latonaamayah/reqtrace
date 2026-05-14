"""Tests for reqtrace.splitter."""
from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest

from reqtrace.splitter import (
    SplitResult,
    _by_method,
    _by_path_prefix,
    _by_status_class,
    split,
)
from reqtrace.storage import LogStorage, RequestRecord


def make_record(
    method: str = "GET",
    path: str = "/api/v1/items",
    status_code: int = 200,
    duration_ms: float = 50.0,
) -> RequestRecord:
    return RequestRecord(
        record_id="test-id",
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
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


@pytest.fixture()
def tmp_storage(tmp_path):
    return LogStorage(str(tmp_path / "log.jsonl"))


def test_split_empty_storage(tmp_storage):
    result = split(tmp_storage, _by_method)
    assert result.total == 0
    assert result.buckets == {}
    assert result.unmatched == 0


def test_split_by_method(tmp_storage):
    tmp_storage.save(make_record(method="GET"))
    tmp_storage.save(make_record(method="POST"))
    tmp_storage.save(make_record(method="GET"))

    result = split(tmp_storage, _by_method)

    assert result.total == 3
    assert len(result.buckets["GET"]) == 2
    assert len(result.buckets["POST"]) == 1
    assert result.unmatched == 0


def test_split_by_status_class(tmp_storage):
    tmp_storage.save(make_record(status_code=200))
    tmp_storage.save(make_record(status_code=201))
    tmp_storage.save(make_record(status_code=404))
    tmp_storage.save(make_record(status_code=500))

    result = split(tmp_storage, _by_status_class)

    assert result.total == 4
    assert len(result.buckets["2xx"]) == 2
    assert len(result.buckets["4xx"]) == 1
    assert len(result.buckets["5xx"]) == 1


def test_split_by_path_prefix_depth1(tmp_storage):
    tmp_storage.save(make_record(path="/api/users"))
    tmp_storage.save(make_record(path="/api/orders"))
    tmp_storage.save(make_record(path="/health"))

    result = split(tmp_storage, _by_path_prefix(depth=1))

    assert "/api" in result.buckets
    assert "/health" in result.buckets
    assert len(result.buckets["/api"]) == 2


def test_split_persists_bucket_files(tmp_storage, tmp_path):
    tmp_storage.save(make_record(method="GET"))
    tmp_storage.save(make_record(method="POST"))

    out_dir = str(tmp_path / "buckets")
    result = split(tmp_storage, _by_method, output_dir=out_dir, persist=True)

    assert result.total == 2
    files = os.listdir(out_dir)
    assert any("GET" in f for f in files)
    assert any("POST" in f for f in files)


def test_split_result_str(tmp_storage):
    tmp_storage.save(make_record(method="GET"))
    result = split(tmp_storage, _by_method)
    text = str(result)
    assert "GET" in text
    assert "1 record(s)" in text


def test_split_unmatched_incremented_on_key_fn_returning_none(tmp_storage):
    tmp_storage.save(make_record())

    result = split(tmp_storage, lambda r: None)

    assert result.unmatched == 1
    assert result.buckets == {}
