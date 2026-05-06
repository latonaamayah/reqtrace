"""Annotator: attach free-form notes to recorded requests."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from reqtrace.storage import LogStorage, RequestRecord


@dataclass
class Annotation:
    record_id: str
    note: str
    author: str = "user"

    def __str__(self) -> str:
        return f"[{self.author}] {self.note}"


class AnnotationStore:
    """In-memory store mapping record IDs to lists of annotations."""

    def __init__(self) -> None:
        self._data: Dict[str, List[Annotation]] = {}

    def add(self, record_id: str, note: str, author: str = "user") -> Annotation:
        ann = Annotation(record_id=record_id, note=note, author=author)
        self._data.setdefault(record_id, []).append(ann)
        return ann

    def get(self, record_id: str) -> List[Annotation]:
        return list(self._data.get(record_id, []))

    def remove(self, record_id: str, index: int) -> Optional[Annotation]:
        notes = self._data.get(record_id, [])
        if 0 <= index < len(notes):
            return notes.pop(index)
        return None

    def all_ids(self) -> List[str]:
        return [rid for rid, notes in self._data.items() if notes]


def annotate_record(
    storage: LogStorage,
    record_id: str,
    note: str,
    author: str = "user",
    store: Optional[AnnotationStore] = None,
) -> Optional[Annotation]:
    """Add a note to a record that exists in *storage*.

    Returns the new Annotation, or None if the record is not found.
    """
    records = storage.load_all()
    if not any(r.id == record_id for r in records):
        return None
    if store is None:
        store = AnnotationStore()
    return store.add(record_id, note, author)


def format_annotations(record: RequestRecord, annotations: List[Annotation]) -> str:
    """Return a human-readable block of annotations for *record*."""
    header = f"{record.method} {record.path} [{record.id}]"
    if not annotations:
        return f"{header}\n  (no annotations)"
    lines = [header]
    for i, ann in enumerate(annotations):
        lines.append(f"  {i}: {ann}")
    return "\n".join(lines)
