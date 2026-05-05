"""Tests for reqtrace.cli_compare module."""

import json
import os
import pytest
from datetime import datetime
from pathlib import Path

from reqtrace.storage import RequestRecord, LogStorage
from reqtrace.cli_compare import run_compare, build_compare_parser


def make_record(method="GET", path="/api", status=200, duration=0.05):
    return RequestRecord(
        method=method,
        path=path,
        query_string="",
        request_headers={"Host": "localhost"},
        request_body=b"",
        response_status=status,
        response_headers={},
        response_body=b"",
        duration=duration,
        timestamp=datetime(2024, 6, 1).isoformat(),
    )


@pytest.fixture()
def tmp_logs(tmp_path):
    baseline_path = str(tmp_path / "baseline.json")
    current_path = str(tmp_path / "current.json")
    return baseline_path, current_path


def write_records(path, records):
    storage = LogStorage(path)
    for r in records:
        storage.save(r)


def make_args(baseline, current, fail_on_regression=False):
    parser = build_compare_parser()
    argv = [baseline, current]
    if fail_on_regression:
        argv.append("--fail-on-regression")
    return parser.parse_args(argv)


def test_compare_no_regressions_exit_zero(tmp_logs):
    baseline_path, current_path = tmp_logs
    write_records(baseline_path, [make_record()])
    write_records(current_path, [make_record()])
    args = make_args(baseline_path, current_path)
    assert run_compare(args) == 0


def test_compare_regression_exit_zero_without_flag(tmp_logs):
    baseline_path, current_path = tmp_logs
    write_records(baseline_path, [make_record(status=200)])
    write_records(current_path, [make_record(status=500)])
    args = make_args(baseline_path, current_path, fail_on_regression=False)
    assert run_compare(args) == 0


def test_compare_regression_exit_one_with_flag(tmp_logs):
    baseline_path, current_path = tmp_logs
    write_records(baseline_path, [make_record(status=200)])
    write_records(current_path, [make_record(status=500)])
    args = make_args(baseline_path, current_path, fail_on_regression=True)
    assert run_compare(args) == 1


def test_compare_empty_baseline_warns(tmp_logs, capsys):
    baseline_path, current_path = tmp_logs
    # Don't write anything to baseline
    write_records(current_path, [make_record()])
    args = make_args(baseline_path, current_path)
    run_compare(args)
    captured = capsys.readouterr()
    assert "warn" in captured.err


def test_compare_output_contains_summary(tmp_logs, capsys):
    baseline_path, current_path = tmp_logs
    write_records(baseline_path, [make_record()])
    write_records(current_path, [make_record()])
    args = make_args(baseline_path, current_path)
    run_compare(args)
    captured = capsys.readouterr()
    assert "Compared" in captured.out
