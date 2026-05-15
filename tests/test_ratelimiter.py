"""Tests for reqtrace.ratelimiter."""
from __future__ import annotations

import time
from typing import List

import pytest

from reqtrace.storage import RequestRecord
from reqtrace.ratelimiter import analyze_rate_limits, EndpointRate, RateLimitResult


def make_record(
    method: str = "GET",
    path: str = "/api/v1/items",
    status: int = 200,
    duration: float = 0.05,
    timestamp: float | None = None,
) -> RequestRecord:
    return RequestRecord(
        method=method,
        path=path,
        status_code=status,
        request_headers={},
        response_headers={},
        request_body="",
        response_body="",
        duration_ms=duration * 1000,
        timestamp=timestamp if timestamp is not None else time.time(),
    )


def test_analyze_empty_returns_empty_result():
    result = analyze_rate_limits([], max_rps=5.0)
    assert isinstance(result, RateLimitResult)
    assert result.endpoint_rates == []
    assert result.violation_count == 0


def test_single_record_no_violation():
    records = [make_record(timestamp=0.0)]
    result = analyze_rate_limits(records, max_rps=5.0)
    assert len(result.endpoint_rates) == 1
    er = result.endpoint_rates[0]
    assert er.method == "GET"
    assert er.path == "/api/v1/items"
    assert not er.exceeds_limit


def test_high_rate_triggers_violation():
    # 100 requests in 1 second => 100 rps
    base = 1_000_000.0
    records = [make_record(timestamp=base + i * 0.01) for i in range(100)]
    result = analyze_rate_limits(records, max_rps=10.0)
    assert result.violation_count == 1
    assert result.violating[0].exceeds_limit is True


def test_low_rate_no_violation():
    base = 0.0
    # 5 requests spread over 10 seconds => 0.5 rps
    records = [make_record(timestamp=base + i * 2.0) for i in range(5)]
    result = analyze_rate_limits(records, max_rps=5.0)
    assert result.violation_count == 0


def test_multiple_endpoints_tracked_separately():
    base = 0.0
    records = (
        [make_record(path="/fast", timestamp=base + i * 0.01) for i in range(50)]
        + [make_record(path="/slow", timestamp=base + i * 2.0) for i in range(5)]
    )
    result = analyze_rate_limits(records, max_rps=10.0)
    paths = {er.path: er for er in result.endpoint_rates}
    assert paths["/fast"].exceeds_limit is True
    assert paths["/slow"].exceeds_limit is False


def test_str_output_contains_summary():
    base = 0.0
    records = [make_record(timestamp=base + i * 0.1) for i in range(10)]
    result = analyze_rate_limits(records, max_rps=5.0)
    text = str(result)
    assert "Rate limit analysis" in text
    assert "Violations" in text


def test_endpoint_rate_str_flags_violation():
    er = EndpointRate(
        method="POST",
        path="/submit",
        count=200,
        window_seconds=10.0,
        rps=20.0,
        exceeds_limit=True,
    )
    assert "EXCEEDS LIMIT" in str(er)


def test_endpoint_rate_str_no_flag_when_ok():
    er = EndpointRate(
        method="GET",
        path="/health",
        count=5,
        window_seconds=10.0,
        rps=0.5,
        exceeds_limit=False,
    )
    assert "EXCEEDS LIMIT" not in str(er)
