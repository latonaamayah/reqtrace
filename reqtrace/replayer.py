"""Replays recorded HTTP requests against a target base URL."""

import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Optional

from reqtrace.storage import LogStorage, RequestRecord


@dataclass
class ReplayResult:
    record: RequestRecord
    response_status: int
    response_body: str
    matched: bool  # True if status code matches original
    error: Optional[str] = None


class Replayer:
    """Replays stored requests against a given base URL and compares responses."""

    def __init__(self, storage: LogStorage, base_url: str):
        self.storage = storage
        self.base_url = base_url.rstrip("/")

    def replay_all(self) -> list[ReplayResult]:
        records = self.storage.load_all()
        return [self.replay(record) for record in records]

    def replay(self, record: RequestRecord) -> ReplayResult:
        url = self.base_url + record.url
        body = record.request_body.encode("utf-8") if record.request_body else None
        headers = {
            k: v for k, v in record.request_headers.items()
            if k.lower() not in ("host", "content-length")
        }

        req = urllib.request.Request(
            url=url,
            data=body,
            headers=headers,
            method=record.method,
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                response_body = resp.read().decode("utf-8", errors="replace")
                status = resp.status
        except urllib.error.HTTPError as e:
            response_body = e.read().decode("utf-8", errors="replace")
            status = e.code
        except Exception as exc:
            return ReplayResult(
                record=record,
                response_status=0,
                response_body="",
                matched=False,
                error=str(exc),
            )

        return ReplayResult(
            record=record,
            response_status=status,
            response_body=response_body,
            matched=(status == record.response_status),
        )
