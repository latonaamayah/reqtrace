"""Tests for reqtrace.retrier."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from unittest.mock import MagicMock

import pytest

from reqtrace.replayer import ReplayResult
from reqtrace.retrier import RetryConfig, Retrier
from reqtrace.storage import RequestRecord


def make_record(**kwargs) -> RequestRecord:
    defaults = dict(
        record_id="abc",
        method="GET",
        url="http://localhost/test",
        path="/test",
        headers={},
        body=None,
        timestamp=datetime.now(timezone.utc).isoformat(),
        duration_ms=50.0,
        status_code=200,
        response_headers={},
        response_body=b"ok",
    )
    defaults.update(kwargs)
    return RequestRecord(**defaults)


def make_result(status_code: int = 200, error: str = None) -> ReplayResult:
    return ReplayResult(
        record_id="abc",
        status_code=status_code,
        response_body=b"body",
        error=error,
    )


@pytest.fixture
def slept() -> List[float]:
    return []


@pytest.fixture
def mock_replayer():
    return MagicMock()


def test_retry_succeeds_on_first_attempt(mock_replayer, slept):
    mock_replayer.replay.return_value = make_result(200)
    retrier = Retrier(mock_replayer, sleep_fn=slept.append)
    outcome = retrier.retry(make_record())
    assert outcome.succeeded
    assert outcome.attempts == 1
    assert len(slept) == 0


def test_retry_retries_on_500(mock_replayer, slept):
    mock_replayer.replay.side_effect = [make_result(500), make_result(200)]
    retrier = Retrier(mock_replayer, sleep_fn=slept.append)
    outcome = retrier.retry(make_record())
    assert outcome.succeeded
    assert outcome.attempts == 2
    assert len(slept) == 1


def test_retry_exhausts_all_attempts(mock_replayer, slept):
    mock_replayer.replay.return_value = make_result(503)
    cfg = RetryConfig(max_attempts=3, backoff_base=0.1)
    retrier = Retrier(mock_replayer, config=cfg, sleep_fn=slept.append)
    outcome = retrier.retry(make_record())
    assert not outcome.succeeded
    assert outcome.attempts == 3
    assert len(slept) == 2


def test_retry_on_exception(mock_replayer, slept):
    mock_replayer.replay.side_effect = [
        make_result(error="connection refused"),
        make_result(200),
    ]
    retrier = Retrier(mock_replayer, sleep_fn=slept.append)
    outcome = retrier.retry(make_record())
    assert outcome.succeeded
    assert outcome.attempts == 2


def test_no_retry_on_exception_when_disabled(mock_replayer, slept):
    mock_replayer.replay.return_value = make_result(error="timeout")
    cfg = RetryConfig(retry_on_exception=False)
    retrier = Retrier(mock_replayer, config=cfg, sleep_fn=slept.append)
    outcome = retrier.retry(make_record())
    assert not outcome.succeeded
    assert outcome.attempts == 1


def test_retry_all(mock_replayer, slept):
    mock_replayer.replay.return_value = make_result(200)
    retrier = Retrier(mock_replayer, sleep_fn=slept.append)
    records = [make_record(record_id=str(i)) for i in range(3)]
    outcomes = retrier.retry_all(records)
    assert len(outcomes) == 3
    assert all(o.succeeded for o in outcomes)


def test_retry_outcome_str(mock_replayer, slept):
    mock_replayer.replay.return_value = make_result(200)
    retrier = Retrier(mock_replayer, sleep_fn=slept.append)
    outcome = retrier.retry(make_record())
    assert "OK" in str(outcome)
    assert "attempts=1" in str(outcome)


def test_backoff_multiplier(mock_replayer, slept):
    mock_replayer.replay.return_value = make_result(502)
    cfg = RetryConfig(max_attempts=4, backoff_base=1.0, backoff_multiplier=3.0)
    retrier = Retrier(mock_replayer, config=cfg, sleep_fn=slept.append)
    retrier.retry(make_record())
    assert slept == pytest.approx([1.0, 3.0, 9.0])
