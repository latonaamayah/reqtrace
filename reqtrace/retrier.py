"""Retry logic for replaying failed HTTP requests with configurable backoff."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from reqtrace.replayer import ReplayResult, Replayer
from reqtrace.storage import RequestRecord


@dataclass
class RetryConfig:
    max_attempts: int = 3
    backoff_base: float = 0.5  # seconds
    backoff_multiplier: float = 2.0
    retry_on_status: List[int] = field(default_factory=lambda: [500, 502, 503, 504])
    retry_on_exception: bool = True


@dataclass
class RetryOutcome:
    record: RequestRecord
    attempts: int
    results: List[ReplayResult]
    succeeded: bool

    @property
    def final_result(self) -> Optional[ReplayResult]:
        return self.results[-1] if self.results else None

    def __str__(self) -> str:
        status = "OK" if self.succeeded else "FAILED"
        return (
            f"RetryOutcome({status}, attempts={self.attempts}, "
            f"final_status={self.final_result.status_code if self.final_result else 'N/A'})"
        )


class Retrier:
    def __init__(
        self,
        replayer: Replayer,
        config: Optional[RetryConfig] = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self._replayer = replayer
        self._config = config or RetryConfig()
        self._sleep = sleep_fn

    def retry(self, record: RequestRecord) -> RetryOutcome:
        cfg = self._config
        results: List[ReplayResult] = []
        delay = cfg.backoff_base

        for attempt in range(1, cfg.max_attempts + 1):
            result = self._replayer.replay(record)
            results.append(result)

            if result.error is None and result.status_code not in cfg.retry_on_status:
                return RetryOutcome(record, attempt, results, succeeded=True)

            if result.error is not None and not cfg.retry_on_exception:
                break

            if attempt < cfg.max_attempts:
                self._sleep(delay)
                delay *= cfg.backoff_multiplier

        final = results[-1]
        succeeded = final.error is None and final.status_code not in cfg.retry_on_status
        return RetryOutcome(record, len(results), results, succeeded=succeeded)

    def retry_all(self, records: List[RequestRecord]) -> List[RetryOutcome]:
        return [self.retry(r) for r in records]
