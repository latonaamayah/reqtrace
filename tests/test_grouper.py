"""Tests for reqtrace.grouper."""

from datetime import datetime

import pytest

from reqtrace.storage import RequestRecord
from reqtrace.grouper import (
    group_by_method,
    group_by_status,
    group_by_path_prefix,
    format_groups,
)


def make_record(
    method="GET",
    path="/api/users",
    status_code=200,
    duration_ms=50.0,
) -> RequestRecord:
    return RequestRecord(
        record_id="test-id",
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        method=method,
        path=path,
        query_string="",
        request_headers={},
        request_body=None,
        status_code=status_code,
        response_headers={},
        response_body=None,
        duration_ms=duration_ms,
    )


def test_group_by_method_single():
    records = [make_record(method="GET"), make_record(method="GET")]
    groups = group_by_method(records)
    assert set(groups.keys()) == {"GET"}
    assert len(groups["GET"]) == 2


def test_group_by_method_multiple():
    records = [
        make_record(method="GET"),
        make_record(method="POST"),
        make_record(method="DELETE"),
    ]
    groups = group_by_method(records)
    assert set(groups.keys()) == {"GET", "POST", "DELETE"}


def test_group_by_status():
    records = [
        make_record(status_code=200),
        make_record(status_code=404),
        make_record(status_code=200),
    ]
    groups = group_by_status(records)
    assert len(groups["200"]) == 2
    assert len(groups["404"]) == 1


def test_group_by_path_prefix_depth1():
    records = [
        make_record(path="/api/users"),
        make_record(path="/api/orders"),
        make_record(path="/health"),
    ]
    groups = group_by_path_prefix(records, depth=1)
    assert "/api" in groups
    assert "/health" in groups
    assert len(groups["/api"]) == 2


def test_group_by_path_prefix_depth2():
    records = [
        make_record(path="/api/users/1"),
        make_record(path="/api/users/2"),
        make_record(path="/api/orders/99"),
    ]
    groups = group_by_path_prefix(records, depth=2)
    assert "/api/users" in groups
    assert "/api/orders" in groups
    assert len(groups["/api/users"]) == 2


def test_group_by_empty():
    assert group_by_method([]) == {}
    assert group_by_status([]) == {}
    assert group_by_path_prefix([]) == {}


def test_format_groups_empty():
    result = format_groups({})
    assert result == "No records."


def test_format_groups_output():
    records = [make_record(duration_ms=100.0), make_record(duration_ms=200.0)]
    groups = group_by_method(records)
    output = format_groups(groups)
    assert "GET" in output
    assert "2 request(s)" in output
    assert "150.0 ms" in output
