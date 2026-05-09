"""Validate recorded requests/responses against simple schema rules."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from reqtrace.storage import RequestRecord


@dataclass
class ValidationError:
    record_id: str
    rule_name: str
    message: str

    def __str__(self) -> str:
        return f"[{self.record_id}] {self.rule_name}: {self.message}"


@dataclass
class ValidationResult:
    errors: List[ValidationError] = field(default_factory=list)

    @property
    def valid_count(self) -> int:
        ids = {e.record_id for e in self.errors}
        return self._total - len(ids)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    def __str__(self) -> str:
        if not self.errors:
            return f"All {self._total} record(s) passed validation."
        lines = [f"{self.error_count} validation error(s) across {self._total} record(s):"]
        for e in self.errors:
            lines.append(f"  {e}")
        return "\n".join(lines)

    # set by validate()
    _total: int = field(default=0, repr=False)


PredicateFn = Callable[[RequestRecord], bool]


@dataclass
class ValidationRule:
    name: str
    predicate: PredicateFn
    message: str

    def check(self, record: RequestRecord) -> Optional[ValidationError]:
        try:
            ok = self.predicate(record)
        except Exception:
            ok = False
        if not ok:
            return ValidationError(
                record_id=record.record_id,
                rule_name=self.name,
                message=self.message,
            )
        return None


class Validator:
    def __init__(self) -> None:
        self._rules: List[ValidationRule] = []

    def add_rule(self, rule: ValidationRule) -> None:
        self._rules.append(rule)

    def validate(self, records: List[RequestRecord]) -> ValidationResult:
        result = ValidationResult()
        result._total = len(records)
        for record in records:
            for rule in self._rules:
                err = rule.check(record)
                if err:
                    result.errors.append(err)
        return result


# Built-in rules
def require_status_below_500() -> ValidationRule:
    return ValidationRule(
        name="no_server_error",
        predicate=lambda r: r.status_code < 500,
        message="Response status code is 5xx (server error).",
    )


def require_non_empty_path() -> ValidationRule:
    return ValidationRule(
        name="non_empty_path",
        predicate=lambda r: bool(r.path.strip()),
        message="Request path is empty.",
    )


def require_duration_below(max_ms: float) -> ValidationRule:
    return ValidationRule(
        name=f"duration_below_{int(max_ms)}ms",
        predicate=lambda r: r.duration_ms <= max_ms,
        message=f"Request duration exceeds {max_ms} ms.",
    )
