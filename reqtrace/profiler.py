"""Request profiler: bucket records by duration and report percentiles."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Dict, Sequence

from reqtrace.storage import RequestRecord


@dataclass
class ProfileResult:
    count: int
    min_ms: float
    max_ms: float
    mean_ms: float
    p50_ms: float
    p90_ms: float
    p99_ms: float
    buckets: Dict[str, int] = field(default_factory=dict)

    def __str__(self) -> str:
        lines = [
            f"count={self.count}  min={self.min_ms:.1f}ms  max={self.max_ms:.1f}ms",
            f"mean={self.mean_ms:.1f}ms  p50={self.p50_ms:.1f}ms  "
            f"p90={self.p90_ms:.1f}ms  p99={self.p99_ms:.1f}ms",
        ]
        if self.buckets:
            lines.append("buckets: " + "  ".join(f"{k}:{v}" for k, v in sorted(self.buckets.items())))
        return "\n".join(lines)


DEFAULT_BOUNDARIES = [50, 100, 250, 500, 1000, 2500, 5000]


def _percentile(sorted_values: List[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    idx = math.ceil(pct / 100.0 * len(sorted_values)) - 1
    return sorted_values[max(0, min(idx, len(sorted_values) - 1))]


def _bucket_label(ms: float, boundaries: List[int]) -> str:
    for b in boundaries:
        if ms < b:
            return f"<{b}ms"
    return f">={boundaries[-1]}ms"


def profile(
    records: Sequence[RequestRecord],
    boundaries: List[int] | None = None,
) -> ProfileResult:
    """Compute duration statistics and bucket distribution for *records*."""
    if boundaries is None:
        boundaries = DEFAULT_BOUNDARIES

    durations = sorted(r.duration_ms for r in records)
    if not durations:
        return ProfileResult(
            count=0, min_ms=0.0, max_ms=0.0, mean_ms=0.0,
            p50_ms=0.0, p90_ms=0.0, p99_ms=0.0, buckets={},
        )

    buckets: Dict[str, int] = {}
    for ms in durations:
        label = _bucket_label(ms, boundaries)
        buckets[label] = buckets.get(label, 0) + 1

    return ProfileResult(
        count=len(durations),
        min_ms=durations[0],
        max_ms=durations[-1],
        mean_ms=sum(durations) / len(durations),
        p50_ms=_percentile(durations, 50),
        p90_ms=_percentile(durations, 90),
        p99_ms=_percentile(durations, 99),
        buckets=buckets,
    )


def profile_by_path(records: Sequence[RequestRecord]) -> Dict[str, ProfileResult]:
    """Return a ProfileResult per unique (method, path) pair."""
    groups: Dict[str, list] = {}
    for r in records:
        key = f"{r.method} {r.path}"
        groups.setdefault(key, []).append(r)
    return {k: profile(v) for k, v in groups.items()}
