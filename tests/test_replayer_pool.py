"""Tests for reqtrace.replayer_pool."""
from __future__ import annotations

import pytest

from reqtrace.replayer import ReplayResult
from reqtrace.replayer_pool import PoolConfig, PoolResult, replay_pool
from reqtrace.storage import RequestRecord


def make_record(
    method: str = "GET",
    path: str = "/api/test",
    status: int = 200,
) -> RequestRecord:
    return RequestRecord(
        id="rec-1",
        timestamp="2024-01-01T00:00:00",
        method=method,
        path=path,
        request_headers={},
        request_body="",
        response_status=status,
        response_headers={},
        response_body="ok",
        duration_ms=10.0,
    )


def _make_result(record: RequestRecord, status: int = 200) -> ReplayResult:
    return ReplayResult(record=record, status_code=status, body="ok", duration_ms=5.0)


# --- PoolConfig ---

def test_config_defaults():
    cfg = PoolConfig()
    assert cfg.max_workers == 4
    assert cfg.timeout_seconds == 10.0


def test_config_invalid_workers_raises():
    with pytest.raises(ValueError, match="max_workers"):
        PoolConfig(max_workers=0)


def test_config_invalid_timeout_raises():
    with pytest.raises(ValueError, match="timeout_seconds"):
        PoolConfig(timeout_seconds=0.0)


# --- PoolResult ---

def test_pool_result_success_count():
    rec = make_record()
    pr = PoolResult(results=[_make_result(rec, 200), _make_result(rec, 404)])
    assert pr.success_count == 2


def test_pool_result_error_count():
    pr = PoolResult(errors=["timeout", "connection refused"])
    assert pr.error_count == 2


def test_pool_result_str():
    rec = make_record()
    pr = PoolResult(results=[_make_result(rec)], errors=["oops"])
    text = str(pr)
    assert "PoolResult" in text
    assert "errors=1" in text


# --- replay_pool ---

def test_replay_pool_empty_records():
    result = replay_pool([], base_url="http://localhost:9999")
    assert result.success_count == 0
    assert result.error_count == 0


def test_replay_pool_on_result_callback(monkeypatch):
    """on_result callback is invoked for each successful replay."""
    rec = make_record()
    collected = []

    def fake_replay(self, record):
        return _make_result(record, 200)

    from reqtrace import replayer as _replayer_mod
    monkeypatch.setattr(_replayer_mod.Replayer, "replay", fake_replay)

    replay_pool([rec, rec], base_url="http://localhost:8080", on_result=collected.append)
    assert len(collected) == 2


def test_replay_pool_captures_errors(monkeypatch):
    """Exceptions from replayer are collected as errors, not raised."""
    rec = make_record()

    def boom(self, record):
        raise ConnectionError("refused")

    from reqtrace import replayer as _replayer_mod
    monkeypatch.setattr(_replayer_mod.Replayer, "replay", boom)

    result = replay_pool([rec], base_url="http://localhost:8080")
    assert result.error_count == 1
    assert "ConnectionError" in result.errors[0]
