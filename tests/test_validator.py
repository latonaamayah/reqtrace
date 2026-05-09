"""Tests for reqtrace.validator."""
from __future__ import annotations

import uuid
from datetime import datetime

import pytest

from reqtrace.storage import RequestRecord
from reqtrace.validator import (
    ValidationRule,
    Validator,
    require_duration_below,
    require_non_empty_path,
    require_status_below_500,
)


def make_record(
    method: str = "GET",
    path: str = "/api/test",
    status_code: int = 200,
    duration_ms: float = 50.0,
) -> RequestRecord:
    return RequestRecord(
        record_id=str(uuid.uuid4()),
        timestamp=datetime.utcnow().isoformat(),
        method=method,
        path=path,
        query_string="",
        request_headers={},
        request_body="",
        status_code=status_code,
        response_headers={},
        response_body="",
        duration_ms=duration_ms,
    )


def test_no_errors_on_clean_records():
    v = Validator()
    v.add_rule(require_status_below_500())
    v.add_rule(require_non_empty_path())
    records = [make_record(), make_record(status_code=201)]
    result = v.validate(records)
    assert result.error_count == 0
    assert "passed" in str(result)


def test_server_error_rule_catches_500():
    v = Validator()
    v.add_rule(require_status_below_500())
    records = [make_record(status_code=500)]
    result = v.validate(records)
    assert result.error_count == 1
    assert result.errors[0].rule_name == "no_server_error"


def test_empty_path_rule():
    v = Validator()
    v.add_rule(require_non_empty_path())
    records = [make_record(path="   ")]
    result = v.validate(records)
    assert result.error_count == 1
    assert result.errors[0].rule_name == "non_empty_path"


def test_duration_rule_passes_fast_request():
    v = Validator()
    v.add_rule(require_duration_below(200.0))
    result = v.validate([make_record(duration_ms=100.0)])
    assert result.error_count == 0


def test_duration_rule_catches_slow_request():
    v = Validator()
    v.add_rule(require_duration_below(100.0))
    result = v.validate([make_record(duration_ms=500.0)])
    assert result.error_count == 1
    assert "duration_below_100ms" in result.errors[0].rule_name


def test_multiple_rules_multiple_errors():
    v = Validator()
    v.add_rule(require_status_below_500())
    v.add_rule(require_duration_below(10.0))
    records = [make_record(status_code=503, duration_ms=999.0)]
    result = v.validate(records)
    assert result.error_count == 2


def test_predicate_exception_treated_as_failure():
    rule = ValidationRule(
        name="bad_rule",
        predicate=lambda r: 1 / 0,  # always raises
        message="Should never pass.",
    )
    v = Validator()
    v.add_rule(rule)
    result = v.validate([make_record()])
    assert result.error_count == 1


def test_validation_error_str():
    v = Validator()
    v.add_rule(require_status_below_500())
    records = [make_record(status_code=500)]
    result = v.validate(records)
    summary = str(result)
    assert "validation error" in summary.lower()
    assert "no_server_error" in summary


def test_validate_empty_list():
    v = Validator()
    v.add_rule(require_status_below_500())
    result = v.validate([])
    assert result.error_count == 0
    assert result._total == 0
