"""Tests for reqtrace.classifier."""
import pytest
from reqtrace.classifier import Classifier, ClassificationResult
from reqtrace.storage import RequestRecord


def make_record(
    method: str = "GET",
    path: str = "/api/test",
    status_code: int = 200,
    duration_ms: float = 50.0,
) -> RequestRecord:
    return RequestRecord(
        record_id="abc123",
        timestamp="2024-01-01T00:00:00",
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


def test_classify_empty_records():
    c = Classifier()
    c.add_rule("ok", lambda r: r.status_code < 400)
    result = c.classify([])
    assert result.total == 0
    assert result.classified_count == 0
    assert result.unclassified == []


def test_classify_single_rule_match():
    c = Classifier()
    c.add_rule("success", lambda r: r.status_code == 200)
    records = [make_record(status_code=200)]
    result = c.classify(records)
    assert "success" in result.categories
    assert len(result.categories["success"]) == 1
    assert result.unclassified == []


def test_classify_unmatched_goes_to_unclassified():
    c = Classifier()
    c.add_rule("error", lambda r: r.status_code >= 500)
    records = [make_record(status_code=200)]
    result = c.classify(records)
    assert result.unclassified == records
    assert result.classified_count == 0


def test_classify_first_matching_rule_wins():
    c = Classifier()
    c.add_rule("client_error", lambda r: r.status_code == 404)
    c.add_rule("any_error", lambda r: r.status_code >= 400)
    records = [make_record(status_code=404)]
    result = c.classify(records)
    assert "client_error" in result.categories
    assert "any_error" not in result.categories


def test_classify_multiple_categories():
    c = Classifier()
    c.add_rule("success", lambda r: r.status_code < 400)
    c.add_rule("error", lambda r: r.status_code >= 400)
    records = [
        make_record(status_code=200),
        make_record(status_code=404),
        make_record(status_code=500),
        make_record(status_code=201),
    ]
    result = c.classify(records)
    assert len(result.categories["success"]) == 2
    assert len(result.categories["error"]) == 2
    assert result.unclassified == []
    assert result.total == 4


def test_classify_predicate_exception_treated_as_no_match():
    c = Classifier()
    def bad_predicate(r: RequestRecord) -> bool:
        raise ValueError("boom")
    c.add_rule("boom", bad_predicate)
    records = [make_record()]
    result = c.classify(records)
    assert result.unclassified == records


def test_str_output_contains_category_names():
    c = Classifier()
    c.add_rule("ok", lambda r: r.status_code == 200)
    records = [make_record(status_code=200), make_record(status_code=404)]
    result = c.classify(records)
    summary = str(result)
    assert "ok" in summary
    assert "unclassified" in summary
