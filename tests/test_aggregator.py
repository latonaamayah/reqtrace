"""Tests for reqtrace.aggregator."""
from __future__ import annotations

import datetime
from reqtrace.aggregator import aggregate, AggregationResult
from reqtrace.storage import RequestRecord


def make_record(
    method="GET",
    path="/api/v1",
    status_code=200,
    duration_ms=50.0,
) -> RequestRecord:
    return RequestRecord(
        record_id="test-id",
        timestamp=datetime.datetime.utcnow().isoformat(),
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
        request_headers={},
        response_headers={},
        request_body="",
        response_body="",
    )


def test_aggregate_empty():
    result = aggregate([])
    assert isinstance(result, AggregationResult)
    assert result.total_requests == 0
    assert result.endpoints == {}


def test_aggregate_single_record():
    records = [make_record(method="GET", path="/ping", status_code=200, duration_ms=10.0)]
    result = aggregate(records)
    assert result.total_requests == 1
    assert "GET:/ping" in result.endpoints
    stats = result.endpoints["GET:/ping"]
    assert stats.count == 1
    assert stats.avg_duration_ms == 10.0
    assert stats.error_count == 0
    assert stats.error_rate == 0.0


def test_aggregate_groups_by_method_and_path():
    records = [
        make_record(method="GET", path="/users"),
        make_record(method="POST", path="/users"),
        make_record(method="GET", path="/users"),
    ]
    result = aggregate(records)
    assert len(result.endpoints) == 2
    assert result.endpoints["GET:/users"].count == 2
    assert result.endpoints["POST:/users"].count == 1


def test_aggregate_avg_duration():
    records = [
        make_record(duration_ms=100.0),
        make_record(duration_ms=200.0),
    ]
    result = aggregate(records)
    stats = result.endpoints["GET:/api/v1"]
    assert stats.avg_duration_ms == 150.0


def test_aggregate_error_count():
    records = [
        make_record(status_code=200),
        make_record(status_code=500),
        make_record(status_code=404),
    ]
    result = aggregate(records)
    stats = result.endpoints["GET:/api/v1"]
    assert stats.error_count == 2
    assert abs(stats.error_rate - 2 / 3) < 1e-9


def test_aggregate_status_code_distribution():
    records = [
        make_record(status_code=200),
        make_record(status_code=200),
        make_record(status_code=500),
    ]
    result = aggregate(records)
    stats = result.endpoints["GET:/api/v1"]
    assert stats.status_codes[200] == 2
    assert stats.status_codes[500] == 1


def test_sorted_by_count():
    records = [
        make_record(path="/a"),
        make_record(path="/b"),
        make_record(path="/b"),
    ]
    result = aggregate(records)
    sorted_stats = result.sorted_by_count()
    assert sorted_stats[0].path == "/b"
    assert sorted_stats[1].path == "/a"


def test_str_representation():
    records = [make_record()]
    result = aggregate(records)
    text = str(result)
    assert "GET" in text
    assert "/api/v1" in text
