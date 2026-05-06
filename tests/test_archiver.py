"""Tests for reqtrace.archiver."""

import uuid
from pathlib import Path

import pytest

from reqtrace.archiver import archive, list_archive, restore
from reqtrace.storage import LogStorage, RequestRecord


def make_record(method="GET", path="/api", status=200, duration=0.1) -> RequestRecord:
    return RequestRecord(
        id=str(uuid.uuid4()),
        timestamp="2024-01-01T00:00:00",
        method=method,
        path=path,
        query_string="",
        request_headers={},
        request_body="",
        status_code=status,
        response_headers={},
        response_body="",
        duration=duration,
    )


@pytest.fixture()
def tmp_storage(tmp_path):
    return LogStorage(str(tmp_path / "logs"))


def test_archive_empty_storage(tmp_storage, tmp_path):
    dest = tmp_path / "snap.zip"
    n = archive(tmp_storage, dest)
    assert n == 0
    assert dest.exists()


def test_archive_returns_count(tmp_storage, tmp_path):
    for _ in range(3):
        tmp_storage.save(make_record())
    dest = tmp_path / "snap.zip"
    n = archive(tmp_storage, dest)
    assert n == 3


def test_restore_loads_records(tmp_storage, tmp_path):
    records = [make_record() for _ in range(4)]
    for r in records:
        tmp_storage.save(r)
    dest = tmp_path / "snap.zip"
    archive(tmp_storage, dest)

    new_storage = LogStorage(str(tmp_path / "new_logs"))
    n = restore(dest, new_storage)
    assert n == 4
    loaded = new_storage.load_all()
    assert len(loaded) == 4


def test_restore_skips_duplicates(tmp_storage, tmp_path):
    rec = make_record()
    tmp_storage.save(rec)
    dest = tmp_path / "snap.zip"
    archive(tmp_storage, dest)

    # restore into same storage — record already exists
    n = restore(dest, tmp_storage)
    assert n == 0
    assert len(tmp_storage.load_all()) == 1


def test_list_archive_returns_ids(tmp_storage, tmp_path):
    records = [make_record() for _ in range(2)]
    for r in records:
        tmp_storage.save(r)
    dest = tmp_path / "snap.zip"
    archive(tmp_storage, dest)

    ids = list_archive(dest)
    assert sorted(ids) == sorted(r.id for r in records)


def test_list_archive_empty(tmp_storage, tmp_path):
    dest = tmp_path / "empty.zip"
    archive(tmp_storage, dest)
    assert list_archive(dest) == []


def test_roundtrip_preserves_fields(tmp_storage, tmp_path):
    rec = make_record(method="POST", path="/submit", status=201, duration=0.42)
    tmp_storage.save(rec)
    dest = tmp_path / "rt.zip"
    archive(tmp_storage, dest)

    new_storage = LogStorage(str(tmp_path / "rt_logs"))
    restore(dest, new_storage)
    loaded = new_storage.load_all()[0]
    assert loaded.method == "POST"
    assert loaded.path == "/submit"
    assert loaded.status_code == 201
    assert abs(loaded.duration - 0.42) < 1e-9
