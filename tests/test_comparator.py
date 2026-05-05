"""Tests for reqtrace.comparator module."""

import pytest
from datetime import datetime

from reqtrace.storage import RequestRecord
from reqtrace.comparator import (
    compare_record_sets,
    format_comparison_report,
    ComparisonReport,
)


def make_record(
    method="GET",
    path="/api/test",
    status=200,
    duration=0.1,
    req_headers=None,
    resp_headers=None,
    body=b"",
):
    return RequestRecord(
        method=method,
        path=path,
        query_string="",
        request_headers=req_headers or {"Host": "localhost"},
        request_body=body,
        response_status=status,
        response_headers=resp_headers or {"Content-Type": "application/json"},
        response_body=b"{}",
        duration=duration,
        timestamp=datetime(2024, 1, 1, 12, 0, 0).isoformat(),
    )


def test_compare_identical_sets():
    baseline = [make_record()]
    current = [make_record()]
    report = compare_record_sets(baseline, current)
    assert report.total_compared == 1
    assert report.regression_count == 0
    assert report.unmatched_baseline == []
    assert report.unmatched_current == []


def test_compare_detects_status_regression():
    baseline = [make_record(status=200)]
    current = [make_record(status=500)]
    report = compare_record_sets(baseline, current)
    assert report.total_compared == 1
    assert report.regression_count == 1


def test_compare_unmatched_baseline():
    baseline = [make_record(path="/old")]
    current = [make_record(path="/new")]
    report = compare_record_sets(baseline, current)
    assert len(report.unmatched_baseline) == 1
    assert len(report.unmatched_current) == 1
    assert report.total_compared == 0


def test_compare_partial_overlap():
    baseline = [make_record(path="/a"), make_record(path="/b")]
    current = [make_record(path="/a"), make_record(path="/c")]
    report = compare_record_sets(baseline, current)
    assert report.total_compared == 1
    assert len(report.unmatched_baseline) == 1
    assert len(report.unmatched_current) == 1


def test_compare_multiple_methods_same_path():
    baseline = [make_record(method="GET", path="/x"), make_record(method="POST", path="/x")]
    current = [make_record(method="GET", path="/x", status=200), make_record(method="POST", path="/x", status=422)]
    report = compare_record_sets(baseline, current)
    assert report.total_compared == 2
    assert report.regression_count == 1


def test_format_report_no_regressions():
    baseline = [make_record()]
    current = [make_record()]
    report = compare_record_sets(baseline, current)
    text = format_comparison_report(report)
    assert "Compared 1" in text
    assert "Regressions (changed): 0" in text


def test_format_report_with_regression():
    baseline = [make_record(status=200)]
    current = [make_record(status=503)]
    report = compare_record_sets(baseline, current)
    text = format_comparison_report(report)
    assert "Regressions (changed): 1" in text


def test_format_report_missing_entries():
    baseline = [make_record(path="/gone")]
    current = [make_record(path="/new")]
    report = compare_record_sets(baseline, current)
    text = format_comparison_report(report)
    assert "Missing from current" in text
    assert "New in current" in text
