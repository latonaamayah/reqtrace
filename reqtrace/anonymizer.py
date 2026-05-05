"""Anonymizer for sensitive fields in request records."""

import re
from typing import Dict, List, Optional
from reqtrace.storage import RequestRecord


DEFAULT_SENSITIVE_HEADERS = [
    "authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "x-auth-token",
]

DEFAULT_SENSITIVE_BODY_PATTERNS = [
    r'"password"\s*:\s*"[^"]*"',
    r'"token"\s*:\s*"[^"]*"',
    r'"secret"\s*:\s*"[^"]*"',
    r'"api_key"\s*:\s*"[^"]*"',
]

REDACTED = "[REDACTED]"


class Anonymizer:
    """Redacts sensitive data from RequestRecord instances."""

    def __init__(
        self,
        sensitive_headers: Optional[List[str]] = None,
        sensitive_body_patterns: Optional[List[str]] = None,
    ):
        self.sensitive_headers = [
            h.lower() for h in (sensitive_headers or DEFAULT_SENSITIVE_HEADERS)
        ]
        self.body_patterns = [
            re.compile(p, re.IGNORECASE)
            for p in (sensitive_body_patterns or DEFAULT_SENSITIVE_BODY_PATTERNS)
        ]

    def anonymize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Return a copy of headers with sensitive values redacted."""
        result = {}
        for key, value in headers.items():
            if key.lower() in self.sensitive_headers:
                result[key] = REDACTED
            else:
                result[key] = value
        return result

    def anonymize_body(self, body: Optional[str]) -> Optional[str]:
        """Return body with sensitive field values redacted."""
        if not body:
            return body
        result = body
        for pattern in self.body_patterns:
            # Replace the value portion with REDACTED, preserving the key
            result = pattern.sub(
                lambda m: re.sub(r'(:\s*)"[^"]*"', r'\1"' + REDACTED + '"', m.group()),
                result,
            )
        return result

    def anonymize(self, record: RequestRecord) -> RequestRecord:
        """Return a new RequestRecord with sensitive data redacted."""
        return RequestRecord(
            id=record.id,
            timestamp=record.timestamp,
            method=record.method,
            path=record.path,
            query_string=record.query_string,
            request_headers=self.anonymize_headers(record.request_headers),
            request_body=self.anonymize_body(record.request_body),
            response_status=record.response_status,
            response_headers=self.anonymize_headers(record.response_headers),
            response_body=record.response_body,
            duration_ms=record.duration_ms,
        )
