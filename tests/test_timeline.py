"""Tests for reqtrace.timeline."""

import time
from reqtrace.storage import RequestRecord
from reqtrace.timeline import build_timeline, Timeline, TimelineEntry


def make_record(path: str = "/api/test", method: str = "GET",
                status: int = 200, duration: float = 50.0,
                timestamp: float = None) -> RequestRecord:
    return RequestRecord(
        method=method,
        path=path,
        query_string="",
        request_headers={},
        request_body="",
        status_code=status,
        response_headers={},
        response_body="",
        duration_ms=duration,
        timestamp=timestamp if timestamp is not None else time.time(),
    )


def test_build_timeline_empty():
    tl = build_timeline([])
    assert isinstance(tl, Timeline)
    assert tl.entries == []
    assert tl.total_span_ms == 0.0


def test_build_timeline_single_record():
    rec = make_record(timestamp=1000.0)
    tl = build_timeline([rec])
    assert len(tl.entries) == 1
    assert tl.entries[0].gap_before_ms is None
    assert tl.total_span_ms == 0.0


def test_build_timeline_orders_by_timestamp():
    r1 = make_record(path="/first", timestamp=1000.0)
    r2 = make_record(path="/second", timestamp=1002.0)
    r3 = make_record(path="/third", timestamp=1001.0)
    tl = build_timeline([r1, r2, r3])
    paths = [e.record.path for e in tl.entries]
    assert paths == ["/first", "/third", "/second"]


def test_build_timeline_gap_computation():
    r1 = make_record(timestamp=1000.0)
    r2 = make_record(timestamp=1000.5)  # 500 ms later
    tl = build_timeline([r1, r2])
    assert tl.entries[0].gap_before_ms is None
    assert abs(tl.entries[1].gap_before_ms - 500.0) < 0.01


def test_build_timeline_total_span():
    r1 = make_record(timestamp=1000.0)
    r2 = make_record(timestamp=1001.0)  # 1000 ms span
    tl = build_timeline([r1, r2])
    assert abs(tl.total_span_ms - 1000.0) < 0.01


def test_timeline_format_empty():
    tl = build_timeline([])
    output = tl.format()
    assert "No records" in output


def test_timeline_format_contains_entries():
    r1 = make_record(path="/health", method="GET", status=200, timestamp=1000.0)
    r2 = make_record(path="/users", method="POST", status=201, timestamp=1000.1)
    tl = build_timeline([r1, r2])
    output = tl.format()
    assert "/health" in output
    assert "/users" in output
    assert "start" in output
    assert "Total span" in output


def test_timeline_entry_str_first():
    rec = make_record(path="/ping", method="GET", status=200, duration=10.0, timestamp=1000.0)
    entry = TimelineEntry(record=rec, gap_before_ms=None)
    s = str(entry)
    assert "start" in s
    assert "/ping" in s
    assert "200" in s


def test_timeline_entry_str_subsequent():
    rec = make_record(path="/data", method="GET", status=200, duration=20.0, timestamp=1001.0)
    entry = TimelineEntry(record=rec, gap_before_ms=250.0)
    s = str(entry)
    assert "+250.0ms" in s
    assert "/data" in s
