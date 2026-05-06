"""Tests for reqtrace.cli_dedup."""
from __future__ import annotations

import argparse
import os

import pytest

from reqtrace.cli_dedup import build_dedup_parser, run_dedup
from reqtrace.storage import LogStorage, RequestRecord


def make_record(path: str = "/api/test", ts: str = "2024-01-01T00:00:00") -> RequestRecord:
    return RequestRecord(
        timestamp=ts,
        method="GET",
        path=path,
        query_string="",
        request_headers={"host": "localhost"},
        request_body="",
        response_status=200,
        response_headers={},
        response_body="ok",
        duration_ms=5.0,
    )


def write_records(path: str, records) -> None:
    s = LogStorage(path)
    for r in records:
        s.save(r)


def make_args(log_file: str, dry_run: bool = False, show_groups: bool = False) -> argparse.Namespace:
    return argparse.Namespace(log_file=log_file, dry_run=dry_run, show_groups=show_groups)


def test_dedup_empty_storage(tmp_path):
    log = str(tmp_path / "log.jsonl")
    LogStorage(log)  # creates empty file implicitly on first save; file doesn't exist yet
    # Write nothing — run_dedup should handle missing/empty gracefully
    log_file = str(tmp_path / "empty.jsonl")
    open(log_file, "w").close()
    args = make_args(log_file)
    rc = run_dedup(args)
    assert rc == 0


def test_dedup_no_duplicates(tmp_path):
    log = str(tmp_path / "log.jsonl")
    records = [make_record(path=f"/api/{i}") for i in range(4)]
    write_records(log, records)
    args = make_args(log)
    rc = run_dedup(args)
    assert rc == 0
    result = LogStorage(log).load_all()
    assert len(result) == 4


def test_dedup_removes_duplicates(tmp_path):
    log = str(tmp_path / "log.jsonl")
    r1 = make_record(ts="2024-01-01T00:00:00")
    r2 = make_record(ts="2024-01-01T01:00:00")  # same fingerprint
    r3 = make_record(path="/other")
    write_records(log, [r1, r2, r3])
    args = make_args(log)
    rc = run_dedup(args)
    assert rc == 0
    result = LogStorage(log).load_all()
    assert len(result) == 2


def test_dedup_dry_run_does_not_modify(tmp_path):
    log = str(tmp_path / "log.jsonl")
    r1 = make_record(ts="T1")
    r2 = make_record(ts="T2")  # duplicate
    write_records(log, [r1, r2])
    args = make_args(log, dry_run=True)
    rc = run_dedup(args)
    assert rc == 0
    result = LogStorage(log).load_all()
    assert len(result) == 2  # unchanged


def test_dedup_show_groups_flag(tmp_path, capsys):
    log = str(tmp_path / "log.jsonl")
    r1 = make_record(ts="T1")
    r2 = make_record(ts="T2")
    write_records(log, [r1, r2])
    args = make_args(log, show_groups=True)
    run_dedup(args)
    captured = capsys.readouterr()
    assert "Duplicate group" in captured.out


def test_build_dedup_parser_returns_parser():
    parser = build_dedup_parser()
    assert isinstance(parser, argparse.ArgumentParser)
    args = parser.parse_args(["myfile.jsonl", "--dry-run"])
    assert args.log_file == "myfile.jsonl"
    assert args.dry_run is True
