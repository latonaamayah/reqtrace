"""Merge multiple log storage files into a single output storage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from reqtrace.storage import LogStorage, RequestRecord


@dataclass
class MergeResult:
    total_sources: int
    records_per_source: List[int]
    total_merged: int
    duplicates_skipped: int

    def __str__(self) -> str:
        lines = [
            f"Sources merged : {self.total_sources}",
            f"Total records  : {self.total_merged}",
            f"Duplicates skip: {self.duplicates_skipped}",
        ]
        for i, count in enumerate(self.records_per_source):
            lines.append(f"  source[{i}]    : {count} records")
        return "\n".join(lines)


def _record_key(record: RequestRecord) -> tuple:
    """Unique identity key for deduplication during merge."""
    return (
        record.timestamp,
        record.method,
        record.path,
        record.status_code,
    )


def merge(
    sources: List[LogStorage],
    destination: LogStorage,
    deduplicate: bool = True,
) -> MergeResult:
    """Load records from all *sources* and write them to *destination*.

    Parameters
    ----------
    sources:
        List of :class:`LogStorage` instances to read from.
    destination:
        :class:`LogStorage` to write merged records into.
    deduplicate:
        When ``True`` (default) records with identical (timestamp, method,
        path, status_code) tuples are written only once.
    """
    seen: set = set()
    records_per_source: List[int] = []
    duplicates_skipped = 0
    merged: List[RequestRecord] = []

    for storage in sources:
        batch = storage.load_all()
        records_per_source.append(len(batch))
        for record in batch:
            if deduplicate:
                key = _record_key(record)
                if key in seen:
                    duplicates_skipped += 1
                    continue
                seen.add(key)
            merged.append(record)

    for record in merged:
        destination.save(record)

    return MergeResult(
        total_sources=len(sources),
        records_per_source=records_per_source,
        total_merged=len(merged),
        duplicates_skipped=duplicates_skipped,
    )
