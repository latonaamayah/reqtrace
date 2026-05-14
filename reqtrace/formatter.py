"""Pretty-print a RequestRecord as a human-readable summary."""

from __future__ import annotations

from typing import Optional

from reqtrace.storage import RequestRecord


_STATUS_COLORS = {
    2: "\033[32m",   # green
    3: "\033[36m",   # cyan
    4: "\033[33m",   # yellow
    5: "\033[31m",   # red
}
_RESET = "\033[0m"


def _status_color(status: int) -> str:
    return _STATUS_COLORS.get(status // 100, "")


def format_record(
    record: RequestRecord,
    *,
    color: bool = False,
    show_headers: bool = False,
    show_body: bool = False,
    max_body_len: int = 256,
) -> str:
    """Return a formatted string representation of *record*.

    Parameters
    ----------
    record:
        The request/response record to format.
    color:
        Emit ANSI colour codes when ``True``.
    show_headers:
        Include request and response headers in the output.
    show_body:
        Include request and response bodies in the output.
    max_body_len:
        Maximum number of characters to display for each body field.
    """
    lines: list[str] = []

    status_str = str(record.response_status)
    if color:
        c = _status_color(record.response_status)
        status_str = f"{c}{status_str}{_RESET}"

    lines.append(
        f"[{record.timestamp}] {record.method} {record.path}"
        f" -> {status_str}  ({record.duration_ms:.1f} ms)"
    )

    if show_headers:
        if record.request_headers:
            lines.append("  Request Headers:")
            for k, v in record.request_headers.items():
                lines.append(f"    {k}: {v}")
        if record.response_headers:
            lines.append("  Response Headers:")
            for k, v in record.response_headers.items():
                lines.append(f"    {k}: {v}")

    if show_body:
        for label, body in (
            ("Request Body", record.request_body),
            ("Response Body", record.response_body),
        ):
            if body:
                snippet = body[:max_body_len]
                suffix = "…" if len(body) > max_body_len else ""
                lines.append(f"  {label}: {snippet}{suffix}")

    return "\n".join(lines)


def format_records(
    records: list[RequestRecord],
    **kwargs,
) -> str:
    """Format multiple records separated by blank lines."""
    if not records:
        return "(no records)"
    return "\n\n".join(format_record(r, **kwargs) for r in records)
