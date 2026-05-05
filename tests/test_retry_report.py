"""Tests for reqtrace.retry_report."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from unittest.mock import MagicMock

import pytest

from reqtrace.replayer import ReplayResult
from reqtrace.retrier import RetryOutcome
from reqtrace.retry_report import format_retry_report, retry_summary_dict
from reqtrace.storage import RequestRecord


def make_record(record_id="r1", method="GET", path="/api") -> RequestRecord:
    return RequestRecord(
        record_id=record_id,
        method=method,
        url=f"http://localhost{path}",
        path=path,
        headers={},
        body=None,
        timestamp=datetime.now(timezone.utc).isoformat(),
        duration_ms=30.0,
        status_code=200,
        response_headers={},
        response_body=b"",
    )


def make_outcome(record_id="r1", method="GET", path="/api",
                 attempts=1, succeeded=True, status_code=200, error=None) -> RetryOutcome:
    record = make_record(record_id, method, path)
    result = ReplayResult(record_id=record_id, status_code=status_code,
                          response_body=b"", error=error)
    return RetryOutcome(record=record, attempts=attempts,
                        results=[result], succeeded=succeeded)


def test_format_empty():
    report = format_retry_report([])
    assert "No retry" in report


def test_format_single_success():
    outcome = make_outcome(succeeded=True, attempts=1, status_code=200)
    report = format_retry_report([outcome])
    assert "Succeeded     : 1" in report
    assert "Failed        : 0" in report
    assert "✓" in report


def test_format_single_failure():
    outcome = make_outcome(succeeded=False, attempts=3, status_code=503)
    report = format_retry_report([outcome])
    assert "Failed        : 1" in report
    assert "✗" in report
    assert "503" in report


def test_format_with_error():
    outcome = make_outcome(succeeded=False, attempts=2, status_code=None, error="timeout")
    report = format_retry_report([outcome])
    assert "timeout" in report


def test_format_total_attempts():
    outcomes = [
        make_outcome(record_id="1", attempts=2, succeeded=True),
        make_outcome(record_id="2", attempts=3, succeeded=False),
    ]
    report = format_retry_report(outcomes)
    assert "Total attempts: 5" in report


def test_summary_dict_keys():
    outcomes = [make_outcome()]
    summary = retry_summary_dict(outcomes)
    assert "total" in summary
    assert "succeeded" in summary
    assert "failed" in summary
    assert "total_attempts" in summary
    assert "records" in summary


def test_summary_dict_values():
    outcomes = [
        make_outcome(record_id="1", succeeded=True, attempts=1),
        make_outcome(record_id="2", succeeded=False, attempts=3, status_code=500),
    ]
    summary = retry_summary_dict(outcomes)
    assert summary["total"] == 2
    assert summary["succeeded"] == 1
    assert summary["failed"] == 1
    assert summary["total_attempts"] == 4


def test_summary_dict_record_fields():
    outcome = make_outcome(record_id="xyz", method="POST", path="/submit",
                           attempts=2, succeeded=True, status_code=201)
    summary = retry_summary_dict([outcome])
    rec = summary["records"][0]
    assert rec["record_id"] == "xyz"
    assert rec["method"] == "POST"
    assert rec["path"] == "/submit"
    assert rec["attempts"] == 2
    assert rec["final_status"] == 201
