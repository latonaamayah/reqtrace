"""Formatting helpers for pool replay results."""
from __future__ import annotations

from typing import Dict, List

from reqtrace.replayer_pool import PoolResult


def pool_summary_dict(result: PoolResult) -> Dict[str, object]:
    """Return a plain dict suitable for JSON serialisation."""
    status_counts: Dict[str, int] = {}
    total_duration = 0.0

    for r in result.results:
        key = str(r.status_code) if r.status_code is not None else "unknown"
        status_counts[key] = status_counts.get(key, 0) + 1
        if r.duration_ms is not None:
            total_duration += r.duration_ms

    avg_duration = (
        total_duration / len(result.results) if result.results else 0.0
    )

    return {
        "total": len(result.results) + result.error_count,
        "success": result.success_count,
        "errors": result.error_count,
        "status_counts": status_counts,
        "avg_duration_ms": round(avg_duration, 2),
    }


def format_pool_report(result: PoolResult) -> str:
    """Return a human-readable multi-line report string."""
    lines: List[str] = []
    summary = pool_summary_dict(result)

    lines.append("=== Pool Replay Report ===")
    lines.append(f"  Total replayed : {summary['total']}")
    lines.append(f"  Successful     : {summary['success']}")
    lines.append(f"  Errors         : {summary['errors']}")
    lines.append(f"  Avg duration   : {summary['avg_duration_ms']} ms")

    if summary["status_counts"]:
        lines.append("  Status breakdown:")
        for code, count in sorted(summary["status_counts"].items()):
            lines.append(f"    {code}: {count}")

    if result.errors:
        lines.append("  Error details:")
        for err in result.errors:
            lines.append(f"    - {err}")

    return "\n".join(lines)
