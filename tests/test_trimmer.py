"""Tests for reqtrace.trimmer."""
from __future__ import annotations

import datetime
import pytest

from reqtrace.storage import LogStorage, RequestRecord
from reqtrace.trimmer import TrimResult, trim


def make_record(n: int) -> RequestRecord:
    return RequestRecord(
        record_id=f"id-{n}",
        timestamp=datetime.datetime(2024, 1, 1, 0, 0, n, tzinfo=datetime.timezone.utc).isoformat(),
        method="GET",
        path=f"/path/{n}",
        status_code=200,
        request_headers={},
        response_headers={},
        request_body="",
        response_body="",
        duration_ms=10.0,
    )


@pytest.fixture()
def tmp_storage(tmp_path):
    return LogStorage(tmp_path / "log.jsonl")


def test_trim_empty_storage(tmp_storage):
    result = trim(tmp_storage, keep=5)
    assert result.total_before == 0
    assert result.kept == 0
    assert result.removed == 0


def test_trim_keep_more_than_available(tmp_storage):
    for i in range(3):
        tmp_storage.save(make_record(i))
    result = trim(tmp_storage, keep=10)
    assert result.total_before == 3
    assert result.kept == 3
    assert result.removed == 0
    assert len(tmp_storage.load_all()) == 3


def test_trim_keeps_newest_by_default(tmp_storage):
    for i in range(5):
        tmp_storage.save(make_record(i))
    result = trim(tmp_storage, keep=3)
    assert result.total_before == 5
    assert result.kept == 3
    assert result.removed == 2
    remaining = tmp_storage.load_all()
    assert len(remaining) == 3
    paths = {r.path for r in remaining}
    assert "/path/2" in paths
    assert "/path/3" in paths
    assert "/path/4" in paths


def test_trim_keeps_oldest_when_newest_first_false(tmp_storage):
    for i in range(5):
        tmp_storage.save(make_record(i))
    result = trim(tmp_storage, keep=2, newest_first=False)
    assert result.kept == 2
    remaining = tmp_storage.load_all()
    paths = {r.path for r in remaining}
    assert "/path/0" in paths
    assert "/path/1" in paths


def test_trim_keep_zero_removes_all(tmp_storage):
    for i in range(4):
        tmp_storage.save(make_record(i))
    result = trim(tmp_storage, keep=0)
    assert result.kept == 0
    assert result.removed == 4
    assert tmp_storage.load_all() == []


def test_trim_negative_keep_raises(tmp_storage):
    with pytest.raises(ValueError, match="keep must be >= 0"):
        trim(tmp_storage, keep=-1)


def test_trim_result_str():
    r = TrimResult(kept=3, removed=2, total_before=5)
    assert "5" in str(r)
    assert "3" in str(r)
    assert "2" in str(r)
