"""Tests for reqtrace.cli_label."""
import json
import os
import pytest

from reqtrace.storage import RequestRecord, LogStorage
from reqtrace.cli_label import build_label_parser, run_label


def make_record(rid="r1", method="GET", path="/x", status_code=200, duration_ms=50.0) -> RequestRecord:
    return RequestRecord(
        id=rid,
        timestamp="2024-01-01T00:00:00",
        method=method,
        path=path,
        query_string="",
        request_headers={},
        request_body="",
        status_code=status_code,
        response_headers={},
        response_body="",
        duration_ms=duration_ms,
    )


def write_records(path, records):
    storage = LogStorage(path)
    for rec in records:
        storage.save(rec)


def make_args(log_file, output="summary", slow_threshold=1000.0):
    parser = build_label_parser()
    return parser.parse_args([log_file, "--output", output, "--slow-threshold", str(slow_threshold)])


def test_label_empty_storage(tmp_path, capsys):
    log = str(tmp_path / "log.jsonl")
    args = make_args(log)
    ret = run_label(args)
    assert ret == 0
    out = capsys.readouterr().out
    assert "No records" in out


def test_label_summary_output(tmp_path, capsys):
    log = str(tmp_path / "log.jsonl")
    records = [
        make_record("r1", status_code=500, duration_ms=2000),
        make_record("r2", status_code=200, duration_ms=50),
    ]
    write_records(log, records)
    args = make_args(log)
    ret = run_label(args)
    assert ret == 0
    out = capsys.readouterr().out
    assert "error" in out
    assert "slow" in out


def test_label_json_output(tmp_path, capsys):
    log = str(tmp_path / "log.jsonl")
    records = [make_record("r1", status_code=404)]
    write_records(log, records)
    args = make_args(log, output="json")
    ret = run_label(args)
    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    assert "label_counts" in payload
    assert "records" in payload
    assert payload["records"][0]["id"] == "r1"


def test_label_custom_slow_threshold(tmp_path, capsys):
    log = str(tmp_path / "log.jsonl")
    records = [make_record("r1", duration_ms=300)]
    write_records(log, records)
    # With threshold=200, this record should be labeled slow
    args = make_args(log, output="json", slow_threshold=200)
    run_label(args)
    payload = json.loads(capsys.readouterr().out)
    r1_labels = next(r["labels"] for r in payload["records"] if r["id"] == "r1")
    assert "slow" in r1_labels


def test_label_mutation_method(tmp_path, capsys):
    log = str(tmp_path / "log.jsonl")
    records = [make_record("r1", method="DELETE")]
    write_records(log, records)
    args = make_args(log, output="json")
    run_label(args)
    payload = json.loads(capsys.readouterr().out)
    r1_labels = payload["records"][0]["labels"]
    assert "mutation" in r1_labels
