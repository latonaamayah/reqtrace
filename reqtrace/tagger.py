"""Tag RequestRecords with user-defined labels based on simple rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List

from reqtrace.storage import RequestRecord


@dataclass
class TagRule:
    """A single tagging rule: if predicate matches, apply tag."""

    tag: str
    predicate: Callable[[RequestRecord], bool]

    def matches(self, record: RequestRecord) -> bool:
        try:
            return self.predicate(record)
        except Exception:
            return False


@dataclass
class Tagger:
    """Applies a collection of TagRules to records, returning tagged copies."""

    rules: List[TagRule] = field(default_factory=list)

    def add_rule(self, tag: str, predicate: Callable[[RequestRecord], bool]) -> None:
        """Register a new tagging rule."""
        self.rules.append(TagRule(tag=tag, predicate=predicate))

    def tag_record(self, record: RequestRecord) -> List[str]:
        """Return the list of tags that apply to *record*."""
        return [rule.tag for rule in self.rules if rule.matches(record)]

    def tag_all(self, records: List[RequestRecord]) -> dict[str, List[str]]:
        """Return a mapping of record id -> list of matching tags."""
        return {record.id: self.tag_record(record) for record in records}


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

def make_default_tagger() -> Tagger:
    """Return a Tagger pre-loaded with sensible default rules."""
    tagger = Tagger()
    tagger.add_rule("slow", lambda r: r.duration_ms is not None and r.duration_ms > 1000)
    tagger.add_rule("error", lambda r: r.status_code is not None and r.status_code >= 500)
    tagger.add_rule("client-error", lambda r: r.status_code is not None and 400 <= r.status_code < 500)
    tagger.add_rule("post", lambda r: r.method.upper() == "POST")
    tagger.add_rule("get", lambda r: r.method.upper() == "GET")
    tagger.add_rule("large-body", lambda r: len(r.request_body or "") > 4096)
    return tagger
