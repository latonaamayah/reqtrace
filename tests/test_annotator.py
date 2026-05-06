"""Tests for reqtrace.annotator."""
import pytest

from reqtrace.annotator import (
    Annotation,
    AnnotationStore,
    annotate_record,
    format_annotations,
)
from reqtrace.storage import LogStorage, RequestRecord


def make_record(rid: str = "abc123", method: str = "GET", path: str = "/api") -> RequestRecord:
    return RequestRecord(
        id=rid,
        method=method,
        path=path,
        query_string="",
        request_headers={},
        request_body="",
        status_code=200,
        response_headers={},
        response_body="",
        duration_ms=10.0,
        timestamp="2024-01-01T00:00:00",
    )


@pytest.fixture
def store() -> AnnotationStore:
    return AnnotationStore()


def test_add_annotation(store):
    ann = store.add("rec1", "looks good", author="alice")
    assert isinstance(ann, Annotation)
    assert ann.record_id == "rec1"
    assert ann.note == "looks good"
    assert ann.author == "alice"


def test_get_returns_empty_for_unknown(store):
    assert store.get("missing") == []


def test_get_returns_all_annotations(store):
    store.add("r1", "first")
    store.add("r1", "second")
    notes = store.get("r1")
    assert len(notes) == 2
    assert notes[0].note == "first"
    assert notes[1].note == "second"


def test_remove_by_index(store):
    store.add("r1", "keep")
    store.add("r1", "delete me")
    removed = store.remove("r1", 1)
    assert removed is not None
    assert removed.note == "delete me"
    assert len(store.get("r1")) == 1


def test_remove_invalid_index_returns_none(store):
    store.add("r1", "only one")
    assert store.remove("r1", 99) is None


def test_all_ids(store):
    store.add("r1", "note")
    store.add("r2", "note")
    ids = store.all_ids()
    assert set(ids) == {"r1", "r2"}


def test_annotation_str():
    ann = Annotation(record_id="x", note="hello", author="bob")
    assert str(ann) == "[bob] hello"


def test_annotate_record_returns_none_for_missing(tmp_path):
    storage = LogStorage(str(tmp_path / "logs.jsonl"))
    store = AnnotationStore()
    result = annotate_record(storage, "nonexistent", "note", store=store)
    assert result is None


def test_annotate_record_success(tmp_path):
    storage = LogStorage(str(tmp_path / "logs.jsonl"))
    rec = make_record(rid="xyz")
    storage.save(rec)
    store = AnnotationStore()
    ann = annotate_record(storage, "xyz", "interesting", author="dev", store=store)
    assert ann is not None
    assert ann.note == "interesting"
    assert store.get("xyz")[0].author == "dev"


def test_format_annotations_no_notes():
    rec = make_record(rid="r1")
    out = format_annotations(rec, [])
    assert "(no annotations)" in out
    assert "r1" in out


def test_format_annotations_with_notes():
    rec = make_record(rid="r1", method="POST", path="/submit")
    anns = [Annotation("r1", "check this", "alice"), Annotation("r1", "agreed", "bob")]
    out = format_annotations(rec, anns)
    assert "POST" in out
    assert "check this" in out
    assert "agreed" in out
    assert "0:" in out
    assert "1:" in out
