"""Rate limit analysis: detect endpoints that exceed request thresholds."""
from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict
from typing import Dict, List

from reqtrace.storage import RequestRecord


@dataclass
class EndpointRate:
    method: str
    path: str
    count: int
    window_seconds: float
    rps: float
    exceeds_limit: bool

    def __str__(self) -> str:
        flag = " [EXCEEDS LIMIT]" if self.exceeds_limit else ""
        return (
            f"{self.method} {self.path}: {self.count} req "
            f"over {self.window_seconds:.1f}s = {self.rps:.2f} rps{flag}"
        )


@dataclass
class RateLimitResult:
    window_seconds: float
    max_rps: float
    endpoint_rates: List[EndpointRate] = field(default_factory=list)

    @property
    def violating(self) -> List[EndpointRate]:
        return [e for e in self.endpoint_rates if e.exceeds_limit]

    @property
    def violation_count(self) -> int:
        return len(self.violating)

    def __str__(self) -> str:
        lines = [
            f"Rate limit analysis (window={self.window_seconds:.1f}s, "
            f"max_rps={self.max_rps:.2f})",
            f"Endpoints analysed : {len(self.endpoint_rates)}",
            f"Violations         : {self.violation_count}",
        ]
        for er in self.endpoint_rates:
            lines.append(f"  {er}")
        return "\n".join(lines)


def analyze_rate_limits(
    records: List[RequestRecord],
    max_rps: float = 10.0,
) -> RateLimitResult:
    """Analyse *records* and flag endpoints whose observed RPS exceeds *max_rps*."""
    if not records:
        return RateLimitResult(window_seconds=0.0, max_rps=max_rps)

    timestamps = [r.timestamp for r in records]
    window = max(timestamps) - min(timestamps)
    window_seconds = window if window > 0 else 1.0

    counts: Dict[tuple, int] = defaultdict(int)
    for r in records:
        counts[(r.method.upper(), r.path)] += 1

    endpoint_rates: List[EndpointRate] = []
    for (method, path), count in sorted(counts.items()):
        rps = count / window_seconds
        endpoint_rates.append(
            EndpointRate(
                method=method,
                path=path,
                count=count,
                window_seconds=window_seconds,
                rps=rps,
                exceeds_limit=rps > max_rps,
            )
        )

    return RateLimitResult(
        window_seconds=window_seconds,
        max_rps=max_rps,
        endpoint_rates=endpoint_rates,
    )
