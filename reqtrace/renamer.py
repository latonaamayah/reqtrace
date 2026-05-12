"""Rename (relabel) request records by rewriting path prefixes or method values."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from reqtrace.storage import RequestRecord


@dataclass
class RenameRule:
    """A single rewrite rule applied to a RequestRecord."""
    description: str
    predicate: Callable[[RequestRecord], bool]
    rewrite: Callable[[RequestRecord], RequestRecord]

    def matches(self, record: RequestRecord) -> bool:
        try:
            return self.predicate(record)
        except Exception:
            return False


@dataclass
class RenameResult:
    renamed: List[RequestRecord] = field(default_factory=list)
    unchanged: List[RequestRecord] = field(default_factory=list)

    @property
    def renamed_count(self) -> int:
        return len(self.renamed)

    @property
    def unchanged_count(self) -> int:
        return len(self.unchanged)

    @property
    def all_records(self) -> List[RequestRecord]:
        return self.renamed + self.unchanged

    def __str__(self) -> str:
        return (
            f"RenameResult: {self.renamed_count} renamed, "
            f"{self.unchanged_count} unchanged"
        )


class Renamer:
    def __init__(self) -> None:
        self._rules: List[RenameRule] = []

    def add_rule(self, rule: RenameRule) -> None:
        self._rules.append(rule)

    def rename_record(self, record: RequestRecord) -> tuple[RequestRecord, bool]:
        """Apply the first matching rule. Returns (record, was_renamed)."""
        for rule in self._rules:
            if rule.matches(record):
                return rule.rewrite(record), True
        return record, False

    def rename_all(self, records: List[RequestRecord]) -> RenameResult:
        result = RenameResult()
        for record in records:
            rewritten, changed = self.rename_record(record)
            if changed:
                result.renamed.append(rewritten)
            else:
                result.unchanged.append(rewritten)
        return result


def replace_path_prefix(
    old_prefix: str,
    new_prefix: str,
    description: Optional[str] = None,
) -> RenameRule:
    """Convenience factory: rewrite path prefix old_prefix -> new_prefix."""
    desc = description or f"replace path prefix '{old_prefix}' -> '{new_prefix}'"

    def _pred(r: RequestRecord) -> bool:
        return r.path.startswith(old_prefix)

    def _rewrite(r: RequestRecord) -> RequestRecord:
        new_path = new_prefix + r.path[len(old_prefix):]
        return RequestRecord(
            id=r.id,
            timestamp=r.timestamp,
            method=r.method,
            path=new_path,
            request_headers=r.request_headers,
            request_body=r.request_body,
            status_code=r.status_code,
            response_headers=r.response_headers,
            response_body=r.response_body,
            duration_ms=r.duration_ms,
        )

    return RenameRule(description=desc, predicate=_pred, rewrite=_rewrite)
