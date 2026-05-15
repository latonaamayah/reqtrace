"""Tests for reqtrace.pool_report."""
from __future__ import annotations

from reqtrace.pool_report import format_pool_report, pool_summary_dict
from reqtrace.replayer import ReplayResult
from reqtrace.replayer_pool import PoolResult
from reqtrace.storage import RequestRecord


def _rec(path: str = "/") -> RequestRecord:
    return RequestRecord(
        id="r",
        timestamp="2024-01-01T00:00:00",
        method="GET",
        path=path,
        request_headers={},
        request_body="",
        response_status=200,
        response_headers={},
        response_body="",
        duration_ms=5.0,
    )


def _res(status: int, duration: float = 5.0) -> ReplayResult:
    return ReplayResult(record=_rec(), status_code=status, body="", duration_ms=duration)


def test_summary_empty():
    pr = PoolResult()
    s = pool_summary_dict(pr)
    assert s["total"] == 0
    assert s["success"] == 0
    assert s["errors"] == 0
    assert s["avg_duration_ms"] == 0.0


def test_summary_counts_status_codes():
    pr = PoolResult(results=[_res(200), _res(200), _res(500)])
    s = pool_summary_dict(pr)
    assert s["status_counts"]["200"] == 2
    assert s["status_counts"]["500"] == 1


def test_summary_avg_duration():
    pr = PoolResult(results=[_res(200, 10.0), _res(200, 20.0)])
    s = pool_summary_dict(pr)
    assert s["avg_duration_ms"] == 15.0


def test_summary_includes_errors():
    pr = PoolResult(results=[_res(200)], errors=["boom"])
    s = pool_summary_dict(pr)
    assert s["total"] == 2
    assert s["errors"] == 1


def test_format_report_contains_headings():
    pr = PoolResult(results=[_res(200), _res(404)], errors=["timeout"])
    report = format_pool_report(pr)
    assert "Pool Replay Report" in report
    assert "Total replayed" in report
    assert "Errors" in report


def test_format_report_lists_error_details():
    pr = PoolResult(errors=["connection refused"])
    report = format_pool_report(pr)
    assert "connection refused" in report


def test_format_report_status_breakdown():
    pr = PoolResult(results=[_res(201), _res(201)])
    report = format_pool_report(pr)
    assert "201: 2" in report
