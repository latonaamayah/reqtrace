"""Tests for reqtrace.differ module."""

import pytest
from datetime import datetime
from reqtrace.storage import RequestRecord
from reqtrace.differ import diff_records, diff_by_index, FieldDiff, RecordDiff


def make_record(**kwargs) -> RequestRecord:
    defaults = dict(
        id="abc123",
        timestamp=datetime(2024, 1, 1, 12, 0, 0).isoformat(),
        method="GET",
        path="/api/users",
        query_string="",
        request_headers={"Host": "localhost"},
        request_body="",
        status_code=200,
        response_headers={"Content-Type": "application/json"},
        response_body='{"ok": true}',
        duration_ms=42.0,
    )
    defaults.update(kwargs)
    return RequestRecord(**defaults)


def test_diff_identical_records():
    a = make_record(id="r1")
    b = make_record(id="r2")
    result = diff_records(a, b)
    assert not result.has_changes
    assert result.record_a_id == "r1"
    assert result.record_b_id == "r2"


def test_diff_different_method():
    a = make_record(id="r1", method="GET")
    b = make_record(id="r2", method="POST")
    result = diff_records(a, b)
    assert result.has_changes
    methods = [d for d in result.diffs if d.field == "method"]
    assert len(methods) == 1
    assert methods[0].old_value == "GET"
    assert methods[0].new_value == "POST"


def test_diff_multiple_fields():
    a = make_record(id="r1", status_code=200, response_body='{"ok": true}')
    b = make_record(id="r2", status_code=404, response_body='{"error": "not found"}')
    result = diff_records(a, b)
    fields = {d.field for d in result.diffs}
    assert "status_code" in fields
    assert "response_body" in fields


def test_diff_format_no_changes():
    a = make_record(id="r1")
    b = make_record(id="r2")
    result = diff_records(a, b)
    output = result.format()
    assert "identical" in output


def test_diff_format_with_changes():
    a = make_record(id="r1", path="/old")
    b = make_record(id="r2", path="/new")
    result = diff_records(a, b)
    output = result.format()
    assert "r1" in output
    assert "r2" in output
    assert "/old" in output
    assert "/new" in output


def test_diff_by_index_valid():
    records = [make_record(id="r1"), make_record(id="r2", path="/other")]
    result = diff_by_index(records, 0, 1)
    assert result is not None
    assert result.record_a_id == "r1"


def test_diff_by_index_out_of_bounds():
    records = [make_record(id="r1")]
    assert diff_by_index(records, 0, 5) is None
    assert diff_by_index(records, -1, 0) is None


def test_field_diff_str():
    fd = FieldDiff(field="method", old_value="GET", new_value="POST")
    s = str(fd)
    assert "method" in s
    assert "GET" in s
    assert "POST" in s
