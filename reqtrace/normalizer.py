"""Normalize request records by cleaning up paths, headers, and bodies."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

from reqtrace.storage import RequestRecord


@dataclass
class NormalizeResult:
    total: int = 0
    changed: int = 0
    records: List[RequestRecord] = field(default_factory=list)

    @property
    def unchanged(self) -> int:
        return self.total - self.changed

    def __str__(self) -> str:
        return (
            f"Normalized {self.changed}/{self.total} records "
            f"({self.unchanged} unchanged)"
        )


def _normalize_path(path: str) -> str:
    """Collapse repeated slashes and strip trailing slash (except root)."""
    path = re.sub(r"/+", "/", path)
    if path != "/":
        path = path.rstrip("/")
    return path


def _normalize_headers(headers: dict) -> dict:
    """Lowercase all header names and strip whitespace from values."""
    return {k.lower().strip(): v.strip() for k, v in headers.items()}


def _normalize_body(body: str) -> str:
    """Strip leading/trailing whitespace from body."""
    return body.strip() if body else body


def normalize_record(record: RequestRecord) -> tuple[RequestRecord, bool]:
    """Return a normalized copy of *record* and whether it changed."""
    new_path = _normalize_path(record.path)
    new_req_headers = _normalize_headers(record.request_headers)
    new_resp_headers = _normalize_headers(record.response_headers)
    new_req_body = _normalize_body(record.request_body)
    new_resp_body = _normalize_body(record.response_body)

    changed = (
        new_path != record.path
        or new_req_headers != record.request_headers
        or new_resp_headers != record.response_headers
        or new_req_body != record.request_body
        or new_resp_body != record.response_body
    )

    normalized = RequestRecord(
        id=record.id,
        timestamp=record.timestamp,
        method=record.method.upper().strip(),
        path=new_path,
        request_headers=new_req_headers,
        request_body=new_req_body,
        status_code=record.status_code,
        response_headers=new_resp_headers,
        response_body=new_resp_body,
        duration_ms=record.duration_ms,
    )
    return normalized, changed


def normalize(records: List[RequestRecord]) -> NormalizeResult:
    """Normalize a list of records and return a NormalizeResult."""
    result = NormalizeResult(total=len(records))
    for record in records:
        normalized, changed = normalize_record(record)
        result.records.append(normalized)
        if changed:
            result.changed += 1
    return result
