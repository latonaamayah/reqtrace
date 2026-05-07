"""Truncate large request/response bodies in stored records."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from reqtrace.storage import RequestRecord

_DEFAULT_MAX_BYTES = 4096
_TRUNCATION_MARKER = "...[truncated]"


@dataclass
class TruncationResult:
    original_count: int
    truncated_count: int
    records: List[RequestRecord]

    @property
    def unchanged_count(self) -> int:
        return self.original_count - self.truncated_count

    def __str__(self) -> str:
        return (
            f"Truncated {self.truncated_count}/{self.original_count} records "
            f"(max body size: unchanged {self.unchanged_count})"
        )


def _truncate_body(body: str, max_bytes: int) -> tuple[str, bool]:
    """Return (possibly truncated body, was_truncated)."""
    if len(body.encode("utf-8", errors="replace")) <= max_bytes:
        return body, False
    truncated = body.encode("utf-8", errors="replace")[:max_bytes].decode(
        "utf-8", errors="replace"
    )
    return truncated + _TRUNCATION_MARKER, True


def truncate_record(
    record: RequestRecord, max_bytes: int = _DEFAULT_MAX_BYTES
) -> tuple[RequestRecord, bool]:
    """Return a new RequestRecord with body fields truncated if needed."""
    changed = False
    new_req_body = record.request_body
    new_resp_body = record.response_body

    if record.request_body:
        new_req_body, req_changed = _truncate_body(record.request_body, max_bytes)
        changed = changed or req_changed

    if record.response_body:
        new_resp_body, resp_changed = _truncate_body(record.response_body, max_bytes)
        changed = changed or resp_changed

    if not changed:
        return record, False

    updated = RequestRecord(
        record_id=record.record_id,
        timestamp=record.timestamp,
        method=record.method,
        path=record.path,
        query_string=record.query_string,
        request_headers=record.request_headers,
        request_body=new_req_body,
        status_code=record.status_code,
        response_headers=record.response_headers,
        response_body=new_resp_body,
        duration_ms=record.duration_ms,
    )
    return updated, True


def truncate_all(
    records: List[RequestRecord], max_bytes: int = _DEFAULT_MAX_BYTES
) -> TruncationResult:
    """Truncate bodies across a list of records and return a TruncationResult."""
    result_records = []
    truncated_count = 0
    for record in records:
        new_record, was_truncated = truncate_record(record, max_bytes)
        result_records.append(new_record)
        if was_truncated:
            truncated_count += 1
    return TruncationResult(
        original_count=len(records),
        truncated_count=truncated_count,
        records=result_records,
    )
