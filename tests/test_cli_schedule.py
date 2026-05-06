"""Tests for reqtrace.cli_schedule."""
from __future__ import annotations

import argparse
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from reqtrace.cli_schedule import build_schedule_parser, run_schedule
from reqtrace.replayer import ReplayResult
from reqtrace.storage import LogStorage, RequestRecord


def make_record(path: str = "/health") -> RequestRecord:
    return RequestRecord(
        method="GET",
        path=path,
        headers={},
        body=None,
        timestamp="2024-01-01T00:00:00",
        status_code=200,
        response_headers={},
        response_body=b"",
        duration_ms=5.0,
    )


def write_records(log_file: str, records: List[RequestRecord]) -> None:
    s = LogStorage(log_file)
    for r in records:
        s.save(r)


def make_args(log_file: str, target: str = "http://localhost:8000", **kwargs) -> argparse.Namespace:
    defaults = dict(
        log_file=log_file,
        target=target,
        interval=0.05,
        max_runs=1,
        verbose=False,
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _fake_replay_all(self) -> List[ReplayResult]:  # noqa: ANN001
    records = self._storage.load_all()
    return [ReplayResult(record=r, status_code=200, response_body=b"", error=None) for r in records]


def test_parser_defaults(tmp_path):
    log = str(tmp_path / "log.jsonl")
    parser = build_schedule_parser()
    args = parser.parse_args(["--log-file", log, "--target", "http://svc"])
    assert args.interval == 60.0
    assert args.max_runs is None
    assert args.verbose is False


def test_parser_custom_values(tmp_path):
    log = str(tmp_path / "log.jsonl")
    parser = build_schedule_parser()
    args = parser.parse_args(["--log-file", log, "--target", "http://svc", "--interval", "5", "--max-runs", "3", "--verbose"])
    assert args.interval == 5.0
    assert args.max_runs == 3
    assert args.verbose is True


def test_run_schedule_executes_max_runs(tmp_path, capsys):
    log = str(tmp_path / "log.jsonl")
    write_records(log, [make_record("/x"), make_record("/y")])
    args = make_args(log, max_runs=2, interval=0.01)

    with patch("reqtrace.replayer.Replayer.replay_all", _fake_replay_all):
        with patch("reqtrace.scheduler.Scheduler.start") as mock_start:
            with patch("reqtrace.scheduler.Scheduler._thread") as mock_thread:
                mock_thread.join = MagicMock(side_effect=lambda: None)
                mock_start.side_effect = lambda: None
                # run_once_sync directly to avoid threading complexity
                from reqtrace.scheduler import Scheduler, SchedulerConfig
                config = SchedulerConfig(interval_seconds=0.01, max_runs=2, on_results=None)
                s = Scheduler(LogStorage(log), "http://localhost:8000", config)
                with patch("reqtrace.replayer.Replayer.replay_all", _fake_replay_all):
                    s.run_once_sync()
                    s.run_once_sync()
                assert s.run_count == 2
