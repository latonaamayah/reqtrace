"""Compare two sets of RequestRecords to identify regressions or differences."""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from reqtrace.storage import RequestRecord
from reqtrace.differ import RecordDiff, diff_records


@dataclass
class ComparisonReport:
    """Result of comparing a baseline set of records against a current set."""
    matched: List[Tuple[RequestRecord, RequestRecord]] = field(default_factory=list)
    unmatched_baseline: List[RequestRecord] = field(default_factory=list)
    unmatched_current: List[RequestRecord] = field(default_factory=list)
    diffs: List[RecordDiff] = field(default_factory=list)

    @property
    def regression_count(self) -> int:
        return sum(1 for d in self.diffs if d.has_changes)

    @property
    def total_compared(self) -> int:
        return len(self.matched)


def _match_key(record: RequestRecord) -> str:
    """Generate a match key from method and path."""
    return f"{record.method.upper()} {record.path}"


def compare_record_sets(
    baseline: List[RequestRecord],
    current: List[RequestRecord],
) -> ComparisonReport:
    """Match records by method+path and diff each pair."""
    report = ComparisonReport()

    baseline_map: dict[str, RequestRecord] = {}
    for rec in baseline:
        key = _match_key(rec)
        baseline_map[key] = rec

    current_map: dict[str, RequestRecord] = {}
    for rec in current:
        key = _match_key(rec)
        current_map[key] = rec

    all_keys = set(baseline_map) | set(current_map)
    for key in sorted(all_keys):
        b = baseline_map.get(key)
        c = current_map.get(key)
        if b and c:
            report.matched.append((b, c))
            report.diffs.append(diff_records(b, c))
        elif b:
            report.unmatched_baseline.append(b)
        else:
            report.unmatched_current.append(c)

    return report


def format_comparison_report(report: ComparisonReport) -> str:
    """Return a human-readable summary of the comparison report."""
    lines = []
    lines.append(f"Compared {report.total_compared} matched pair(s).")
    lines.append(f"Regressions (changed): {report.regression_count}")
    lines.append(f"Only in baseline: {len(report.unmatched_baseline)}")
    lines.append(f"Only in current:  {len(report.unmatched_current)}")

    for diff in report.diffs:
        if diff.has_changes:
            lines.append("")
            lines.append(diff.format())

    if report.unmatched_baseline:
        lines.append("\nMissing from current:")
        for r in report.unmatched_baseline:
            lines.append(f"  - {r.method} {r.path}")

    if report.unmatched_current:
        lines.append("\nNew in current (no baseline):")
        for r in report.unmatched_current:
            lines.append(f"  + {r.method} {r.path}")

    return "\n".join(lines)
