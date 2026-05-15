"""Formatting helpers for rate-limit analysis results."""
from __future__ import annotations

from typing import Any, Dict, List

from reqtrace.ratelimiter import RateLimitResult, EndpointRate


def ratelimit_summary_dict(result: RateLimitResult) -> Dict[str, Any]:
    """Return a JSON-serialisable summary of a :class:`RateLimitResult`."""
    return {
        "window_seconds": round(result.window_seconds, 3),
        "max_rps": result.max_rps,
        "total_endpoints": len(result.endpoint_rates),
        "violation_count": result.violation_count,
        "endpoints": [
            {
                "method": er.method,
                "path": er.path,
                "count": er.count,
                "rps": round(er.rps, 4),
                "exceeds_limit": er.exceeds_limit,
            }
            for er in result.endpoint_rates
        ],
    }


def format_ratelimit_report(result: RateLimitResult) -> str:
    """Return a human-readable multi-line report string."""
    lines: List[str] = [
        "=" * 56,
        "Rate-Limit Analysis Report",
        "=" * 56,
        f"Observation window : {result.window_seconds:.3f} s",
        f"Max allowed RPS    : {result.max_rps:.2f}",
        f"Endpoints analysed : {len(result.endpoint_rates)}",
        f"Violations         : {result.violation_count}",
        "-" * 56,
    ]

    if not result.endpoint_rates:
        lines.append("  (no records to analyse)")
    else:
        for er in result.endpoint_rates:
            marker = "  [!]" if er.exceeds_limit else "     "
            lines.append(
                f"{marker} {er.method:<7} {er.path:<30} "
                f"{er.rps:>8.2f} rps  ({er.count} req)"
            )

    lines.append("=" * 56)
    return "\n".join(lines)
