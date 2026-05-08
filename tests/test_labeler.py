"""Tests for reqtrace.labeler."""
import pytest

from reqtrace.storage import RequestRecord
from reqtrace.labeler import LabelRule, Labeler, LabelResult, default_labeler


def make_record(
    method="GET",
    path="/api/test",
    status_code=200,
    duration_ms=100.0,
    response_body="",
) -> RequestRecord:
    return RequestRecord(
        id="rec-1",
        timestamp="2024-01-01T00:00:00",
        method=method,
        path=path,
        query_string="",
        request_headers={},
        request_body="",
        status_code=status_code,
        response_headers={},
        response_body=response_body,
        duration_ms=duration_ms,
    )


def test_label_rule_matches_true():
    rule = LabelRule("fast", lambda r: r.duration_ms < 50)
    rec = make_record(duration_ms=10)
    assert rule.matches(rec) is True


def test_label_rule_matches_false():
    rule = LabelRule("fast", lambda r: r.duration_ms < 50)
    rec = make_record(duration_ms=200)
    assert rule.matches(rec) is False


def test_label_rule_predicate_exception_returns_false():
    rule = LabelRule("boom", lambda r: 1 / 0)
    rec = make_record()
    assert rule.matches(rec) is False


def test_labeler_single_rule():
    labeler = Labeler()
    labeler.add_rule(LabelRule("error", lambda r: r.status_code >= 500))
    rec = make_record(status_code=503)
    assert labeler.label_record(rec) == ["error"]


def test_labeler_no_matching_rules():
    labeler = Labeler()
    labeler.add_rule(LabelRule("error", lambda r: r.status_code >= 500))
    rec = make_record(status_code=200)
    assert labeler.label_record(rec) == []


def test_labeler_multiple_labels_on_one_record():
    labeler = Labeler()
    labeler.add_rule(LabelRule("slow", lambda r: r.duration_ms > 500))
    labeler.add_rule(LabelRule("error", lambda r: r.status_code >= 500))
    rec = make_record(status_code=500, duration_ms=2000)
    labels = labeler.label_record(rec)
    assert "slow" in labels
    assert "error" in labels


def test_label_all_counts():
    labeler = Labeler()
    labeler.add_rule(LabelRule("error", lambda r: r.status_code >= 500))
    records = [
        make_record(status_code=200),
        make_record(status_code=500),
        make_record(status_code=503),
    ]
    # Give unique ids
    records[1].id = "rec-2"
    records[2].id = "rec-3"
    result = labeler.label_all(records)
    assert result.label_counts.get("error") == 2
    assert result.total_labeled() == 2


def test_label_result_str():
    result = LabelResult(
        labeled={"a": ["slow"], "b": []},
        label_counts={"slow": 1},
    )
    text = str(result)
    assert "slow" in text
    assert "1" in text


def test_default_labeler_slow():
    labeler = default_labeler()
    rec = make_record(duration_ms=1500)
    assert "slow" in labeler.label_record(rec)


def test_default_labeler_mutation():
    labeler = default_labeler()
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        rec = make_record(method=method)
        assert "mutation" in labeler.label_record(rec)


def test_default_labeler_large_response():
    labeler = default_labeler()
    rec = make_record(response_body="x" * 11_000)
    assert "large-response" in labeler.label_record(rec)
