"""Highlight records that match user-defined criteria for visual inspection."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from reqtrace.storage import RequestRecord


@dataclass
class HighlightRule:
    label: str
    color: str  # ANSI color code, e.g. '\033[91m' for red
    predicate: Callable[[RequestRecord], bool]

    def matches(self, record: RequestRecord) -> bool:
        try:
            return self.predicate(record)
        except Exception:
            return False


@dataclass
class HighlightResult:
    record: RequestRecord
    matched_rule: Optional[HighlightRule] = None

    @property
    def is_highlighted(self) -> bool:
        return self.matched_rule is not None

    def format_label(self) -> str:
        if self.matched_rule is None:
            return ""
        reset = "\033[0m"
        return f"{self.matched_rule.color}[{self.matched_rule.label}]{reset}"


class Highlighter:
    """Apply highlight rules to records, returning the first matching rule per record."""

    def __init__(self) -> None:
        self._rules: List[HighlightRule] = []

    def add_rule(self, rule: HighlightRule) -> None:
        self._rules.append(rule)

    def highlight_record(self, record: RequestRecord) -> HighlightResult:
        for rule in self._rules:
            if rule.matches(record):
                return HighlightResult(record=record, matched_rule=rule)
        return HighlightResult(record=record)

    def highlight_all(
        self, records: List[RequestRecord]
    ) -> List[HighlightResult]:
        return [self.highlight_record(r) for r in records]

    def highlighted_only(
        self, records: List[RequestRecord]
    ) -> List[HighlightResult]:
        return [
            result
            for result in self.highlight_all(records)
            if result.is_highlighted
        ]
