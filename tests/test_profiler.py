"""Tests for reqtrace.profiler."""
import pytest
from reqtrace.storage import RequestRecord
from reqtrace.profiler import (
    profile,
    profile_by_path,
    ProfileResult,
    DEFAULT_BOUNDARIES,
)


def make_record(method="GET", path="/api", status=200, duration_ms=100.0):
    return RequestRecord(
        method=method,
        path=path,
        status_code=status,
        duration_ms=duration_ms,
        request_headers={},
        response_headers={},
        request_body=None,
        response_body=None,
    )


def test_profile_empty():
    result = profile([])
    assert result.count == 0
    assert result.min_ms == 0.0
    assert result.max_ms == 0.0
    assert result.mean_ms == 0.0
    assert result.p50_ms == 0.0
    assert result.buckets == {}


def test_profile_single_record():
    r = make_record(duration_ms=200.0)
    result = profile([r])
    assert result.count == 1
    assert result.min_ms == 200.0
    assert result.max_ms == 200.0
    assert result.mean_ms == 200.0
    assert result.p50_ms == 200.0
    assert result.p99_ms == 200.0


def test_profile_multiple_records_percentiles():
    durations = [10.0, 50.0, 100.0, 200.0, 300.0, 400.0, 500.0, 600.0, 700.0, 1000.0]
    records = [make_record(duration_ms=d) for d in durations]
    result = profile(records)
    assert result.count == 10
    assert result.min_ms == 10.0
    assert result.max_ms == 1000.0
    assert abs(result.mean_ms - sum(durations) / 10) < 0.01
    assert result.p50_ms == durations[4]   # index 4 at 50th pct
    assert result.p90_ms == durations[8]   # index 8 at 90th pct
    assert result.p99_ms == durations[9]   # index 9 at 99th pct


def test_profile_buckets_populated():
    records = [
        make_record(duration_ms=30.0),   # <50ms
        make_record(duration_ms=80.0),   # <100ms
        make_record(duration_ms=80.0),   # <100ms
        make_record(duration_ms=600.0),  # <1000ms
    ]
    result = profile(records)
    assert result.buckets.get("<50ms") == 1
    assert result.buckets.get("<100ms") == 2
    assert result.buckets.get("<1000ms") == 1


def test_profile_bucket_overflow():
    r = make_record(duration_ms=9999.0)
    result = profile([r])
    last = f">={DEFAULT_BOUNDARIES[-1]}ms"
    assert result.buckets.get(last) == 1


def test_profile_str_output():
    records = [make_record(duration_ms=d) for d in [100.0, 200.0, 300.0]]
    result = profile(records)
    text = str(result)
    assert "count=3" in text
    assert "mean=" in text
    assert "p90=" in text


def test_profile_by_path_groups_correctly():
    records = [
        make_record(method="GET", path="/a", duration_ms=100.0),
        make_record(method="GET", path="/a", duration_ms=200.0),
        make_record(method="POST", path="/b", duration_ms=50.0),
    ]
    by_path = profile_by_path(records)
    assert "GET /a" in by_path
    assert "POST /b" in by_path
    assert by_path["GET /a"].count == 2
    assert by_path["POST /b"].count == 1
    assert by_path["POST /b"].mean_ms == 50.0
