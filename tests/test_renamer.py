"""Tests for reqtrace.renamer."""
import pytest
from reqtrace.storage import RequestRecord
from reqtrace.renamer import (
    RenameRule,
    RenameResult,
    Renamer,
    replace_path_prefix,
)


def make_record(
    path: str = "/api/v1/users",
    method: str = "GET",
    status_code: int = 200,
    duration_ms: float = 50.0,
) -> RequestRecord:
    return RequestRecord(
        id="test-id",
        timestamp="2024-01-01T00:00:00",
        method=method,
        path=path,
        request_headers={},
        request_body="",
        status_code=status_code,
        response_headers={},
        response_body="",
        duration_ms=duration_ms,
    )


def test_replace_path_prefix_matches():
    rule = replace_path_prefix("/api/v1", "/api/v2")
    record = make_record(path="/api/v1/users")
    assert rule.matches(record)


def test_replace_path_prefix_no_match():
    rule = replace_path_prefix("/api/v1", "/api/v2")
    record = make_record(path="/health")
    assert not rule.matches(record)


def test_replace_path_prefix_rewrites_correctly():
    rule = replace_path_prefix("/api/v1", "/api/v2")
    record = make_record(path="/api/v1/users/42")
    _, changed = Renamer.__new__(Renamer), False
    renamer = Renamer()
    renamer.add_rule(rule)
    result, changed = renamer.rename_record(record)
    assert changed
    assert result.path == "/api/v2/users/42"


def test_renamer_unchanged_when_no_rule_matches():
    renamer = Renamer()
    renamer.add_rule(replace_path_prefix("/api/v1", "/api/v2"))
    record = make_record(path="/health")
    result, changed = renamer.rename_record(record)
    assert not changed
    assert result.path == "/health"


def test_renamer_first_matching_rule_wins():
    renamer = Renamer()
    renamer.add_rule(replace_path_prefix("/api", "/svc"))
    renamer.add_rule(replace_path_prefix("/api/v1", "/api/v2"))  # never reached
    record = make_record(path="/api/v1/items")
    result, changed = renamer.rename_record(record)
    assert changed
    assert result.path == "/svc/v1/items"


def test_rename_all_counts():
    renamer = Renamer()
    renamer.add_rule(replace_path_prefix("/old", "/new"))
    records = [
        make_record(path="/old/a"),
        make_record(path="/old/b"),
        make_record(path="/keep/c"),
    ]
    result = renamer.rename_all(records)
    assert result.renamed_count == 2
    assert result.unchanged_count == 1


def test_rename_all_paths_updated():
    renamer = Renamer()
    renamer.add_rule(replace_path_prefix("/v1", "/v2"))
    records = [make_record(path="/v1/orders"), make_record(path="/v1/users")]
    result = renamer.rename_all(records)
    paths = [r.path for r in result.renamed]
    assert "/v2/orders" in paths
    assert "/v2/users" in paths


def test_rename_result_str():
    r = RenameResult()
    r.renamed.append(make_record())
    r.unchanged.append(make_record())
    s = str(r)
    assert "1 renamed" in s
    assert "1 unchanged" in s


def test_rename_rule_predicate_exception_returns_false():
    def bad_pred(r):
        raise RuntimeError("boom")

    rule = RenameRule(description="bad", predicate=bad_pred, rewrite=lambda r: r)
    record = make_record()
    assert not rule.matches(record)


def test_rename_all_records_property():
    renamer = Renamer()
    renamer.add_rule(replace_path_prefix("/old", "/new"))
    records = [make_record(path="/old/x"), make_record(path="/keep/y")]
    result = renamer.rename_all(records)
    assert len(result.all_records) == 2
