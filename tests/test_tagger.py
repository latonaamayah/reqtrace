"""Tests for reqtrace.tagger."""

import uuid
from datetime import datetime

import pytest

from reqtrace.storage import RequestRecord
from reqtrace.tagger import TagRule, Tagger, make_default_tagger


def make_record(
    method="GET",
    path="/api/test",
    status_code=200,
    duration_ms=100.0,
    request_body="",
) -> RequestRecord:
    return RequestRecord(
        id=str(uuid.uuid4()),
        timestamp=datetime.utcnow().isoformat(),
        method=method,
        path=path,
        query_string="",
        request_headers={},
        request_body=request_body,
        response_status=status_code,
        status_code=status_code,
        response_headers={},
        response_body="",
        duration_ms=duration_ms,
    )


def test_tag_rule_matches():
    rule = TagRule(tag="slow", predicate=lambda r: r.duration_ms > 500)
    fast = make_record(duration_ms=100)
    slow = make_record(duration_ms=1500)
    assert not rule.matches(fast)
    assert rule.matches(slow)


def test_tag_rule_predicate_exception_returns_false():
    rule = TagRule(tag="broken", predicate=lambda r: 1 / 0)
    assert not rule.matches(make_record())


def test_tagger_add_and_tag_record():
    tagger = Tagger()
    tagger.add_rule("error", lambda r: r.status_code >= 500)
    ok = make_record(status_code=200)
    err = make_record(status_code=503)
    assert tagger.tag_record(ok) == []
    assert tagger.tag_record(err) == ["error"]


def test_tagger_multiple_tags():
    tagger = Tagger()
    tagger.add_rule("post", lambda r: r.method == "POST")
    tagger.add_rule("error", lambda r: r.status_code >= 500)
    record = make_record(method="POST", status_code=500)
    tags = tagger.tag_record(record)
    assert "post" in tags
    assert "error" in tags


def test_tag_all_returns_mapping():
    tagger = Tagger()
    tagger.add_rule("get", lambda r: r.method == "GET")
    records = [make_record(method="GET"), make_record(method="POST")]
    result = tagger.tag_all(records)
    assert result[records[0].id] == ["get"]
    assert result[records[1].id] == []


def test_make_default_tagger_slow():
    tagger = make_default_tagger()
    slow = make_record(duration_ms=2000)
    assert "slow" in tagger.tag_record(slow)


def test_make_default_tagger_error():
    tagger = make_default_tagger()
    assert "error" in tagger.tag_record(make_record(status_code=500))
    assert "client-error" in tagger.tag_record(make_record(status_code=404))


def test_make_default_tagger_large_body():
    tagger = make_default_tagger()
    big = make_record(request_body="x" * 5000)
    small = make_record(request_body="hello")
    assert "large-body" in tagger.tag_record(big)
    assert "large-body" not in tagger.tag_record(small)
