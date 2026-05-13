"""Tests for reqtrace.redactor."""
import pytest

from reqtrace.storage import RequestRecord
from reqtrace.redactor import RedactRule, Redactor, RedactResult, _MASK


def make_record(
    method="GET",
    path="/api/data",
    status_code=200,
    request_headers=None,
    response_headers=None,
    request_body=None,
    response_body=None,
) -> RequestRecord:
    return RequestRecord(
        id="rec-1",
        timestamp="2024-01-01T00:00:00",
        method=method,
        path=path,
        query_string="",
        request_headers=request_headers or {},
        request_body=request_body,
        status_code=status_code,
        response_headers=response_headers or {},
        response_body=response_body,
        duration_ms=10.0,
    )


def test_redact_request_header_value():
    record = make_record(request_headers={"Authorization": "Bearer secret-token"})
    redactor = Redactor()
    redactor.add_rule(RedactRule(field="request_headers", pattern=r"Bearer \S+"))
    new_record, changed = redactor.redact_record(record)
    assert changed
    assert new_record.request_headers["Authorization"] == _MASK


def test_redact_response_header_value():
    record = make_record(response_headers={"Set-Cookie": "session=abc123; Path=/"})
    redactor = Redactor()
    redactor.add_rule(RedactRule(field="response_headers", pattern=r"session=\S+"))
    new_record, changed = redactor.redact_record(record)
    assert changed
    assert _MASK in new_record.response_headers["Set-Cookie"]


def test_redact_request_body_password():
    record = make_record(request_body='{"username": "alice", "password": "s3cr3t"}')
    redactor = Redactor()
    redactor.add_rule(RedactRule(field="request_body", pattern=r'"password":\s*"[^"]+"',
                                  replacement='"password": "[REDACTED]"'))
    new_record, changed = redactor.redact_record(record)
    assert changed
    assert "s3cr3t" not in new_record.request_body
    assert "[REDACTED]" in new_record.request_body


def test_redact_response_body_token():
    record = make_record(response_body='{"token": "abc.def.ghi"}')
    redactor = Redactor()
    redactor.add_rule(RedactRule(field="response_body", pattern=r'"token":\s*"[^"]+"',
                                  replacement='"token": "[REDACTED]"'))
    new_record, changed = redactor.redact_record(record)
    assert changed
    assert "abc.def.ghi" not in new_record.response_body


def test_no_match_returns_unchanged():
    record = make_record(request_headers={"Content-Type": "application/json"})
    redactor = Redactor()
    redactor.add_rule(RedactRule(field="request_headers", pattern=r"Bearer \S+"))
    new_record, changed = redactor.redact_record(record)
    assert not changed
    assert new_record.request_headers["Content-Type"] == "application/json"


def test_predicate_skips_non_matching_records():
    record = make_record(method="GET", request_headers={"Authorization": "Bearer token"})
    redactor = Redactor()
    redactor.add_rule(RedactRule(
        field="request_headers",
        pattern=r"Bearer \S+",
        predicate=lambda r: r.method == "POST",  # only apply to POST
    ))
    new_record, changed = redactor.redact_record(record)
    assert not changed
    assert new_record.request_headers["Authorization"] == "Bearer token"


def test_redact_all_counts_correctly():
    records = [
        make_record(request_headers={"Authorization": "Bearer tok1"}),
        make_record(request_headers={"Content-Type": "application/json"}),
        make_record(request_headers={"Authorization": "Bearer tok2"}),
    ]
    redactor = Redactor()
    redactor.add_rule(RedactRule(field="request_headers", pattern=r"Bearer \S+"))
    result = redactor.redact_all(records)
    assert result.total == 3
    assert result.redacted_count == 2
    assert len(result.records) == 3


def test_redact_result_str():
    result = RedactResult(total=5, redacted_count=2)
    assert "total=5" in str(result)
    assert "redacted=2" in str(result)


def test_predicate_exception_treated_as_no_match():
    record = make_record(request_headers={"Authorization": "Bearer secret"})
    redactor = Redactor()
    redactor.add_rule(RedactRule(
        field="request_headers",
        pattern=r"Bearer \S+",
        predicate=lambda r: 1 / 0,  # raises ZeroDivisionError
    ))
    new_record, changed = redactor.redact_record(record)
    assert not changed
