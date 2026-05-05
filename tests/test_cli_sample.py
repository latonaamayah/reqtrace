"""Tests for reqtrace.cli_sample."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from reqtrace.cli_sample import build_sample_parser, run_sample
from reqtrace.storage import LogStorage, RequestRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_record(method: str = "GET", status: int = 200) -> RequestRecord:
    return RequestRecord(
        request_id=str(uuid.uuid4()),
        method=method,
        path="/api/test",
        query_string="",
        request_headers={},
        request_body="",
        response_status=status,
        response_headers={},
        response_body="",
        duration_ms=5.0,
        timestamp="2024-06-01T12:00:00",
    )


def write_records(path: Path, records):
    storage = LogStorage(str(path))
    for r in records:
        storage.save(r)


def make_args(input_path, output_path, rate=1.0, seed=None, method=None, status=None):
    parser = build_sample_parser()
    argv = [str(input_path), str(output_path), "--rate", str(rate)]
    if seed is not None:
        argv += ["--seed", str(seed)]
    if method is not None:
        argv += ["--method", method]
    if status is not None:
        argv += ["--status", str(status)]
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_sample_rate_one_keeps_all(tmp_path):
    src = tmp_path / "src.jsonl"
    dst = tmp_path / "dst.jsonl"
    records = [make_record() for _ in range(10)]
    write_records(src, records)

    args = make_args(src, dst, rate=1.0)
    rc = run_sample(args)

    assert rc == 0
    kept = LogStorage(str(dst)).load_all()
    assert len(kept) == 10


def test_sample_rate_zero_keeps_none(tmp_path):
    src = tmp_path / "src.jsonl"
    dst = tmp_path / "dst.jsonl"
    write_records(src, [make_record() for _ in range(10)])

    args = make_args(src, dst, rate=0.0)
    rc = run_sample(args)

    assert rc == 0
    assert LogStorage(str(dst)).load_all() == []


def test_sample_invalid_rate_returns_2(tmp_path):
    src = tmp_path / "src.jsonl"
    dst = tmp_path / "dst.jsonl"
    write_records(src, [make_record()])

    args = make_args(src, dst, rate=2.5)
    rc = run_sample(args)

    assert rc == 2


def test_sample_with_method_filter(tmp_path):
    src = tmp_path / "src.jsonl"
    dst = tmp_path / "dst.jsonl"
    records = [make_record(method="GET")] * 5 + [make_record(method="POST")] * 5
    write_records(src, records)

    args = make_args(src, dst, rate=1.0, method="POST")
    run_sample(args)

    kept = LogStorage(str(dst)).load_all()
    assert len(kept) == 5
    assert all(r.method == "POST" for r in kept)


def test_sample_deterministic_with_seed(tmp_path):
    src = tmp_path / "src.jsonl"
    dst1 = tmp_path / "dst1.jsonl"
    dst2 = tmp_path / "dst2.jsonl"
    write_records(src, [make_record() for _ in range(20)])

    run_sample(make_args(src, dst1, rate=0.5, seed=99))
    run_sample(make_args(src, dst2, rate=0.5, seed=99))

    ids1 = {r.request_id for r in LogStorage(str(dst1)).load_all()}
    ids2 = {r.request_id for r in LogStorage(str(dst2)).load_all()}
    assert ids1 == ids2
