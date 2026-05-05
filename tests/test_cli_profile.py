"""Tests for reqtrace.cli_profile."""
import io
import os
import pytest

from reqtrace.storage import LogStorage, RequestRecord
from reqtrace.cli_profile import build_profile_parser, run_profile


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


@pytest.fixture()
def tmp_logs(tmp_path):
    return str(tmp_path / "logs")


def write_records(log_dir, records):
    storage = LogStorage(log_dir)
    for r in records:
        storage.save(r)


def make_args(log_dir, method=None, path_prefix=None, status=None, by_path=False):
    parser = build_profile_parser()
    argv = ["--log-dir", log_dir]
    if method:
        argv += ["--method", method]
    if path_prefix:
        argv += ["--path-prefix", path_prefix]
    if status:
        argv += ["--status", str(status)]
    if by_path:
        argv.append("--by-path")
    return parser.parse_args(argv)


def test_profile_empty_storage(tmp_logs):
    os.makedirs(tmp_logs, exist_ok=True)
    args = make_args(tmp_logs)
    out = io.StringIO()
    rc = run_profile(args, out=out)
    assert rc == 0
    assert "No records found" in out.getvalue()


def test_profile_basic_stats(tmp_logs):
    write_records(tmp_logs, [
        make_record(duration_ms=100.0),
        make_record(duration_ms=200.0),
        make_record(duration_ms=300.0),
    ])
    args = make_args(tmp_logs)
    out = io.StringIO()
    rc = run_profile(args, out=out)
    assert rc == 0
    text = out.getvalue()
    assert "count=3" in text
    assert "min=" in text
    assert "p90=" in text


def test_profile_filter_by_method(tmp_logs):
    write_records(tmp_logs, [
        make_record(method="GET", duration_ms=50.0),
        make_record(method="POST", duration_ms=500.0),
    ])
    args = make_args(tmp_logs, method="GET")
    out = io.StringIO()
    run_profile(args, out=out)
    assert "count=1" in out.getvalue()


def test_profile_by_path_breakdown(tmp_logs):
    write_records(tmp_logs, [
        make_record(method="GET", path="/a", duration_ms=100.0),
        make_record(method="GET", path="/a", duration_ms=200.0),
        make_record(method="POST", path="/b", duration_ms=50.0),
    ])
    args = make_args(tmp_logs, by_path=True)
    out = io.StringIO()
    rc = run_profile(args, out=out)
    assert rc == 0
    text = out.getvalue()
    assert "GET /a" in text
    assert "POST /b" in text


def test_profile_filter_no_match(tmp_logs):
    write_records(tmp_logs, [make_record(method="GET")])
    args = make_args(tmp_logs, method="DELETE")
    out = io.StringIO()
    rc = run_profile(args, out=out)
    assert rc == 0
    assert "No records found" in out.getvalue()
