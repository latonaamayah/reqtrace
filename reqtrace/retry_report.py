"""Format retry outcomes into human-readable reports."""

from __future__ import annotations

from typing import List

from reqtrace.retrier import RetryOutcome


def format_retry_report(outcomes: List[RetryOutcome]) -> str:
    """Return a multi-line summary of retry outcomes."""
    if not outcomes:
        return "No retry outcomes to report."

    total = len(outcomes)
    succeeded = sum(1 for o in outcomes if o.succeeded)
    failed = total - succeeded
    total_attempts = sum(o.attempts for o in outcomes)

    lines = [
        f"Retry Report",
        f"============",
        f"Total records : {total}",
        f"Succeeded     : {succeeded}",
        f"Failed        : {failed}",
        f"Total attempts: {total_attempts}",
        "",
        "Details:",
    ]

    for o in outcomes:
        final = o.final_result
        status_str = str(final.status_code) if final and final.status_code else "ERR"
        error_str = f" [{final.error}]" if final and final.error else ""
        flag = "✓" if o.succeeded else "✗"
        lines.append(
            f"  {flag} {o.record.method} {o.record.path}"
            f" → {status_str}{error_str}"
            f" (attempts: {o.attempts})"
        )

    return "\n".join(lines)


def retry_summary_dict(outcomes: List[RetryOutcome]) -> dict:
    """Return a dict suitable for JSON serialisation."""
    total = len(outcomes)
    succeeded = sum(1 for o in outcomes if o.succeeded)
    return {
        "total": total,
        "succeeded": succeeded,
        "failed": total - succeeded,
        "total_attempts": sum(o.attempts for o in outcomes),
        "records": [
            {
                "record_id": o.record.record_id,
                "method": o.record.method,
                "path": o.record.path,
                "attempts": o.attempts,
                "succeeded": o.succeeded,
                "final_status": o.final_result.status_code if o.final_result else None,
                "final_error": o.final_result.error if o.final_result else None,
            }
            for o in outcomes
        ],
    }
