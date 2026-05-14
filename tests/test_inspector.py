"""Tests for reqtrace.inspector."""
import uuid
from datetime import datetime, timezone

import pytest

from reqtrace.storage import RequestRecord
from reqtrace.inspector import (
    InspectionWarning,
    InspectionResult,
    inspect_record,
    inspect_all,
)


def make_record(
    method="GET",
    path="/api/test",
    status=200,
    duration_ms=100.0,
    request_body=None,
    request_headers=None,
    response_body=None,
    response_headers=None,
) -> RequestRecord:
    return RequestRecord(
        record_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        method=method,
        path=path,
        request_headers=request_headers or {},
        request_body=request_body,
        response_status=status,
        response_headers=response_headers or {},
        response_body=response_body,
        duration_ms=duration_ms,
    )


def test_clean_record_has_no_warnings():
    r = make_record()
    result = inspect_record(r)
    assert not result.has_warnings
    assert "No issues found" in result.format()


def test_slow_request_triggers_warning():
    r = make_record(duration_ms=2500.0)
    result = inspect_record(r, slow_threshold_ms=1000.0)
    fields = [w.field for w in result.warnings]
    assert "duration_ms" in fields


def test_server_error_triggers_warning():
    r = make_record(status=503)
    result = inspect_record(r)
    fields = [w.field for w in result.warnings]
    assert "response_status" in fields


def test_client_error_does_not_trigger_server_error_warning():
    r = make_record(status=404)
    result = inspect_record(r)
    fields = [w.field for w in result.warnings]
    assert "response_status" not in fields


def test_missing_content_type_on_request_body():
    r = make_record(request_body='{"key": "value"}', request_headers={})
    result = inspect_record(r)
    fields = [w.field for w in result.warnings]
    assert "request_headers" in fields


def test_no_content_type_warning_when_body_absent():
    r = make_record(request_body=None, request_headers={})
    result = inspect_record(r)
    fields = [w.field for w in result.warnings]
    assert "request_headers" not in fields


def test_invalid_json_body_warns_when_content_type_json():
    r = make_record(
        request_body="not-json",
        request_headers={"Content-Type": "application/json"},
    )
    result = inspect_record(r)
    fields = [w.field for w in result.warnings]
    assert "request_body" in fields


def test_valid_json_body_no_warning():
    r = make_record(
        request_body='{"ok": true}',
        request_headers={"Content-Type": "application/json"},
    )
    result = inspect_record(r)
    fields = [w.field for w in result.warnings]
    assert "request_body" not in fields


def test_empty_path_warns():
    r = make_record(path="")
    result = inspect_record(r)
    fields = [w.field for w in result.warnings]
    assert "path" in fields


def test_inspect_all_returns_one_result_per_record():
    records = [make_record() for _ in range(5)]
    results = inspect_all(records)
    assert len(results) == 5


def test_format_includes_warnings():
    r = make_record(status=500, duration_ms=3000.0)
    result = inspect_record(r)
    formatted = result.format()
    assert "WARN" in formatted
    assert result.record_id in formatted
