"""Patch fields on stored request records in bulk."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from .storage import RequestRecord, LogStorage


@dataclass
class PatchRule:
    """A single field-patch rule."""
    field_name: str
    transform: Callable[[object], object]
    predicate: Optional[Callable[[RequestRecord], bool]] = None

    def matches(self, record: RequestRecord) -> bool:
        if self.predicate is None:
            return True
        try:
            return bool(self.predicate(record))
        except Exception:
            return False


@dataclass
class PatchResult:
    patched_count: int = 0
    skipped_count: int = 0
    errors: List[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.patched_count + self.skipped_count

    def __str__(self) -> str:
        return (
            f"PatchResult(patched={self.patched_count}, "
            f"skipped={self.skipped_count}, errors={len(self.errors)})"
        )


class Patcher:
    def __init__(self) -> None:
        self._rules: List[PatchRule] = []

    def add_rule(self, rule: PatchRule) -> None:
        self._rules.append(rule)

    def patch_record(self, record: RequestRecord) -> RequestRecord:
        """Apply all matching rules to a record, returning a new record dict."""
        data = record.to_dict()
        for rule in self._rules:
            if rule.matches(record):
                if rule.field_name in data:
                    data[rule.field_name] = rule.transform(data[rule.field_name])
        return RequestRecord.from_dict(data)

    def apply(self, records: List[RequestRecord]) -> tuple[List[RequestRecord], PatchResult]:
        result = PatchResult()
        patched: List[RequestRecord] = []
        for record in records:
            try:
                new_record = self.patch_record(record)
                patched.append(new_record)
                if new_record.to_dict() != record.to_dict():
                    result.patched_count += 1
                else:
                    result.skipped_count += 1
            except Exception as exc:
                result.errors.append(str(exc))
                patched.append(record)
                result.skipped_count += 1
        return patched, result


def patch_storage(storage: LogStorage, patcher: Patcher) -> PatchResult:
    """Load all records from storage, patch them, and save back."""
    records = storage.load_all()
    patched_records, result = patcher.apply(records)
    for record in patched_records:
        storage.save(record)
    return result
