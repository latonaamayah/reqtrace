"""Tests for reqtrace.throttler."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from typing import List

from reqtrace.storage import RequestRecord
from reqtrace.throttler import ThrottleConfig, ThrottleResult, throttle_records


def make_record(path: str = "/api", method: str = "GET", status: int = 200,
                duration: float = 0.05, ts: str | None = None) -> RequestRecord:
    return RequestRecord(
        timestamp=ts or "2024-01-01T00:00:00+00:00",
        method=method,
        path=path,
        request_headers={},
        request_body="",
        status_code=status,
        response_headers={},
        response_body="",
        duration_ms=duration,
    )


def _ts(offset_ms: int) -> str:
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    dt = base + timedelta(milliseconds=offset_ms)
    return dt.isoformat()


def test_config_invalid_max_rps_raises():
    with pytest.raises(ValueError, match="max_rps"):
        ThrottleConfig(max_rps=0)


def test_config_negative_window_raises():
    with pytest.raises(ValueError, match="window_ms"):
        ThrottleConfig(max_rps=1.0, window_ms=-100)


def test_throttle_empty_returns_empty():
    config = ThrottleConfig(max_rps=10.0)
    result = throttle_records([], config)
    assert result.kept_count == 0
    assert result.dropped_count == 0


def test_throttle_keeps_all_when_under_budget():
    config = ThrottleConfig(max_rps=10.0, window_ms=1000.0)  # 10 per second
    records = [make_record(ts=_ts(i * 50)) for i in range(5)]  # 5 in one window
    result = throttle_records(records, config)
    assert result.kept_count == 5
    assert result.dropped_count == 0


def test_throttle_drops_excess_records():
    # 2 per second budget, 5 records in the same 1-second window
    config = ThrottleConfig(max_rps=2.0, window_ms=1000.0)
    records = [make_record(ts=_ts(i * 100)) for i in range(5)]
    result = throttle_records(records, config)
    assert result.kept_count == 2
    assert result.dropped_count == 3


def test_throttle_resets_budget_across_windows():
    # 1 per second; records spread across 3 windows
    config = ThrottleConfig(max_rps=1.0, window_ms=1000.0)
    records = [
        make_record(ts=_ts(0)),    # window 0 -> kept
        make_record(ts=_ts(100)),  # window 0 -> dropped
        make_record(ts=_ts(1000)), # window 1 -> kept
        make_record(ts=_ts(2000)), # window 2 -> kept
        make_record(ts=_ts(2500)), # window 2 -> dropped
    ]
    result = throttle_records(records, config)
    assert result.kept_count == 3
    assert result.dropped_count == 2


def test_throttle_result_str():
    result = ThrottleResult(kept=[], dropped=[])
    assert "kept=0" in str(result)
    assert "dropped=0" in str(result)


def test_throttle_preserves_order_of_kept_records():
    config = ThrottleConfig(max_rps=2.0, window_ms=1000.0)
    records = [make_record(path=f"/{i}", ts=_ts(i * 100)) for i in range(5)]
    result = throttle_records(records, config)
    paths = [r.path for r in result.kept]
    assert paths == ["/0", "/1"]


def test_throttle_sub_second_window():
    # 1 per 100 ms window, 3 records in 300 ms
    config = ThrottleConfig(max_rps=10.0, window_ms=100.0)  # budget=1 per 100ms
    records = [
        make_record(ts=_ts(0)),
        make_record(ts=_ts(50)),   # same 100ms bucket -> dropped
        make_record(ts=_ts(100)),  # next bucket -> kept
    ]
    result = throttle_records(records, config)
    assert result.kept_count == 2
    assert result.dropped_count == 1
