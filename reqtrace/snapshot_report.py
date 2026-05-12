"""Formatting helpers for snapshot comparison reports."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from reqtrace.storage import RequestRecord


@dataclass
class SnapshotDiff:
    """Summary of differences between a snapshot and current records."""
    snapshot_name: str
    only_in_snapshot: List[str] = field(default_factory=list)   # paths
    only_in_current: List[str] = field(default_factory=list)
    status_changed: List[Dict[str, object]] = field(default_factory=list)

    @property
    def has_differences(self) -> bool:
        return bool(self.only_in_snapshot or self.only_in_current or self.status_changed)


def compare_with_snapshot(
    snapshot_records: List[RequestRecord],
    current_records: List[RequestRecord],
    snapshot_name: str = "snapshot",
) -> SnapshotDiff:
    """Compare *snapshot_records* against *current_records* by (method, path)."""
    diff = SnapshotDiff(snapshot_name=snapshot_name)

    snap_index: Dict[str, RequestRecord] = {}
    for r in snapshot_records:
        key = f"{r.method}:{r.path}"
        snap_index[key] = r

    curr_index: Dict[str, RequestRecord] = {}
    for r in current_records:
        key = f"{r.method}:{r.path}"
        curr_index[key] = r

    for key, snap_r in snap_index.items():
        if key not in curr_index:
            diff.only_in_snapshot.append(snap_r.path)
        else:
            curr_r = curr_index[key]
            if snap_r.status_code != curr_r.status_code:
                diff.status_changed.append(
                    {
                        "path": snap_r.path,
                        "method": snap_r.method,
                        "snapshot_status": snap_r.status_code,
                        "current_status": curr_r.status_code,
                    }
                )

    for key, curr_r in curr_index.items():
        if key not in snap_index:
            diff.only_in_current.append(curr_r.path)

    return diff


def format_snapshot_diff(diff: SnapshotDiff) -> str:
    lines: List[str] = [f"Snapshot diff: '{diff.snapshot_name}'"]
    if not diff.has_differences:
        lines.append("  No differences found.")
        return "\n".join(lines)
    if diff.only_in_snapshot:
        lines.append("  Only in snapshot:")
        for p in diff.only_in_snapshot:
            lines.append(f"    - {p}")
    if diff.only_in_current:
        lines.append("  Only in current:")
        for p in diff.only_in_current:
            lines.append(f"    + {p}")
    if diff.status_changed:
        lines.append("  Status changed:")
        for c in diff.status_changed:
            lines.append(
                f"    ~ {c['method']} {c['path']}: {c['snapshot_status']} -> {c['current_status']}"
            )
    return "\n".join(lines)
