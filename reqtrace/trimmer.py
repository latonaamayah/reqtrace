"""Trim records from storage to keep only the most recent N entries."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from reqtrace.storage import LogStorage, RequestRecord


@dataclass
class TrimResult:
    kept: int
    removed: int
    total_before: int

    def __str__(self) -> str:
        return (
            f"Trim complete: {self.total_before} records found, "
            f"{self.kept} kept, {self.removed} removed."
        )


def trim(
    storage: LogStorage,
    keep: int,
    *,
    newest_first: bool = True,
) -> TrimResult:
    """Trim records in *storage* so that at most *keep* records remain.

    By default the *newest* records are retained (sorted descending by
    ``timestamp``).  Pass ``newest_first=False`` to retain the oldest.

    The storage file is rewritten in-place with the surviving records.
    """
    if keep < 0:
        raise ValueError(f"keep must be >= 0, got {keep}")

    all_records: List[RequestRecord] = storage.load_all()
    total_before = len(all_records)

    sorted_records = sorted(
        all_records,
        key=lambda r: r.timestamp,
        reverse=newest_first,
    )

    survivors = sorted_records[:keep]
    removed_count = max(0, total_before - len(survivors))

    # Persist survivors (restore chronological order for readability)
    survivors_ordered = sorted(survivors, key=lambda r: r.timestamp)
    _rewrite(storage, survivors_ordered)

    return TrimResult(
        kept=len(survivors),
        removed=removed_count,
        total_before=total_before,
    )


def _rewrite(storage: LogStorage, records: List[RequestRecord]) -> None:
    """Overwrite the storage file with *records*."""
    # Clear by writing an empty list then re-saving each record.
    storage.path.write_text("")
    for record in records:
        storage.save(record)
