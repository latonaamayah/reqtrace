"""Tests for reqtrace.merger and reqtrace.cli_merge."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from reqtrace.merger import MergeResult, merge
from reqtrace.storage import LogStorage, RequestRecord
from reqtrace.cli_merge import build_merge_parser, run_merge


def make_record(
    method: str = "GET",
    path: str = "/api",
    status: int = 200,
    timestamp: str = "2024-01-01T00:00:00",
) -> RequestRecord:
    return RequestRecord(
        timestamp=timestamp,
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


@pytest.fixture()
def tmp_storage(tmp_path):
    def _make(name: str) -> LogStorage:
        return LogStorage(str(tmp_path / name))
    return _make


def test_merge_empty_sources(tmp_storage):
    dest = tmp_storage("dest.jsonl")
    result = merge(sources=[], destination=dest)
    assert result.total_sources == 0
    assert result.total_merged == 0
    assert result.duplicates_skipped == 0
    assert dest.load_all() == []


def test_merge_single_source(tmp_storage):
    src = tmp_storage("src.jsonl")
    src.save(make_record(path="/a"))
    src.save(make_record(path="/b"))
    dest = tmp_storage("dest.jsonl")
    result = merge(sources=[src], destination=dest)
    assert result.total_merged == 2
    assert result.duplicates_skipped == 0
    assert len(dest.load_all()) == 2


def test_merge_multiple_sources(tmp_storage):
    s1 = tmp_storage("s1.jsonl")
    s2 = tmp_storage("s2.jsonl")
    s1.save(make_record(path="/x", timestamp="2024-01-01T01:00:00"))
    s2.save(make_record(path="/y", timestamp="2024-01-01T02:00:00"))
    dest = tmp_storage("dest.jsonl")
    result = merge(sources=[s1, s2], destination=dest)
    assert result.total_merged == 2
    assert result.records_per_source == [1, 1]


def test_merge_deduplication(tmp_storage):
    s1 = tmp_storage("s1.jsonl")
    s2 = tmp_storage("s2.jsonl")
    rec = make_record(path="/dup", timestamp="2024-01-01T00:00:00")
    s1.save(rec)
    s2.save(rec)  # identical record
    dest = tmp_storage("dest.jsonl")
    result = merge(sources=[s1, s2], destination=dest, deduplicate=True)
    assert result.total_merged == 1
    assert result.duplicates_skipped == 1


def test_merge_no_dedup_keeps_all(tmp_storage):
    s1 = tmp_storage("s1.jsonl")
    s2 = tmp_storage("s2.jsonl")
    rec = make_record(path="/dup")
    s1.save(rec)
    s2.save(rec)
    dest = tmp_storage("dest.jsonl")
    result = merge(sources=[s1, s2], destination=dest, deduplicate=False)
    assert result.total_merged == 2
    assert result.duplicates_skipped == 0


def test_merge_result_str():
    r = MergeResult(total_sources=2, records_per_source=[3, 2], total_merged=5, duplicates_skipped=0)
    text = str(r)
    assert "Sources merged" in text
    assert "5" in text


def test_cli_merge_missing_source(tmp_path):
    parser = build_merge_parser()
    args = parser.parse_args([
        str(tmp_path / "nonexistent.jsonl"),
        "-o", str(tmp_path / "out.jsonl"),
    ])
    code = run_merge(args)
    assert code == 1


def test_cli_merge_success(tmp_path):
    src = LogStorage(str(tmp_path / "src.jsonl"))
    src.save(make_record())
    parser = build_merge_parser()
    args = parser.parse_args([
        str(tmp_path / "src.jsonl"),
        "-o", str(tmp_path / "out.jsonl"),
    ])
    code = run_merge(args)
    assert code == 0
    dest = LogStorage(str(tmp_path / "out.jsonl"))
    assert len(dest.load_all()) == 1
