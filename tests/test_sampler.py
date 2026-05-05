"""Tests for reqtrace.sampler."""

from __future__ import annotations

import uuid
from typing import List

import pytest

from reqtrace.sampler import Sampler, SamplerConfig
from reqtrace.storage import RequestRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_record(request_id: str = None, method: str = "GET", path: str = "/") -> RequestRecord:
    return RequestRecord(
        request_id=request_id or str(uuid.uuid4()),
        method=method,
        path=path,
        query_string="",
        request_headers={},
        request_body="",
        response_status=200,
        response_headers={},
        response_body="",
        duration_ms=10.0,
        timestamp="2024-01-01T00:00:00",
    )


def _records(n: int) -> List[RequestRecord]:
    return [make_record() for _ in range(n)]


# ---------------------------------------------------------------------------
# SamplerConfig validation
# ---------------------------------------------------------------------------

def test_config_invalid_rate_raises():
    with pytest.raises(ValueError):
        SamplerConfig(rate=1.5)


def test_config_negative_rate_raises():
    with pytest.raises(ValueError):
        SamplerConfig(rate=-0.1)


# ---------------------------------------------------------------------------
# Rate = 1.0 keeps everything
# ---------------------------------------------------------------------------

def test_keep_all_at_rate_one():
    sampler = Sampler(SamplerConfig(rate=1.0))
    records = _records(20)
    assert sampler.apply(records) == records


# ---------------------------------------------------------------------------
# Rate = 0.0 drops everything
# ---------------------------------------------------------------------------

def test_keep_none_at_rate_zero():
    sampler = Sampler(SamplerConfig(rate=0.0))
    records = _records(20)
    assert sampler.apply(records) == []


# ---------------------------------------------------------------------------
# Deterministic sampling with seed
# ---------------------------------------------------------------------------

def test_deterministic_sampling():
    """Same records + same seed must produce identical results across calls."""
    records = _records(50)
    sampler1 = Sampler(SamplerConfig(rate=0.5, seed=42))
    sampler2 = Sampler(SamplerConfig(rate=0.5, seed=42))
    assert sampler1.apply(records) == sampler2.apply(records)


# ---------------------------------------------------------------------------
# Predicate filtering
# ---------------------------------------------------------------------------

def test_predicate_filters_records():
    sampler = Sampler(SamplerConfig(predicate=lambda r: r.method == "POST"))
    records = [
        make_record(method="GET"),
        make_record(method="POST"),
        make_record(method="GET"),
        make_record(method="POST"),
    ]
    result = sampler.apply(records)
    assert all(r.method == "POST" for r in result)
    assert len(result) == 2


def test_predicate_exception_drops_record():
    def bad_predicate(r):
        raise RuntimeError("boom")

    sampler = Sampler(SamplerConfig(predicate=bad_predicate))
    assert sampler.apply([make_record()]) == []


# ---------------------------------------------------------------------------
# should_keep is consistent with apply
# ---------------------------------------------------------------------------

def test_should_keep_consistent_with_apply():
    sampler = Sampler(SamplerConfig(rate=0.7, seed=7))
    records = _records(30)
    kept_apply = sampler.apply(records)
    kept_manual = [r for r in records if sampler.should_keep(r)]
    assert kept_apply == kept_manual
