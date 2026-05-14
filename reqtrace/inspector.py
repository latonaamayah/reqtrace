"""Inspect individual RequestRecords and produce a human-readable detail report."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import List, Optional

from reqtrace.storage import RequestRecord


@dataclass
class InspectionWarning:
    field: str
    message: str

    def __str__(self) -> str:
        return f"[{self.field}] {self.message}"


@dataclass
class InspectionResult:
    record_id: str
    warnings: List[InspectionWarning] = field(default_factory=list)

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    def format(self) -> str:
        lines = [f"Record : {self.record_id}"]
        if not self.has_warnings:
            lines.append("  No issues found.")
        else:
            for w in self.warnings:
                lines.append(f"  WARN  {w}")
        return "\n".join(lines)


def _is_json(text: Optional[str]) -> bool:
    if not text:
        return False
    try:
        json.loads(text)
        return True
    except (ValueError, TypeError):
        return False


def inspect_record(
    record: RequestRecord,
    slow_threshold_ms: float = 1000.0,
) -> InspectionResult:
    """Analyse a single record and return an InspectionResult with any warnings."""
    result = InspectionResult(record_id=record.record_id)

    # Slow response
    if record.duration_ms is not None and record.duration_ms > slow_threshold_ms:
        result.warnings.append(
            InspectionWarning("duration_ms", f"{record.duration_ms:.1f} ms exceeds threshold {slow_threshold_ms:.1f} ms")
        )

    # Server-side error
    if record.response_status is not None and record.response_status >= 500:
        result.warnings.append(
            InspectionWarning("response_status", f"Server error: HTTP {record.response_status}")
        )

    # Missing Content-Type on non-empty request body
    if record.request_body:
        ct = {k.lower(): v for k, v in (record.request_headers or {}).items()}.get("content-type", "")
        if not ct:
            result.warnings.append(
                InspectionWarning("request_headers", "Non-empty request body has no Content-Type header")
            )

    # Malformed JSON body when Content-Type claims JSON
    for label, body, headers in [
        ("request", record.request_body, record.request_headers or {}),
        ("response", record.response_body, record.response_headers or {}),
    ]:
        ct = {k.lower(): v for k, v in headers.items()}.get("content-type", "")
        if "application/json" in ct and body and not _is_json(body):
            result.warnings.append(
                InspectionWarning(f"{label}_body", "Content-Type is application/json but body is not valid JSON")
            )

    # Empty path
    if not record.path or record.path.strip() == "":
        result.warnings.append(InspectionWarning("path", "Request path is empty"))

    return result


def inspect_all(
    records: List[RequestRecord],
    slow_threshold_ms: float = 1000.0,
) -> List[InspectionResult]:
    return [inspect_record(r, slow_threshold_ms=slow_threshold_ms) for r in records]
