"""Timeline builder: orders records chronologically and computes gap durations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from reqtrace.storage import RequestRecord


@dataclass
class TimelineEntry:
    record: RequestRecord
    gap_before_ms: Optional[float]  # ms since previous request, None for first

    def __str__(self) -> str:
        gap = f"+{self.gap_before_ms:.1f}ms" if self.gap_before_ms is not None else "start"
        ts = self.record.timestamp
        method = self.record.method
        path = self.record.path
        status = self.record.status_code
        dur = self.record.duration_ms
        return f"[{ts}] ({gap}) {method} {path} -> {status} in {dur:.1f}ms"


@dataclass
class Timeline:
    entries: List[TimelineEntry] = field(default_factory=list)

    @property
    def total_span_ms(self) -> float:
        """Wall-clock ms between first and last request timestamps."""
        if len(self.entries) < 2:
            return 0.0
        first = self.entries[0].record.timestamp
        last = self.entries[-1].record.timestamp
        return max(0.0, (last - first) * 1000.0)

    def format(self) -> str:
        if not self.entries:
            return "No records in timeline."
        lines = [str(e) for e in self.entries]
        lines.append(f"Total span: {self.total_span_ms:.1f}ms over {len(self.entries)} request(s).")
        return "\n".join(lines)


def build_timeline(records: List[RequestRecord]) -> Timeline:
    """Sort records by timestamp and compute inter-request gaps."""
    if not records:
        return Timeline()

    sorted_records = sorted(records, key=lambda r: r.timestamp)
    entries: List[TimelineEntry] = []

    for i, rec in enumerate(sorted_records):
        if i == 0:
            gap = None
        else:
            prev_ts = sorted_records[i - 1].timestamp
            gap = max(0.0, (rec.timestamp - prev_ts) * 1000.0)
        entries.append(TimelineEntry(record=rec, gap_before_ms=gap))

    return Timeline(entries=entries)
