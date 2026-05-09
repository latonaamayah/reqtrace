"""Tests for reqtrace.cli_validate."""
from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime
from pathlib import Path

import pytest

from reqtrace.storage import RequestRecord
from reqtrace.cli_validate import build_validate_parser, run_validate


def make_record(
    status_code: int = 200,
    duration_ms: float = 50.0,
    path: str = "/api/ping",
) -> RequestRecord:
    return RequestRecord(
        record_id=str(uuid.uuid4()),
        timestamp=datetime.utcnow().isoformat(),
        method="GET",
        path=path,
        query_string="",
        request_headers={},
        request_body="",
        status_code=status_code,
        response_headers={},
        response_body="",
        duration_ms=duration_ms,
    )


def write_records(path: Path, records):
    from reqtrace.storage import to_dict
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(to_dict(r)) + "\n")


def make_args(log_file: str, **kwargs) -> argparse.Namespace:
    defaults = dict(
        log_file=log_file,
        method=None,
        path_prefix=None,
        max_duration=None,
        no_5xx=True,
        exit_nonzero=False,
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_validate_all_ok(tmp_path, capsys):
    log = tmp_path / "log.jsonl"
    write_records(log, [make_record(), make_record(status_code=201)])
    args = make_args(str(log))
    rc = run_validate(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "passed" in out.lower()


def test_validate_detects_500(tmp_path, capsys):
    log = tmp_path / "log.jsonl"
    write_records(log, [make_record(status_code=500)])
    args = make_args(str(log), exit_nonzero=True)
    rc = run_validate(args)
    assert rc == 1
    out = capsys.readouterr().out
    assert "no_server_error" in out


def test_validate_duration_rule(tmp_path, capsys):
    log = tmp_path / "log.jsonl"
    write_records(log, [make_record(duration_ms=9999.0)])
    args = make_args(str(log), max_duration=100.0, exit_nonzero=True)
    rc = run_validate(args)
    assert rc == 1
    out = capsys.readouterr().out
    assert "duration" in out


def test_validate_empty_storage(tmp_path, capsys):
    log = tmp_path / "log.jsonl"
    log.write_text("")
    args = make_args(str(log))
    rc = run_validate(args)
    assert rc == 0


def test_parser_builds_correctly():
    parser = build_validate_parser()
    args = parser.parse_args(["my.log", "--max-duration", "250", "--exit-nonzero"])
    assert args.log_file == "my.log"
    assert args.max_duration == 250.0
    assert args.exit_nonzero is True
