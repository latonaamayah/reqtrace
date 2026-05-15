"""Tests for reqtrace.streamer."""
from __future__ import annotations

import os
import pytest
from datetime import datetime

from reqtrace.storage import RequestRecord, LogStorage
from reqtrace.streamer import StreamConfig, StreamResult, stream_records


def make_record(method="GET", path="/api", status=200, duration=50.0) -> RequestRecord:
    return RequestRecord(
        record_id="id-1",
        timestamp=datetime(2024, 1, 1, 12, 0, 0).isoformat(),
        method=method,
        path=path,
        request_headers={},
        request_body="",
        response_status=status,
        response_headers={},
        response_body="",
        duration_ms=duration,
    )


@pytest.fixture
def tmp_storage(tmp_path):
    return LogStorage(str(tmp_path / "test.log"))


def _collect(storage, config):
    gen = stream_records(storage, config)
    batches = []
    result = StreamResult()
    try:
        while True:
            batches.append(next(gen))
    except StopIteration as exc:
        result = exc.value
    return batches, result


def test_stream_empty_storage(tmp_storage):
    config = StreamConfig(batch_size=5)
    batches, result = _collect(tmp_storage, config)
    assert batches == []
    assert result.total_records == 0
    assert result.batches_yielded == 0


def test_stream_single_batch(tmp_storage):
    for i in range(3):
        r = make_record(path=f"/api/{i}")
        r.record_id = f"id-{i}"
        tmp_storage.save(r)
    config = StreamConfig(batch_size=10)
    batches, result = _collect(tmp_storage, config)
    assert len(batches) == 1
    assert len(batches[0]) == 3
    assert result.total_records == 3
    assert result.batches_yielded == 1


def test_stream_multiple_batches(tmp_storage):
    for i in range(7):
        r = make_record(path=f"/p/{i}")
        r.record_id = f"id-{i}"
        tmp_storage.save(r)
    config = StreamConfig(batch_size=3)
    batches, result = _collect(tmp_storage, config)
    assert result.total_records == 7
    assert result.batches_yielded == 3  # 3+3+1
    assert [len(b) for b in batches] == [3, 3, 1]


def test_stream_max_records(tmp_storage):
    for i in range(10):
        r = make_record(path=f"/p/{i}")
        r.record_id = f"id-{i}"
        tmp_storage.save(r)
    config = StreamConfig(batch_size=4, max_records=5)
    batches, result = _collect(tmp_storage, config)
    assert result.total_records == 5


def test_stream_predicate_filters(tmp_storage):
    for i in range(5):
        r = make_record(method="GET" if i % 2 == 0 else "POST", path=f"/p/{i}")
        r.record_id = f"id-{i}"
        tmp_storage.save(r)
    config = StreamConfig(batch_size=10, predicate=lambda r: r.method == "POST")
    batches, result = _collect(tmp_storage, config)
    assert result.total_records == 2
    assert result.filtered_out == 3


def test_stream_predicate_exception_treated_as_false(tmp_storage):
    r = make_record()
    tmp_storage.save(r)
    def bad_pred(record):
        raise RuntimeError("oops")
    config = StreamConfig(batch_size=5, predicate=bad_pred)
    batches, result = _collect(tmp_storage, config)
    assert result.total_records == 0
    assert result.filtered_out == 1


def test_config_invalid_batch_size_raises():
    with pytest.raises(ValueError, match="batch_size"):
        StreamConfig(batch_size=0)


def test_config_negative_max_records_raises():
    with pytest.raises(ValueError, match="max_records"):
        StreamConfig(max_records=-1)


def test_stream_result_str():
    r = StreamResult(batches_yielded=2, total_records=10, filtered_out=3)
    s = str(r)
    assert "batches=2" in s
    assert "records=10" in s
    assert "filtered_out=3" in s
