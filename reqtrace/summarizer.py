"""Summarize logged request records for quick diagnostics."""

from collections import Counter, defaultdict
from typing import List, Dict, Any

from reqtrace.storage import RequestRecord


def summarize(records: List[RequestRecord]) -> Dict[str, Any]:
    """Return a summary dict for a list of RequestRecord objects."""
    if not records:
        return {
            "total": 0,
            "methods": {},
            "status_codes": {},
            "top_paths": [],
            "avg_duration_ms": None,
            "slowest": None,
            "fastest": None,
            "error_rate": 0.0,
        }

    methods: Counter = Counter(r.method for r in records)
    status_codes: Counter = Counter(r.status_code for r in records)
    path_counts: Counter = Counter(r.path for r in records)

    durations = [r.duration_ms for r in records if r.duration_ms is not None]
    avg_duration = sum(durations) / len(durations) if durations else None

    sorted_by_duration = sorted(
        [r for r in records if r.duration_ms is not None],
        key=lambda r: r.duration_ms,
    )
    slowest = sorted_by_duration[-1] if sorted_by_duration else None
    fastest = sorted_by_duration[0] if sorted_by_duration else None

    error_count = sum(1 for r in records if r.status_code >= 400)
    error_rate = error_count / len(records)

    return {
        "total": len(records),
        "methods": dict(methods),
        "status_codes": {str(k): v for k, v in status_codes.items()},
        "top_paths": path_counts.most_common(5),
        "avg_duration_ms": round(avg_duration, 2) if avg_duration is not None else None,
        "slowest": {"path": slowest.path, "duration_ms": slowest.duration_ms} if slowest else None,
        "fastest": {"path": fastest.path, "duration_ms": fastest.duration_ms} if fastest else None,
        "error_rate": round(error_rate, 4),
    }


def format_summary(summary: Dict[str, Any]) -> str:
    """Return a human-readable string representation of a summary dict."""
    lines = [
        f"Total requests : {summary['total']}",
        f"Methods        : {summary['methods']}",
        f"Status codes   : {summary['status_codes']}",
        f"Avg duration   : {summary['avg_duration_ms']} ms",
        f"Slowest        : {summary['slowest']}",
        f"Fastest        : {summary['fastest']}",
        f"Error rate     : {summary['error_rate'] * 100:.2f}%",
        "Top paths:",
    ]
    for path, count in summary.get("top_paths", []):
        lines.append(f"  {count:>4}x  {path}")
    return "\n".join(lines)
