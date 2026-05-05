"""Group RequestRecords by various dimensions for analysis."""

from collections import defaultdict
from typing import Callable, Dict, List

from reqtrace.storage import RequestRecord


def _path_prefix(depth: int = 1) -> Callable[[RequestRecord], str]:
    """Return a key function that groups by the first `depth` path segments."""
    def key(record: RequestRecord) -> str:
        parts = record.path.strip("/").split("/")
        return "/" + "/".join(parts[:depth])
    return key


def group_by(
    records: List[RequestRecord],
    key_fn: Callable[[RequestRecord], str],
) -> Dict[str, List[RequestRecord]]:
    """Group records by an arbitrary key function."""
    groups: Dict[str, List[RequestRecord]] = defaultdict(list)
    for record in records:
        groups[key_fn(record)].append(record)
    return dict(groups)


def group_by_method(records: List[RequestRecord]) -> Dict[str, List[RequestRecord]]:
    """Group records by HTTP method."""
    return group_by(records, lambda r: r.method.upper())


def group_by_status(records: List[RequestRecord]) -> Dict[str, List[RequestRecord]]:
    """Group records by HTTP status code."""
    return group_by(records, lambda r: str(r.status_code))


def group_by_path_prefix(
    records: List[RequestRecord], depth: int = 1
) -> Dict[str, List[RequestRecord]]:
    """Group records by the first `depth` URL path segments."""
    return group_by(records, _path_prefix(depth))


def format_groups(groups: Dict[str, List[RequestRecord]]) -> str:
    """Return a human-readable summary of grouped records."""
    if not groups:
        return "No records."
    lines = []
    for key in sorted(groups):
        count = len(groups[key])
        avg_ms = (
            sum(r.duration_ms for r in groups[key]) / count
            if count else 0.0
        )
        lines.append(f"  {key}: {count} request(s), avg {avg_ms:.1f} ms")
    return "\n".join(lines)
