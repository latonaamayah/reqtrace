"""Tests for reqtrace.scheduler."""
from __future__ import annotations

import os
import tempfile
import time
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from reqtrace.replayer import ReplayResult
from reqtrace.scheduler import Scheduler, SchedulerConfig
from reqtrace.storage import LogStorage, RequestRecord


def make_record(path: str = "/ping", method: str = "GET") -> RequestRecord:
    return RequestRecord(
        method=method,
        path=path,
        headers={},
        body=None,
        timestamp="2024-01-01T00:00:00",
        status_code=200,
        response_headers={},
        response_body=b"",
        duration_ms=10.0,
    )


@pytest.fixture()
def tmp_storage(tmp_path):
    log_file = str(tmp_path / "log.jsonl")
    s = LogStorage(log_file)
    s.save(make_record("/a"))
    s.save(make_record("/b"))
    return s


def _fake_replay_all(self) -> List[ReplayResult]:  # noqa: ANN001
    records = self._storage.load_all()
    return [ReplayResult(record=r, status_code=200, response_body=b"", error=None) for r in records]


def test_run_once_sync_returns_results(tmp_storage):
    config = SchedulerConfig(interval_seconds=1)
    scheduler = Scheduler(tmp_storage, "http://localhost:9999", config)
    with patch("reqtrace.replayer.Replayer.replay_all", _fake_replay_all):
        results = scheduler.run_once_sync()
    assert len(results) == 2
    assert scheduler.run_count == 1


def test_on_results_callback_called(tmp_storage):
    collected: List[List[ReplayResult]] = []
    config = SchedulerConfig(interval_seconds=1, on_results=lambda r: collected.append(r))
    scheduler = Scheduler(tmp_storage, "http://localhost:9999", config)
    with patch("reqtrace.replayer.Replayer.replay_all", _fake_replay_all):
        scheduler.run_once_sync()
    assert len(collected) == 1
    assert len(collected[0]) == 2


def test_max_runs_stops_loop(tmp_storage):
    config = SchedulerConfig(interval_seconds=0.01, max_runs=2)
    scheduler = Scheduler(tmp_storage, "http://localhost:9999", config)
    with patch("reqtrace.replayer.Replayer.replay_all", _fake_replay_all):
        scheduler.start()
        scheduler._thread.join(timeout=3)
    assert scheduler.run_count == 2


def test_stop_halts_scheduler(tmp_storage):
    config = SchedulerConfig(interval_seconds=60)
    scheduler = Scheduler(tmp_storage, "http://localhost:9999", config)
    with patch("reqtrace.replayer.Replayer.replay_all", _fake_replay_all):
        scheduler.start()
        time.sleep(0.05)
        scheduler.stop()
    assert scheduler.run_count >= 1


def test_invalid_interval_raises():
    with pytest.raises(ValueError, match="interval_seconds must be positive"):
        SchedulerConfig(interval_seconds=0)


def test_last_results_updated(tmp_storage):
    config = SchedulerConfig(interval_seconds=1)
    scheduler = Scheduler(tmp_storage, "http://localhost:9999", config)
    assert scheduler.last_results == []
    with patch("reqtrace.replayer.Replayer.replay_all", _fake_replay_all):
        scheduler.run_once_sync()
    assert len(scheduler.last_results) == 2
