"""Tests for reqtrace.cli_archive."""

import uuid
from pathlib import Path

import pytest

from reqtrace.cli_archive import build_archive_parser, run_archive
from reqtrace.storage import LogStorage, RequestRecord


def make_record():
    return RequestRecord(
        id=str(uuid.uuid4()),
        timestamp="2024-01-01T00:00:00",
        method="GET",
        path="/test",
        query_string="",
        request_headers={},
        request_body="",
        status_code=200,
        response_headers={},
        response_body="ok",
        duration=0.05,
    )


def write_records(log_dir, n=2):
    storage = LogStorage(log_dir)
    records = [make_record() for _ in range(n)]
    for r in records:
        storage.save(r)
    return records


def make_args(archive_cmd, **kwargs):
    ns = type("Namespace", (), {"archive_cmd": archive_cmd})()
    for k, v in kwargs.items():
        setattr(ns, k, v)
    return ns


def test_save_creates_zip(tmp_path):
    log_dir = str(tmp_path / "logs")
    write_records(log_dir, 2)
    dest = str(tmp_path / "out.zip")
    args = make_args("save", log_dir=log_dir, dest=dest)
    rc = run_archive(args)
    assert rc == 0
    assert Path(dest).exists()


def test_load_restores_records(tmp_path, capsys):
    log_dir = str(tmp_path / "logs")
    write_records(log_dir, 3)
    dest = str(tmp_path / "out.zip")
    run_archive(make_args("save", log_dir=log_dir, dest=dest))

    new_log_dir = str(tmp_path / "new_logs")
    rc = run_archive(make_args("load", log_dir=new_log_dir, src=dest))
    assert rc == 0
    captured = capsys.readouterr()
    assert "3" in captured.out


def test_list_prints_ids(tmp_path, capsys):
    log_dir = str(tmp_path / "logs")
    records = write_records(log_dir, 2)
    dest = str(tmp_path / "out.zip")
    run_archive(make_args("save", log_dir=log_dir, dest=dest))

    rc = run_archive(make_args("list", src=dest))
    assert rc == 0
    captured = capsys.readouterr()
    for r in records:
        assert r.id in captured.out


def test_list_empty_archive(tmp_path, capsys):
    log_dir = str(tmp_path / "logs")
    LogStorage(log_dir)  # ensure dir created
    dest = str(tmp_path / "empty.zip")
    run_archive(make_args("save", log_dir=log_dir, dest=dest))

    rc = run_archive(make_args("list", src=dest))
    assert rc == 0
    captured = capsys.readouterr()
    assert "empty" in captured.out


def test_parser_builds_without_parent():
    parser = build_archive_parser()
    assert parser is not None
