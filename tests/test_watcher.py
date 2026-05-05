"""Tests for reqtrace.watcher.StorageWatcher."""

import time
import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from reqtrace.storage import LogStorage, RequestRecord
from reqtrace.watcher import StorageWatcher


@pytest.fixture
def tmp_storage(tmp_path):
    return LogStorage(str(tmp_path / "log.json"))


def make_record(method="GET", path="/test", status=200):
    return RequestRecord(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        method=method,
        path=path,
        query_string="",
        request_headers={},
        request_body="",
        status_code=status,
        response_headers={},
        response_body="",
        duration_ms=10.0,
    )


def test_watcher_detects_new_record(tmp_storage):
    callback = MagicMock()
    watcher = StorageWatcher(tmp_storage, callback, poll_interval=0.1)
    watcher.start()
    time.sleep(0.05)

    record = make_record()
    tmp_storage.save(record)

    time.sleep(0.4)
    watcher.stop()

    callback.assert_called_once()
    assert callback.call_args[0][0].id == record.id


def test_watcher_ignores_existing_records(tmp_storage):
    existing = make_record(path="/existing")
    tmp_storage.save(existing)

    callback = MagicMock()
    watcher = StorageWatcher(tmp_storage, callback, poll_interval=0.1)
    watcher.start()
    time.sleep(0.35)
    watcher.stop()

    callback.assert_not_called()


def test_watcher_detects_multiple_new_records(tmp_storage):
    callback = MagicMock()
    watcher = StorageWatcher(tmp_storage, callback, poll_interval=0.1)
    watcher.start()
    time.sleep(0.05)

    r1, r2 = make_record(path="/a"), make_record(path="/b")
    tmp_storage.save(r1)
    tmp_storage.save(r2)

    time.sleep(0.4)
    watcher.stop()

    assert callback.call_count == 2


def test_watcher_context_manager(tmp_storage):
    callback = MagicMock()
    with StorageWatcher(tmp_storage, callback, poll_interval=0.1) as watcher:
        assert watcher._thread is not None
        assert watcher._thread.is_alive()
    assert not watcher._thread


def test_watcher_stop_is_idempotent(tmp_storage):
    callback = MagicMock()
    watcher = StorageWatcher(tmp_storage, callback, poll_interval=0.1)
    watcher.start()
    watcher.stop()
    watcher.stop()  # Should not raise
