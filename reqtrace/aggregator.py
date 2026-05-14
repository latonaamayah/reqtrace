"""Aggregate request records into statistical summaries per endpoint."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from reqtrace.storage import RequestRecord


@dataclass
class EndpointStats:
    method: str
    path: str
    count: int = 0
    total_duration_ms: float = 0.0
    error_count: int = 0
    status_codes: Dict[int, int] = field(default_factory=dict)

    @property
    def avg_duration_ms(self) -> float:
        return self.total_duration_ms / self.count if self.count else 0.0

    @property
    def error_rate(self) -> float:
        return self.error_count / self.count if self.count else 0.0

    def __str__(self) -> str:
        return (
            f"{self.method} {self.path}: count={self.count}, "
            f"avg_duration={self.avg_duration_ms:.1f}ms, "
            f"error_rate={self.error_rate:.1%}"
        )


@dataclass
class AggregationResult:
    endpoints: Dict[str, EndpointStats] = field(default_factory=dict)

    @property
    def total_requests(self) -> int:
        return sum(s.count for s in self.endpoints.values())

    def sorted_by_count(self) -> List[EndpointStats]:
        return sorted(self.endpoints.values(), key=lambda s: s.count, reverse=True)

    def sorted_by_avg_duration(self) -> List[EndpointStats]:
        return sorted(self.endpoints.values(), key=lambda s: s.avg_duration_ms, reverse=True)

    def __str__(self) -> str:
        lines = [f"Aggregation over {self.total_requests} request(s):"]
        for stats in self.sorted_by_count():
            lines.append(f"  {stats}")
        return "\n".join(lines)


def aggregate(records: List[RequestRecord]) -> AggregationResult:
    """Aggregate a list of records into per-endpoint statistics."""
    result = AggregationResult()
    for record in records:
        key = f"{record.method}:{record.path}"
        if key not in result.endpoints:
            result.endpoints[key] = EndpointStats(method=record.method, path=record.path)
        stats = result.endpoints[key]
        stats.count += 1
        stats.total_duration_ms += record.duration_ms
        if record.status_code >= 400:
            stats.error_count += 1
        stats.status_codes[record.status_code] = (
            stats.status_codes.get(record.status_code, 0) + 1
        )
    return result
