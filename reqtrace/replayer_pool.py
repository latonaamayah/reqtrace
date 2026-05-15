"""Concurrent replay pool — replays multiple records in parallel."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from reqtrace.replayer import ReplayResult, Replayer
from reqtrace.storage import RequestRecord


@dataclass
class PoolConfig:
    max_workers: int = 4
    timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        if self.max_workers < 1:
            raise ValueError("max_workers must be >= 1")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")


@dataclass
class PoolResult:
    results: List[ReplayResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.results if r.status_code is not None)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    def __str__(self) -> str:
        return (
            f"PoolResult(total={len(self.results)}, "
            f"success={self.success_count}, errors={self.error_count})"
        )


def replay_pool(
    records: List[RequestRecord],
    base_url: str,
    config: Optional[PoolConfig] = None,
    on_result: Optional[Callable[[ReplayResult], None]] = None,
) -> PoolResult:
    """Replay *records* concurrently and return a :class:`PoolResult`."""
    if config is None:
        config = PoolConfig()

    pool_result = PoolResult()

    def _replay_one(record: RequestRecord) -> ReplayResult:
        replayer = Replayer(base_url=base_url, timeout=config.timeout_seconds)
        return replayer.replay(record)

    with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
        future_to_record = {executor.submit(_replay_one, rec): rec for rec in records}
        for future in as_completed(future_to_record):
            rec = future_to_record[future]
            try:
                result = future.result()
                pool_result.results.append(result)
                if on_result is not None:
                    on_result(result)
            except Exception as exc:  # noqa: BLE001
                pool_result.errors.append(
                    f"{rec.method} {rec.path} -> {type(exc).__name__}: {exc}"
                )

    return pool_result
