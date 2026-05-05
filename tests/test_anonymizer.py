"""Tests for reqtrace.anonymizer."""

import pytest
from datetime import datetime
from reqtrace.storage import RequestRecord
from reqtrace.anonymizer import Anonymizer, REDACTED


def make_record(
    request_headers=None,
    response_headers=None,
    request_body=None,
):
    return RequestRecord(
        id="abc-123",
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        method="POST",
        path="/api/login",
        query_string="",
        request_headers=request_headers or {},
        request_body=request_body,
        response_status=200,
        response_headers=response_headers or {},
        response_body='{"ok": true}',
        duration_ms=42.0,
    )


def test_anonymize_sensitive_header():
    anon = Anonymizer()
    record = make_record(request_headers={"Authorization": "Bearer secret-token", "Content-Type": "application/json"})
    result = anon.anonymize(record)
    assert result.request_headers["Authorization"] == REDACTED
    assert result.request_headers["Content-Type"] == "application/json"


def test_anonymize_cookie_header():
    anon = Anonymizer()
    record = make_record(response_headers={"Set-Cookie": "session=xyz; Path=/", "X-Request-Id": "123"})
    result = anon.anonymize(record)
    assert result.response_headers["Set-Cookie"] == REDACTED
    assert result.response_headers["X-Request-Id"] == "123"


def test_anonymize_body_password():
    anon = Anonymizer()
    body = '{"username": "alice", "password": "supersecret"}'
    record = make_record(request_body=body)
    result = anon.anonymize(record)
    assert "supersecret" not in result.request_body
    assert REDACTED in result.request_body
    assert "alice" in result.request_body


def test_anonymize_body_token():
    anon = Anonymizer()
    body = '{"token": "abc.def.ghi", "user": "bob"}'
    record = make_record(request_body=body)
    result = anon.anonymize(record)
    assert "abc.def.ghi" not in result.request_body
    assert REDACTED in result.request_body


def test_anonymize_none_body():
    anon = Anonymizer()
    record = make_record(request_body=None)
    result = anon.anonymize(record)
    assert result.request_body is None


def test_anonymize_does_not_mutate_original():
    anon = Anonymizer()
    headers = {"Authorization": "Bearer token"}
    record = make_record(request_headers=headers)
    anon.anonymize(record)
    assert record.request_headers["Authorization"] == "Bearer token"


def test_custom_sensitive_headers():
    anon = Anonymizer(sensitive_headers=["X-Custom-Secret"])
    record = make_record(request_headers={"X-Custom-Secret": "my-secret", "Authorization": "Bearer keep"})
    result = anon.anonymize(record)
    assert result.request_headers["X-Custom-Secret"] == REDACTED
    # Authorization is NOT in the custom list, so it should be preserved
    assert result.request_headers["Authorization"] == "Bearer keep"


def test_non_sensitive_headers_preserved():
    anon = Anonymizer()
    record = make_record(request_headers={"Content-Type": "application/json", "Accept": "*/*"})
    result = anon.anonymize(record)
    assert result.request_headers["Content-Type"] == "application/json"
    assert result.request_headers["Accept"] == "*/*"
