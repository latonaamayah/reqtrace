"""Integration tests for cli_ratelimit."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from reqtrace.storage import RequestRecord, LogStorage
from reqtrace.cli_ratelimit import build_ratelimit_parser, run_ratelimit


def make_record(
    method: str = "GET",
    path: str = "/api",
    status: int = 200,
    timestamp: float = 0.0,
) -> RequestRecord:
    return RequestRecord(
        method=method,
        path=path,
        status_code=status,
        request_headers={},
        response_headers={},
        request_body="",
        response_body="",
        duration_ms=10.0,
        timestamp=timestamp,
    )


def write_records(path: str, records) -> None:
    storage = LogStorage(path)
    for r in records:
        storage.save(r)


def make_args(log_file: str, **kwargs):
    parser = build_ratelimit_parser()
    argv = [log_file]
    if "max_rps" in kwargs:
        argv += ["--max-rps", str(kwargs["max_rps"])]
    if kwargs.get("violations_only"):
        argv += ["--violations-only"]
    if "method" in kwargs:
        argv += ["--method", kwargs["method"]]
    if "path_prefix" in kwargs:
        argv += ["--path-prefix", kwargs["path_prefix"]]
    return parser.parse_args(argv)


def test_empty_storage_exits_zero(tmp_path):
    log = str(tmp_path / "log.jsonl")
    args = make_args(log, max_rps=5.0)
    assert run_ratelimit(args) == 0


def test_no_violations_exits_zero(tmp_path):
    log = str(tmp_path / "log.jsonl")
    # 3 requests over 10 seconds => 0.3 rps, well under 5
    records = [make_record(timestamp=float(i * 5)) for i in range(3)]
    write_records(log, records)
    args = make_args(log, max_rps=5.0)
    assert run_ratelimit(args) == 0


def test_violation_exits_nonzero(tmp_path):
    log = str(tmp_path / "log.jsonl")
    # 50 requests in ~0.5 seconds => ~100 rps
    records = [make_record(timestamp=i * 0.01) for i in range(50)]
    write_records(log, records)
    args = make_args(log, max_rps=5.0)
    assert run_ratelimit(args) == 1


def test_violations_only_flag_no_violations(tmp_path, capsys):
    log = str(tmp_path / "log.jsonl")
    records = [make_record(timestamp=float(i * 10)) for i in range(3)]
    write_records(log, records)
    args = make_args(log, max_rps=5.0, violations_only=True)
    rc = run_ratelimit(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "No rate-limit violations" in captured.out


def test_violations_only_flag_with_violations(tmp_path, capsys):
    log = str(tmp_path / "log.jsonl")
    records = [make_record(timestamp=i * 0.01) for i in range(50)]
    write_records(log, records)
    args = make_args(log, max_rps=5.0, violations_only=True)
    rc = run_ratelimit(args)
    assert rc == 1
    captured = capsys.readouterr()
    assert "/api" in captured.out
