"""Tests for reqtrace.cli_stream."""
from __future__ import annotations

import argparse
from datetime import datetime

import pytest

from reqtrace.storage import RequestRecord, LogStorage
from reqtrace.cli_stream import build_stream_parser, run_stream


def make_record(method="GET", path="/api", status=200) -> RequestRecord:
    return RequestRecord(
        record_id="id-1",
        timestamp=datetime(2024, 1, 1, 12, 0, 0).isoformat(),
        method=method,
        path=path,
        request_headers={},
        request_body="",
        response_status=status,
        response_headers={},
        response_body="",
        duration_ms=30.0,
    )


def write_records(storage, records):
    for r in records:
        storage.save(r)


def make_args(log_file, batch_size=10, max_records=None, method=None, status=None, headers=False):
    return argparse.Namespace(
        log_file=log_file,
        batch_size=batch_size,
        max_records=max_records,
        method=method,
        status=status,
        headers=headers,
    )


def test_stream_empty_storage(tmp_path, capsys):
    log = str(tmp_path / "test.log")
    args = make_args(log)
    rc = run_stream(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "StreamResult" in out


def test_stream_outputs_records(tmp_path, capsys):
    log = str(tmp_path / "test.log")
    storage = LogStorage(log)
    r1 = make_record(path="/hello")
    r2 = make_record(path="/world")
    write_records(storage, [r1, r2])
    args = make_args(log, batch_size=5)
    rc = run_stream(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "/hello" in out
    assert "/world" in out


def test_stream_method_filter(tmp_path, capsys):
    log = str(tmp_path / "test.log")
    storage = LogStorage(log)
    r1 = make_record(method="GET", path="/get")
    r2 = make_record(method="POST", path="/post")
    write_records(storage, [r1, r2])
    args = make_args(log, method="POST")
    rc = run_stream(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "/post" in out
    assert "records=1" in out


def test_stream_invalid_batch_size_returns_error(tmp_path, capsys):
    log = str(tmp_path / "test.log")
    args = make_args(log, batch_size=0)
    rc = run_stream(args)
    assert rc == 1
    err = capsys.readouterr().err
    assert "Error" in err


def test_parser_defaults():
    parser = build_stream_parser()
    args = parser.parse_args([])
    assert args.batch_size == 10
    assert args.max_records is None
    assert args.method is None
    assert args.headers is False
