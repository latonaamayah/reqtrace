"""Tests for reqtrace.sorter."""
import pytest

from reqtrace.storage import RequestRecord
from reqtrace.sorter import SortConfig, sort_records


def make_record(
    method="GET",
    path="/api",
    status=200,
    duration=100.0,
    timestamp="2024-01-01T00:00:00",
) -> RequestRecord:
    return RequestRecord(
        id="test-id",
        timestamp=timestamp,
        method=method,
        path=path,
        request_headers={},
        request_body="",
        response_status=status,
        response_headers={},
        response_body="",
        duration_ms=duration,
    )


def test_sort_by_timestamp_asc():
    r1 = make_record(timestamp="2024-01-01T10:00:00")
    r2 = make_record(timestamp="2024-01-01T08:00:00")
    r3 = make_record(timestamp="2024-01-01T09:00:00")
    result = sort_records([r1, r2, r3], SortConfig(field="timestamp", order="asc"))
    assert [r.timestamp for r in result] == [
        "2024-01-01T08:00:00",
        "2024-01-01T09:00:00",
        "2024-01-01T10:00:00",
    ]


def test_sort_by_duration_desc():
    r1 = make_record(duration=50.0)
    r2 = make_record(duration=200.0)
    r3 = make_record(duration=120.0)
    result = sort_records([r1, r2, r3], SortConfig(field="duration_ms", order="desc"))
    assert [r.duration_ms for r in result] == [200.0, 120.0, 50.0]


def test_sort_by_status_code_asc():
    r1 = make_record(status=500)
    r2 = make_record(status=200)
    r3 = make_record(status=404)
    result = sort_records([r1, r2, r3], SortConfig(field="status_code", order="asc"))
    assert [r.response_status for r in result] == [200, 404, 500]


def test_sort_by_method_asc():
    r1 = make_record(method="POST")
    r2 = make_record(method="DELETE")
    r3 = make_record(method="GET")
    result = sort_records([r1, r2, r3], SortConfig(field="method", order="asc"))
    assert [r.method for r in result] == ["DELETE", "GET", "POST"]


def test_sort_by_path_asc():
    r1 = make_record(path="/users")
    r2 = make_record(path="/api")
    r3 = make_record(path="/health")
    result = sort_records([r1, r2, r3], SortConfig(field="path", order="asc"))
    assert [r.path for r in result] == ["/api", "/health", "/users"]


def test_sort_default_config_uses_timestamp_asc():
    r1 = make_record(timestamp="2024-06-01T00:00:00")
    r2 = make_record(timestamp="2024-01-01T00:00:00")
    result = sort_records([r1, r2])
    assert result[0].timestamp == "2024-01-01T00:00:00"


def test_sort_does_not_mutate_original():
    records = [make_record(duration=d) for d in [300.0, 100.0, 200.0]]
    original_order = [r.duration_ms for r in records]
    sort_records(records, SortConfig(field="duration_ms", order="asc"))
    assert [r.duration_ms for r in records] == original_order


def test_invalid_field_raises():
    with pytest.raises(ValueError, match="Invalid sort field"):
        SortConfig(field="unknown")  # type: ignore[arg-type]


def test_invalid_order_raises():
    with pytest.raises(ValueError, match="Invalid sort order"):
        SortConfig(order="random")  # type: ignore[arg-type]
