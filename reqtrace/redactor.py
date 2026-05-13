"""Redactor: mask or remove sensitive field values in request/response records."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from reqtrace.storage import RequestRecord

_MASK = "[REDACTED]"


@dataclass
class RedactRule:
    """Describes one redaction rule applied to a record field."""

    field: str  # 'request_headers', 'response_headers', 'request_body', 'response_body'
    pattern: str  # regex pattern to match within the field value
    replacement: str = _MASK
    predicate: Optional[Callable[[RequestRecord], bool]] = None

    def matches(self, record: RequestRecord) -> bool:
        if self.predicate is None:
            return True
        try:
            return bool(self.predicate(record))
        except Exception:
            return False


@dataclass
class RedactResult:
    total: int = 0
    redacted_count: int = 0
    records: List[RequestRecord] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"RedactResult(total={self.total}, redacted={self.redacted_count})"
        )


def _redact_headers(
    headers: Dict[str, str], pattern: str, replacement: str
) -> tuple[Dict[str, str], bool]:
    changed = False
    result: Dict[str, str] = {}
    for k, v in headers.items():
        new_v = re.sub(pattern, replacement, v, flags=re.IGNORECASE)
        if new_v != v:
            changed = True
        result[k] = new_v
    return result, changed


def _redact_body(
    body: Optional[str], pattern: str, replacement: str
) -> tuple[Optional[str], bool]:
    if body is None:
        return body, False
    new_body = re.sub(pattern, replacement, body, flags=re.IGNORECASE)
    return new_body, new_body != body


class Redactor:
    def __init__(self) -> None:
        self._rules: List[RedactRule] = []

    def add_rule(self, rule: RedactRule) -> None:
        self._rules.append(rule)

    def redact_record(self, record: RequestRecord) -> tuple[RequestRecord, bool]:
        """Apply all matching rules to a record. Returns (new_record, was_changed)."""
        changed = False
        req_headers = dict(record.request_headers)
        resp_headers = dict(record.response_headers)
        req_body = record.request_body
        resp_body = record.response_body

        for rule in self._rules:
            if not rule.matches(record):
                continue
            if rule.field == "request_headers":
                req_headers, c = _redact_headers(req_headers, rule.pattern, rule.replacement)
                changed = changed or c
            elif rule.field == "response_headers":
                resp_headers, c = _redact_headers(resp_headers, rule.pattern, rule.replacement)
                changed = changed or c
            elif rule.field == "request_body":
                req_body, c = _redact_body(req_body, rule.pattern, rule.replacement)
                changed = changed or c
            elif rule.field == "response_body":
                resp_body, c = _redact_body(resp_body, rule.pattern, rule.replacement)
                changed = changed or c

        new_record = RequestRecord(
            id=record.id,
            timestamp=record.timestamp,
            method=record.method,
            path=record.path,
            query_string=record.query_string,
            request_headers=req_headers,
            request_body=req_body,
            status_code=record.status_code,
            response_headers=resp_headers,
            response_body=resp_body,
            duration_ms=record.duration_ms,
        )
        return new_record, changed

    def redact_all(self, records: List[RequestRecord]) -> RedactResult:
        result = RedactResult(total=len(records))
        for record in records:
            new_record, changed = self.redact_record(record)
            result.records.append(new_record)
            if changed:
                result.redacted_count += 1
        return result
