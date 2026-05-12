"""Tests for reqtrace.cli_snapshot."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from reqtrace.cli_snapshot import build_snapshot_parser, run_snapshot
from reqtrace.snapshotter import save_snapshot
from reqtrace.storage import LogStorage, RequestRecord


def make_record(path: str = "/x") -> RequestRecord:
    return RequestRecord(
        timestamp=datetime.now(timezone.utc).isoformat(),
        method="GET",
        path=path,
        query_string="",
        request_headers={},
        request_body="",
        status_code=200,
        response_headers={},
        response_body="",
        duration_ms=5.0,
    )


def make_args(snapshot_dir: str, log_file: str, snapshot_cmd: str, name: str = "") -> argparse.Namespace:
    return argparse.Namespace(
        snapshot_cmd=snapshot_cmd,
        name=name,
        log_file=log_file,
        snapshot_dir=snapshot_dir,
    )


@pytest.fixture()
def tmp_storage(tmp_path: Path) -> LogStorage:
    s = LogStorage(str(tmp_path / "reqtrace.log"))
    s.save(make_record("/hello"))
    return s


@pytest.fixture()
def snap_dir(tmp_path: Path) -> str:
    return str(tmp_path / "snaps")


def test_save_creates_snapshot(tmp_storage: LogStorage, snap_dir: str) -> None:
    args = make_args(snap_dir, tmp_storage.path, "save", "mysnap")
    code = run_snapshot(args)
    assert code == 0
    assert (Path(snap_dir) / "mysnap.snapshot.json").exists()


def test_list_shows_snapshot(tmp_storage: LogStorage, snap_dir: str, capsys) -> None:
    save_snapshot(tmp_storage, "listed", snap_dir)
    args = make_args(snap_dir, tmp_storage.path, "list")
    code = run_snapshot(args)
    assert code == 0
    out = capsys.readouterr().out
    assert "listed" in out


def test_list_empty_dir(snap_dir: str, capsys) -> None:
    args = make_args(snap_dir, "", "list")
    code = run_snapshot(args)
    assert code == 0
    assert "No snapshots" in capsys.readouterr().out


def test_load_prints_records(tmp_storage: LogStorage, snap_dir: str, capsys) -> None:
    save_snapshot(tmp_storage, "loaded", snap_dir)
    args = make_args(snap_dir, tmp_storage.path, "load", "loaded")
    code = run_snapshot(args)
    assert code == 0
    out = capsys.readouterr().out
    assert "/hello" in out


def test_load_missing_returns_1(snap_dir: str, capsys) -> None:
    args = make_args(snap_dir, "", "load", "ghost")
    code = run_snapshot(args)
    assert code == 1


def test_delete_removes_snapshot(tmp_storage: LogStorage, snap_dir: str, capsys) -> None:
    save_snapshot(tmp_storage, "todel", snap_dir)
    args = make_args(snap_dir, "", "delete", "todel")
    code = run_snapshot(args)
    assert code == 0
    assert "deleted" in capsys.readouterr().out


def test_delete_missing_returns_1(snap_dir: str, capsys) -> None:
    args = make_args(snap_dir, "", "delete", "nope")
    code = run_snapshot(args)
    assert code == 1
