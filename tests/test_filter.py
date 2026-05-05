"""Tests for reqtrace.filter module."""

import pytest
from datetime import datetime
from reqtrace.storage import RequestRecord
from reqtrace.filter import RecordFilter


def make_record(
    method="GET",
    path="/api/test",
    status_code=200,
    duration_ms=50.0,
    host="localhost",
):
    return RequestRecord(
        id="test-id",
        timestamp=datetime.utcnow().isoformat(),
        method=method,
        path=path,
        query_string="",
        request_headers={"Host": host},
        request_body="",
        status_code=status_code,
        response_headers={},
        response_body="",
        duration_ms=duration_ms,
    )


def test_filter_by_method():
    records = [make_record(method="GET"), make_record(method="POST")]
    f = RecordFilter(method="GET")
    result = f.apply(records)
    assert len(result) == 1
    assert result[0].method == "GET"


def test_filter_by_path_prefix():
    records = [make_record(path="/api/users"), make_record(path="/health")]
    f = RecordFilter(path_prefix="/api")
    result = f.apply(records)
    assert len(result) == 1
    assert result[0].path == "/api/users"


def test_filter_by_status_code():
    records = [make_record(status_code=200), make_record(status_code=404)]
    f = RecordFilter(status_code=404)
    result = f.apply(records)
    assert len(result) == 1
    assert result[0].status_code == 404


def test_filter_by_duration_range():
    records = [
        make_record(duration_ms=10.0),
        make_record(duration_ms=100.0),
        make_record(duration_ms=500.0),
    ]
    f = RecordFilter(min_duration_ms=50.0, max_duration_ms=200.0)
    result = f.apply(records)
    assert len(result) == 1
    assert result[0].duration_ms == 100.0


def test_filter_by_host():
    records = [make_record(host="service-a"), make_record(host="service-b")]
    f = RecordFilter(host="service-a")
    result = f.apply(records)
    assert len(result) == 1


def test_no_filter_returns_all():
    records = [make_record(), make_record(), make_record()]
    f = RecordFilter()
    assert len(f.apply(records)) == 3


def test_combined_filters():
    records = [
        make_record(method="POST", path="/api/orders", status_code=201),
        make_record(method="GET", path="/api/orders", status_code=200),
        make_record(method="POST", path="/api/users", status_code=201),
    ]
    f = RecordFilter(method="POST", path_prefix="/api/orders")
    result = f.apply(records)
    assert len(result) == 1
    assert result[0].path == "/api/orders"
