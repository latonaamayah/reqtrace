"""Tests for reqtrace.patcher."""
import pytest
from reqtrace.storage import RequestRecord
from reqtrace.patcher import PatchRule, PatchResult, Patcher, patch_storage


def make_record(
    method="GET",
    path="/api/test",
    status=200,
    duration_ms=120.0,
    request_body="",
    response_body="ok",
):
    return RequestRecord(
        id="rec-1",
        timestamp="2024-01-01T00:00:00",
        method=method,
        path=path,
        query_string="",
        request_headers={},
        request_body=request_body,
        status_code=status,
        response_headers={},
        response_body=response_body,
        duration_ms=duration_ms,
    )


def test_patch_rule_matches_no_predicate():
    rule = PatchRule(field_name="method", transform=str.lower)
    record = make_record(method="GET")
    assert rule.matches(record) is True


def test_patch_rule_matches_with_predicate():
    rule = PatchRule(
        field_name="path",
        transform=lambda p: p.replace("/api", "/v2"),
        predicate=lambda r: r.path.startswith("/api"),
    )
    assert rule.matches(make_record(path="/api/users")) is True
    assert rule.matches(make_record(path="/health")) is False


def test_patch_rule_predicate_exception_returns_false():
    rule = PatchRule(
        field_name="path",
        transform=lambda p: p,
        predicate=lambda r: 1 / 0,
    )
    assert rule.matches(make_record()) is False


def test_patcher_transforms_field():
    patcher = Patcher()
    patcher.add_rule(PatchRule(field_name="method", transform=str.lower))
    record = make_record(method="GET")
    new_record, result = patcher.apply([record])
    assert new_record[0].method == "get"
    assert result.patched_count == 1
    assert result.skipped_count == 0


def test_patcher_skips_unmatched():
    patcher = Patcher()
    patcher.add_rule(PatchRule(
        field_name="path",
        transform=lambda p: "/patched",
        predicate=lambda r: r.path.startswith("/never"),
    ))
    record = make_record(path="/api/test")
    new_records, result = patcher.apply([record])
    assert new_records[0].path == "/api/test"
    assert result.skipped_count == 1
    assert result.patched_count == 0


def test_patcher_multiple_rules():
    patcher = Patcher()
    patcher.add_rule(PatchRule(field_name="method", transform=str.lower))
    patcher.add_rule(PatchRule(field_name="path", transform=lambda p: p + "/patched"))
    record = make_record(method="POST", path="/api")
    new_records, result = patcher.apply([record])
    assert new_records[0].method == "post"
    assert new_records[0].path == "/api/patched"
    assert result.patched_count == 1


def test_patch_result_str():
    r = PatchResult(patched_count=3, skipped_count=1)
    assert "patched=3" in str(r)
    assert "skipped=1" in str(r)


def test_patch_storage(tmp_path):
    from reqtrace.storage import LogStorage
    storage = LogStorage(str(tmp_path / "logs.jsonl"))
    storage.save(make_record(method="GET", path="/a"))
    storage.save(make_record(method="POST", path="/b"))

    patcher = Patcher()
    patcher.add_rule(PatchRule(field_name="method", transform=str.lower))
    result = patch_storage(storage, patcher)

    assert result.patched_count == 2
    records = storage.load_all()
    assert all(r.method in ("get", "post") for r in records)
