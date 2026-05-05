"""Filtering utilities for request records."""

from typing import List, Optional
from reqtrace.storage import RequestRecord


class RecordFilter:
    """Filter request records by various criteria."""

    def __init__(
        self,
        method: Optional[str] = None,
        path_prefix: Optional[str] = None,
        status_code: Optional[int] = None,
        min_duration_ms: Optional[float] = None,
        max_duration_ms: Optional[float] = None,
        host: Optional[str] = None,
    ):
        self.method = method.upper() if method else None
        self.path_prefix = path_prefix
        self.status_code = status_code
        self.min_duration_ms = min_duration_ms
        self.max_duration_ms = max_duration_ms
        self.host = host

    def matches(self, record: RequestRecord) -> bool:
        """Return True if the record matches all specified criteria."""
        if self.method and record.method.upper() != self.method:
            return False

        if self.path_prefix and not record.path.startswith(self.path_prefix):
            return False

        if self.status_code is not None and record.status_code != self.status_code:
            return False

        duration = record.duration_ms
        if self.min_duration_ms is not None and (duration is None or duration < self.min_duration_ms):
            return False

        if self.max_duration_ms is not None and (duration is None or duration > self.max_duration_ms):
            return False

        if self.host:
            record_host = record.request_headers.get("Host", "")
            if record_host != self.host:
                return False

        return True

    def apply(self, records: List[RequestRecord]) -> List[RequestRecord]:
        """Return only records that match all criteria."""
        return [r for r in records if self.matches(r)]
