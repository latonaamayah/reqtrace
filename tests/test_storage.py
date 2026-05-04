"""Tests for the LogStorage and RequestRecord classes."""

import time
import uuid
import pytest
from pathlib import Path

from reqtrace.storage import LogStorage, RequestRecord


def make_record(**kwargs) -> RequestRecord:
    defaults = dict(
        id=str(uuid.uuid4()),
        timestamp=time.time(),
        method="GET",
        url="http://localhost:8080/api/users",
        request_headers={"Accept": "application/json"},
        request_body=None,
        response_status=200,
        response_headers={"Content-Type": "application/json"},
        response_body='{"users": []}',
        duration_ms=42.3,
        tags=[],
    )
    defaults.update(kwargs)
    return RequestRecord(**defaults)


@pytest.fixture
def storage(tmp_path):
    return LogStorage(log_dir=str(tmp_path / ".reqtrace"))


def test_save_and_load_all(storage):
    record = make_record()
    storage.save(record)
    records = storage.load_all()
    assert len(records) == 1
    assert records[0].id == record.id
    assert records[0].url == record.url


def test_load_all_empty(storage):
    assert storage.load_all() == []


def test_multiple_records_preserved(storage):
    r1 = make_record(method="GET")
    r2 = make_record(method="POST", url="http://localhost:8080/api/users")
    storage.save(r1)
    storage.save(r2)
    records = storage.load_all()
    assert len(records) == 2
    assert records[0].method == "GET"
    assert records[1].method == "POST"


def test_find_by_id_found(storage):
    record = make_record()
    storage.save(record)
    found = storage.find_by_id(record.id)
    assert found is not None
    assert found.id == record.id


def test_find_by_id_not_found(storage):
    assert storage.find_by_id("nonexistent-id") is None


def test_clear(storage):
    storage.save(make_record())
    storage.clear()
    assert storage.load_all() == []


def test_count(storage):
    assert storage.count() == 0
    storage.save(make_record())
    storage.save(make_record())
    assert storage.count() == 2


def test_record_roundtrip():
    original = make_record(tags=["auth", "slow"], response_status=404)
    restored = RequestRecord.from_dict(original.to_dict())
    assert restored.id == original.id
    assert restored.tags == ["auth", "slow"]
    assert restored.response_status == 404
