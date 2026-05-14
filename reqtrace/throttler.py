"""Rate-based throttling: keep only records within a max-requests-per-second budget."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict

from reqtrace.storage import RequestRecord


@dataclass
class ThrottleConfig:
    max_rps: float  # maximum requests per second to retain
    window_ms: float = 1000.0  # bucket window in milliseconds

    def __post_init__(self) -> None:
        if self.max_rps <= 0:
            raise ValueError("max_rps must be positive")
        if self.window_ms <= 0:
            raise ValueError("window_ms must be positive")


@dataclass
class ThrottleResult:
    kept: List[RequestRecord]
    dropped: List[RequestRecord]

    @property
    def kept_count(self) -> int:
        return len(self.kept)

    @property
    def dropped_count(self) -> int:
        return len(self.dropped)

    def __str__(self) -> str:
        return (
            f"ThrottleResult: kept={self.kept_count}, dropped={self.dropped_count}"
        )


def throttle_records(
    records: List[RequestRecord], config: ThrottleConfig
) -> ThrottleResult:
    """Apply rate-based throttling to a list of records.

    Records are assumed to be in any order; they are sorted by timestamp
    internally.  Within each time window of `config.window_ms` milliseconds
    only the first `floor(max_rps * window_ms / 1000)` records are kept.
    """
    if not records:
        return ThrottleResult(kept=[], dropped=[])

    import math

    budget_per_window = max(1, math.floor(config.max_rps * config.window_ms / 1000.0))

    sorted_records = sorted(records, key=lambda r: r.timestamp)

    # bucket key -> count of records already kept in that bucket
    bucket_counts: Dict[int, int] = {}
    kept: List[RequestRecord] = []
    dropped: List[RequestRecord] = []

    for record in sorted_records:
        # Convert ISO timestamp to milliseconds-since-epoch for bucketing
        bucket = int(_ts_to_ms(record.timestamp) / config.window_ms)
        count = bucket_counts.get(bucket, 0)
        if count < budget_per_window:
            kept.append(record)
            bucket_counts[bucket] = count + 1
        else:
            dropped.append(record)

    return ThrottleResult(kept=kept, dropped=dropped)


def _ts_to_ms(timestamp: str) -> float:
    """Parse an ISO-8601 timestamp string and return milliseconds since epoch."""
    from datetime import datetime, timezone

    try:
        dt = datetime.fromisoformat(timestamp)
    except ValueError:
        return 0.0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp() * 1000.0
