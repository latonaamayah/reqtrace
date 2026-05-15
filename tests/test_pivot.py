"""Tests for reqtrace.pivot and reqtrace.cli_pivot."""
from __future__ import annotations

import io
import json
import os
import tempfile
from datetime import datetime, timezone

import pytest

from reqtrace.pivot import PivotTable, pivot, _method_key, _status_class_key
from reqtrace.storage import RequestRecord


def make_record(
    method: str = "GET",
    path: str = "/api/test",
    status: int = 200,
    duration: float = 0.05,
) -> RequestRecord:
    return RequestRecord(
        record_id="test-id",
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc).isoformat(),
        method=method,
        path=path,
        request_headers={},
        request_body="",
        response_status=status,
        response_headers={},
        response_body="",
        duration_ms=duration * 1000,
    )


def test_pivot_empty_records():
    table = pivot([], row_by="method", col_by="status_class")
    assert table.rows == []
    assert table.cols == []
    assert table.cells == {}


def test_pivot_single_record():
    records = [make_record(method="GET", status=200)]
    table = pivot(records, row_by="method", col_by="status_class")
    assert "GET" in table.rows
    assert "2xx" in table.cols
    assert table.get("GET", "2xx") == 1


def test_pivot_multiple_methods():
    records = [
        make_record(method="GET", status=200),
        make_record(method="POST", status=201),
        make_record(method="GET", status=404),
    ]
    table = pivot(records, row_by="method", col_by="status_class")
    assert table.get("GET", "2xx") == 1
    assert table.get("GET", "4xx") == 1
    assert table.get("POST", "2xx") == 1
    assert table.get("POST", "4xx") == 0


def test_pivot_exact_status_column():
    records = [
        make_record(status=200),
        make_record(status=200),
        make_record(status=500),
    ]
    table = pivot(records, row_by="method", col_by="status")
    assert table.get("GET", "200") == 2
    assert table.get("GET", "500") == 1


def test_pivot_custom_key_function():
    records = [
        make_record(path="/api/users", status=200),
        make_record(path="/api/orders", status=500),
    ]
    path_fn = lambda r: r.path.split("/")[2] if len(r.path.split("/")) > 2 else "root"
    table = pivot(records, row_by=path_fn, col_by="status_class")
    assert "users" in table.rows
    assert "orders" in table.rows
    assert table.row_label == "custom_row"


def test_pivot_table_get_missing_returns_zero():
    table = PivotTable(row_label="method", col_label="status_class")
    assert table.get("DELETE", "5xx") == 0


def test_pivot_rows_and_cols_sorted():
    records = [
        make_record(method="POST", status=500),
        make_record(method="DELETE", status=200),
        make_record(method="GET", status=404),
    ]
    table = pivot(records)
    assert table.rows == sorted(table.rows)
    assert table.cols == sorted(table.cols)


def test_cli_pivot_no_records(tmp_path):
    from reqtrace.cli_pivot import run_pivot, build_pivot_parser

    log = tmp_path / "empty.jsonl"
    log.write_text("")
    parser = build_pivot_parser()
    args = parser.parse_args([str(log)])
    out = io.StringIO()
    rc = run_pivot(args, out=out)
    assert rc == 0
    assert "No records" in out.getvalue()


def test_cli_pivot_produces_table(tmp_path):
    from reqtrace.cli_pivot import run_pivot, build_pivot_parser
    from reqtrace.storage import LogStorage

    log = tmp_path / "log.jsonl"
    storage = LogStorage(str(log))
    storage.save(make_record(method="GET", status=200))
    storage.save(make_record(method="POST", status=500))

    parser = build_pivot_parser()
    args = parser.parse_args([str(log), "--rows", "method", "--cols", "status_class"])
    out = io.StringIO()
    rc = run_pivot(args, out=out)
    assert rc == 0
    output = out.getvalue()
    assert "GET" in output
    assert "POST" in output
    assert "2xx" in output
    assert "5xx" in output
