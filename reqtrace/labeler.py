"""Automatic labeling of request records based on configurable rules."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from reqtrace.storage import RequestRecord


@dataclass
class LabelRule:
    """A single rule that maps a predicate to a label string."""

    label: str
    predicate: Callable[[RequestRecord], bool]
    description: str = ""

    def matches(self, record: RequestRecord) -> bool:
        try:
            return bool(self.predicate(record))
        except Exception:
            return False


@dataclass
class LabelResult:
    """Result of labeling a collection of records."""

    labeled: Dict[str, List[str]] = field(default_factory=dict)  # record_id -> labels
    label_counts: Dict[str, int] = field(default_factory=dict)

    def total_labeled(self) -> int:
        return sum(1 for labels in self.labeled.values() if labels)

    def __str__(self) -> str:
        lines = [f"Total records labeled: {self.total_labeled()}"]
        for label, count in sorted(self.label_counts.items()):
            lines.append(f"  {label}: {count}")
        return "\n".join(lines)


class Labeler:
    """Applies multiple label rules to request records."""

    def __init__(self) -> None:
        self._rules: List[LabelRule] = []

    def add_rule(self, rule: LabelRule) -> None:
        self._rules.append(rule)

    def label_record(self, record: RequestRecord) -> List[str]:
        """Return all matching labels for a single record."""
        return [rule.label for rule in self._rules if rule.matches(record)]

    def label_all(self, records: List[RequestRecord]) -> LabelResult:
        """Label a list of records and aggregate counts."""
        result = LabelResult()
        for record in records:
            labels = self.label_record(record)
            result.labeled[record.id] = labels
            for lbl in labels:
                result.label_counts[lbl] = result.label_counts.get(lbl, 0) + 1
        return result


def default_labeler() -> Labeler:
    """Return a Labeler pre-loaded with sensible default rules."""
    labeler = Labeler()
    labeler.add_rule(LabelRule("slow", lambda r: r.duration_ms > 1000, "duration > 1s"))
    labeler.add_rule(LabelRule("error", lambda r: r.status_code >= 500, "5xx response"))
    labeler.add_rule(LabelRule("client-error", lambda r: 400 <= r.status_code < 500, "4xx response"))
    labeler.add_rule(LabelRule("large-response", lambda r: len(r.response_body or "") > 10_000, "response > 10KB"))
    labeler.add_rule(LabelRule("mutation", lambda r: r.method in ("POST", "PUT", "PATCH", "DELETE"), "mutating method"))
    return labeler
