"""Sort RequestRecord collections by various fields."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Optional

from reqtrace.storage import RequestRecord

SortField = Literal["timestamp", "duration_ms", "status_code", "method", "path"]
SortOrder = Literal["asc", "desc"]


@dataclass
class SortConfig:
    field: SortField = "timestamp"
    order: SortOrder = "asc"

    def __post_init__(self) -> None:
        valid_fields = {"timestamp", "duration_ms", "status_code", "method", "path"}
        if self.field not in valid_fields:
            raise ValueError(f"Invalid sort field '{self.field}'. Choose from {valid_fields}.")
        if self.order not in ("asc", "desc"):
            raise ValueError(f"Invalid sort order '{self.order}'. Use 'asc' or 'desc'.")


def _sort_key(record: RequestRecord, field: SortField):
    """Return a comparable key for *field* from *record*."""
    if field == "timestamp":
        return record.timestamp
    if field == "duration_ms":
        return record.duration_ms if record.duration_ms is not None else 0.0
    if field == "status_code":
        return record.response_status if record.response_status is not None else 0
    if field == "method":
        return record.method.upper()
    if field == "path":
        return record.path
    raise ValueError(f"Unknown field: {field}")


def sort_records(
    records: List[RequestRecord],
    config: Optional[SortConfig] = None,
) -> List[RequestRecord]:
    """Return a new list of *records* sorted according to *config*.

    The original list is not modified.
    """
    if config is None:
        config = SortConfig()
    reverse = config.order == "desc"
    return sorted(records, key=lambda r: _sort_key(r, config.field), reverse=reverse)
