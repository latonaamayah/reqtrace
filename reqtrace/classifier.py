"""Classify HTTP records into named categories based on configurable rules."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from reqtrace.storage import RequestRecord


@dataclass
class ClassifyRule:
    category: str
    predicate: Callable[[RequestRecord], bool]

    def matches(self, record: RequestRecord) -> bool:
        try:
            return self.predicate(record)
        except Exception:
            return False


@dataclass
class ClassificationResult:
    categories: Dict[str, List[RequestRecord]] = field(default_factory=dict)
    unclassified: List[RequestRecord] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(len(v) for v in self.categories.values()) + len(self.unclassified)

    @property
    def classified_count(self) -> int:
        return sum(len(v) for v in self.categories.values())

    def __str__(self) -> str:
        lines = [f"Classification: {self.classified_count}/{self.total} classified"]
        for cat, records in sorted(self.categories.items()):
            lines.append(f"  {cat}: {len(records)} record(s)")
        if self.unclassified:
            lines.append(f"  (unclassified): {len(self.unclassified)} record(s)")
        return "\n".join(lines)


class Classifier:
    def __init__(self) -> None:
        self._rules: List[ClassifyRule] = []

    def add_rule(self, category: str, predicate: Callable[[RequestRecord], bool]) -> None:
        self._rules.append(ClassifyRule(category=category, predicate=predicate))

    def classify(self, records: List[RequestRecord]) -> ClassificationResult:
        result = ClassificationResult()
        for record in records:
            matched: Optional[str] = None
            for rule in self._rules:
                if rule.matches(record):
                    matched = rule.category
                    break
            if matched is not None:
                result.categories.setdefault(matched, []).append(record)
            else:
                result.unclassified.append(record)
        return result
