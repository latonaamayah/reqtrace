"""Diff two RequestRecord objects to highlight changes between requests."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from reqtrace.storage import RequestRecord


@dataclass
class FieldDiff:
    field: str
    old_value: Any
    new_value: Any

    def __str__(self) -> str:
        return f"  {self.field}:\n    - {self.old_value!r}\n    + {self.new_value!r}"


@dataclass
class RecordDiff:
    record_a_id: str
    record_b_id: str
    diffs: List[FieldDiff]

    @property
    def has_changes(self) -> bool:
        return len(self.diffs) > 0

    def format(self) -> str:
        if not self.has_changes:
            return f"Records {self.record_a_id} and {self.record_b_id} are identical."
        lines = [f"Diff {self.record_a_id} -> {self.record_b_id}:"]
        for d in self.diffs:
            lines.append(str(d))
        return "\n".join(lines)


_COMPARABLE_FIELDS = [
    "method",
    "path",
    "query_string",
    "request_headers",
    "request_body",
    "status_code",
    "response_headers",
    "response_body",
]


def diff_records(a: RequestRecord, b: RequestRecord) -> RecordDiff:
    """Compare two RequestRecord objects field by field."""
    diffs: List[FieldDiff] = []
    for field in _COMPARABLE_FIELDS:
        val_a = getattr(a, field, None)
        val_b = getattr(b, field, None)
        if val_a != val_b:
            diffs.append(FieldDiff(field=field, old_value=val_a, new_value=val_b))
    return RecordDiff(record_a_id=a.id, record_b_id=b.id, diffs=diffs)


def diff_by_index(
    records: List[RequestRecord], idx_a: int, idx_b: int
) -> Optional[RecordDiff]:
    """Diff two records from a list by their indices."""
    if idx_a < 0 or idx_b < 0 or idx_a >= len(records) or idx_b >= len(records):
        return None
    return diff_records(records[idx_a], records[idx_b])
