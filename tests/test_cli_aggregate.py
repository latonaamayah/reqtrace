"""Tests for reqtrace.cli_aggregate."""
from __future__ import annotations

import datetime
import io
import json
import os
import tempfile

import pytest

from reqtrace.cli_aggregate import build_aggregate_parser, run_aggregate
from reqtrace.storage import LogStorage, RequestRecord


def make_record(method="GET", path="/api", status_code=200, duration_ms=30.0) -> RequestRecord:
    return RequestRecord(
        record_id="r1",
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


def write_records(path: str, records) -> None:
    storage = LogStorage(path)
    for r in records:
        storage.save(r)


def make_args(log_file, method=None, path_prefix=None, sort="count", top=0):
    parser = build_aggregate_parser()
    argv = ["--log-file", log_file, "--sort", sort, "--top", str(top)]
    if method:
        argv += ["--method", method]
    if path_prefix:
        argv += ["--path-prefix", path_prefix]
    return parser.parse_args(argv)


def test_aggregate_empty_storage():
    with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
        path = f.name
    try:
        out = io.StringIO()
        args = make_args(path)
        run_aggregate(args, out=out)
        assert "No records found" in out.getvalue()
    finally:
        os.unlink(path)


def test_aggregate_shows_endpoint():
    with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
        path = f.name
    try:
        write_records(path, [make_record(method="GET", path="/health")])
        out = io.StringIO()
        args = make_args(path)
        run_aggregate(args, out=out)
        text = out.getvalue()
        assert "GET" in text
        assert "/health" in text
    finally:
        os.unlink(path)


def test_aggregate_top_limits_output():
    with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
        path = f.name
    try:
        records = [
            make_record(path="/a"),
            make_record(path="/b"),
            make_record(path="/c"),
        ]
        write_records(path, records)
        out = io.StringIO()
        args = make_args(path, top=2)
        run_aggregate(args, out=out)
        lines = [l for l in out.getvalue().splitlines() if l.startswith("  ")]
        assert len(lines) == 2
    finally:
        os.unlink(path)


def test_aggregate_filter_by_method():
    with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
        path = f.name
    try:
        write_records(path, [
            make_record(method="GET", path="/x"),
            make_record(method="POST", path="/y"),
        ])
        out = io.StringIO()
        args = make_args(path, method="POST")
        run_aggregate(args, out=out)
        text = out.getvalue()
        assert "POST" in text
        assert "GET" not in text
    finally:
        os.unlink(path)
