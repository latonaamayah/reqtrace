"""Tests for reqtrace.scorer module."""

import pytest
from datetime import datetime, timezone
from reqtrace.storage import RequestRecord
from reqtrace.scorer import score_record, score_all, ScoreResult


def make_record(
    method="GET",
    path="/api/test",
    status=200,
    duration_ms=100,
    body="",
):
    return RequestRecord(
        id="test-id",
        timestamp=datetime.now(timezone.utc).isoformat(),
        method=method,
        path=path,
        request_headers={},
        request_body=body,
        response_status=status,
        response_headers={},
        response_body="ok",
        duration_ms=duration_ms,
    )


def test_score_ok_request_is_zero():
    result = score_record(make_record())
    assert result.score == 0
    assert result.reasons == []


def test_score_server_error():
    result = score_record(make_record(status=500))
    assert result.score >= 10
    assert any("500" in r for r in result.reasons)


def test_score_client_error():
    result = score_record(make_record(status=404))
    assert 1 <= result.score < 10
    assert any("404" in r for r in result.reasons)


def test_score_slow_request():
    result = score_record(make_record(duration_ms=1500))
    assert result.score >= 3
    assert any("Slow" in r for r in result.reasons)


def test_score_very_slow_request():
    result = score_record(make_record(duration_ms=5000))
    slow_result = score_record(make_record(duration_ms=1500))
    assert result.score > slow_result.score
    assert any("Very slow" in r for r in result.reasons)


def test_score_delete_method():
    result = score_record(make_record(method="DELETE"))
    assert result.score >= 1
    assert any("DELETE" in r for r in result.reasons)


def test_score_large_body():
    big_body = "x" * 15000
    result = score_record(make_record(body=big_body))
    assert result.score >= 2
    assert any("Large" in r for r in result.reasons)


def test_score_all_sorted_descending():
    records = [
        make_record(status=200, duration_ms=50),
        make_record(status=500, duration_ms=50),
        make_record(status=404, duration_ms=50),
    ]
    results = score_all(records)
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_score_all_min_score_filter():
    records = [
        make_record(status=200),
        make_record(status=500),
    ]
    results = score_all(records, min_score=5)
    assert all(r.score >= 5 for r in results)
    assert len(results) == 1


def test_score_result_str_high():
    result = score_record(make_record(status=500))
    text = str(result)
    assert "HIGH" in text


def test_score_result_str_low():
    result = score_record(make_record())
    text = str(result)
    assert "LOW" in text
