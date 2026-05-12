"""Tests for reqtrace.snapshotter."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from reqtrace.snapshotter import (
    SnapshotMeta,
    delete_snapshot,
    list_snapshots,
    load_snapshot,
    save_snapshot,
)
from reqtrace.storage import LogStorage, RequestRecord


def make_record(path: str = "/api/test", method: str = "GET", status: int = 200) -> RequestRecord:
    return RequestRecord(
        timestamp=datetime.now(timezone.utc).isoformat(),
        method=method,
        path=path,
        query_string="",
        request_headers={},
        request_body="",
        status_code=status,
        response_headers={},
        response_body="ok",
        duration_ms=10.0,
    )


@pytest.fixture()
def tmp_dir(tmp_path: Path) -> str:
    return str(tmp_path / "snapshots")


@pytest.fixture()
def tmp_storage(tmp_path: Path) -> LogStorage:
    return LogStorage(str(tmp_path / "reqtrace.log"))


def test_save_snapshot_creates_file(tmp_storage: LogStorage, tmp_dir: str) -> None:
    tmp_storage.save(make_record())
    result = save_snapshot(tmp_storage, "snap1", tmp_dir)
    assert result.record_count == 1
    assert result.name == "snap1"
    assert Path(result.path).exists()


def test_save_snapshot_empty_storage(tmp_storage: LogStorage, tmp_dir: str) -> None:
    result = save_snapshot(tmp_storage, "empty", tmp_dir)
    assert result.record_count == 0


def test_load_snapshot_returns_records(tmp_storage: LogStorage, tmp_dir: str) -> None:
    tmp_storage.save(make_record("/a"))
    tmp_storage.save(make_record("/b"))
    save_snapshot(tmp_storage, "two", tmp_dir)
    records = load_snapshot("two", tmp_dir)
    assert len(records) == 2
    paths = {r.path for r in records}
    assert paths == {"/a", "/b"}


def test_load_snapshot_missing_raises(tmp_dir: str) -> None:
    with pytest.raises(FileNotFoundError, match="ghost"):
        load_snapshot("ghost", tmp_dir)


def test_list_snapshots_empty_dir(tmp_dir: str) -> None:
    metas = list_snapshots(tmp_dir)
    assert metas == []


def test_list_snapshots_returns_metadata(tmp_storage: LogStorage, tmp_dir: str) -> None:
    tmp_storage.save(make_record())
    save_snapshot(tmp_storage, "alpha", tmp_dir)
    save_snapshot(tmp_storage, "beta", tmp_dir)
    metas = list_snapshots(tmp_dir)
    names = [m.name for m in metas]
    assert "alpha" in names
    assert "beta" in names
    for m in metas:
        assert isinstance(m, SnapshotMeta)
        assert m.record_count == 1


def test_delete_snapshot_removes_file(tmp_storage: LogStorage, tmp_dir: str) -> None:
    save_snapshot(tmp_storage, "del_me", tmp_dir)
    removed = delete_snapshot("del_me", tmp_dir)
    assert removed is True
    assert list_snapshots(tmp_dir) == []


def test_delete_snapshot_missing_returns_false(tmp_dir: str) -> None:
    assert delete_snapshot("nope", tmp_dir) is False


def test_snapshot_str(tmp_storage: LogStorage, tmp_dir: str) -> None:
    save_snapshot(tmp_storage, "s1", tmp_dir)
    metas = list_snapshots(tmp_dir)
    assert "s1" in str(metas[0])
