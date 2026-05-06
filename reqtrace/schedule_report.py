"""Format a human-readable report from a batch of scheduled replay results."""
from __future__ import annotations

from typing import Dict, List

from reqtrace.replayer import ReplayResult


def schedule_run_summary(results: List[ReplayResult]) -> Dict[str, object]:
    """Return a dict with aggregate stats for one scheduler run."""
    total = len(results)
    successes = [r for r in results if r.status_code is not None and r.status_code < 400]
    failures = [r for r in results if r not in successes]
    errors = [r for r in results if r.error]
    status_counts: Dict[int, int] = {}
    for r in results:
        if r.status_code is not None:
            status_counts[r.status_code] = status_counts.get(r.status_code, 0) + 1
    return {
        "total": total,
        "success_count": len(successes),
        "failure_count": len(failures),
        "error_count": len(errors),
        "status_counts": status_counts,
    }


def format_schedule_report(run_number: int, results: List[ReplayResult]) -> str:
    """Return a formatted string summarising one scheduler run."""
    if not results:
        return f"Run #{run_number}: no requests replayed."

    summary = schedule_run_summary(results)
    lines: List[str] = [
        f"Run #{run_number}: {summary['total']} request(s) replayed",
        f"  OK (< 400): {summary['success_count']}",
        f"  Failed    : {summary['failure_count']}",
        f"  Errors    : {summary['error_count']}",
    ]
    if summary["status_counts"]:
        status_line = "  Status codes: " + ", ".join(
            f"{code}×{count}" for code, count in sorted(summary["status_counts"].items())  # type: ignore[arg-type]
        )
        lines.append(status_line)
    return "\n".join(lines)
