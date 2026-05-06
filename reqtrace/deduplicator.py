"""Deduplicator: identify and remove duplicate request records."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import List, Tuple

from reqtrace.storage import RequestRecord


def _record_fingerprint(record: RequestRecord) -> str:
    """Return a stable hash representing the logical identity of a record."""
    key_parts = {
        "method": record.method,
        "path": record.path,
        "query": record.query_string,
        "request_headers": dict(sorted(record.request_headers.items())),
        "body": record.request_body,
    }
    raw = json.dumps(key_parts, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


@dataclass
class DeduplicationResult:
    unique: List[RequestRecord]
    duplicates: List[RequestRecord]

    @property
    def duplicate_count(self) -> int:
        return len(self.duplicates)

    @property
    def unique_count(self) -> int:
        return len(self.unique)

    def __str__(self) -> str:
        return (
            f"DeduplicationResult: {self.unique_count} unique, "
            f"{self.duplicate_count} duplicates removed"
        )


def deduplicate(records: List[RequestRecord]) -> DeduplicationResult:
    """Return unique records (first occurrence wins) and the duplicates."""
    seen: dict = {}
    unique: List[RequestRecord] = []
    duplicates: List[RequestRecord] = []

    for record in records:
        fp = _record_fingerprint(record)
        if fp in seen:
            duplicates.append(record)
        else:
            seen[fp] = record
            unique.append(record)

    return DeduplicationResult(unique=unique, duplicates=duplicates)


def find_duplicate_groups(
    records: List[RequestRecord],
) -> List[List[RequestRecord]]:
    """Group records by fingerprint, returning only groups with >1 member."""
    groups: dict = {}
    for record in records:
        fp = _record_fingerprint(record)
        groups.setdefault(fp, []).append(record)
    return [group for group in groups.values() if len(group) > 1]
