"""Stream records from storage in configurable batches with optional filtering."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Generator, List, Optional

from reqtrace.storage import RequestRecord, LogStorage


@dataclass
class StreamConfig:
    batch_size: int = 10
    max_records: Optional[int] = None
    predicate: Optional[Callable[[RequestRecord], bool]] = None

    def __post_init__(self) -> None:
        if self.batch_size < 1:
            raise ValueError("batch_size must be >= 1")
        if self.max_records is not None and self.max_records < 0:
            raise ValueError("max_records must be >= 0")


@dataclass
class StreamResult:
    batches_yielded: int = 0
    total_records: int = 0
    filtered_out: int = 0

    def __str__(self) -> str:
        return (
            f"StreamResult(batches={self.batches_yielded}, "
            f"records={self.total_records}, filtered_out={self.filtered_out})"
        )


def stream_records(
    storage: LogStorage,
    config: StreamConfig,
) -> Generator[List[RequestRecord], None, StreamResult]:
    """Yield batches of records from storage, applying optional filtering.

    Returns a StreamResult via StopIteration value (use `result = yield from ...`).
    """
    all_records = storage.load_all()
    result = StreamResult()
    batch: List[RequestRecord] = []

    for record in all_records:
        if config.predicate is not None:
            try:
                keep = config.predicate(record)
            except Exception:
                keep = False
            if not keep:
                result.filtered_out += 1
                continue

        if config.max_records is not None and result.total_records >= config.max_records:
            break

        batch.append(record)
        result.total_records += 1

        if len(batch) >= config.batch_size:
            result.batches_yielded += 1
            yield batch
            batch = []

    if batch:
        result.batches_yielded += 1
        yield batch

    return result
