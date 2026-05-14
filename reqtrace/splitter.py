"""Split a log storage into multiple storages based on a field or predicate."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from reqtrace.storage import LogStorage, RequestRecord


@dataclass
class SplitResult:
    buckets: Dict[str, List[RequestRecord]] = field(default_factory=dict)
    total: int = 0
    unmatched: int = 0

    def __str__(self) -> str:
        lines = [f"Split result: {self.total} records across {len(self.buckets)} buckets"]
        for key, records in sorted(self.buckets.items()):
            lines.append(f"  {key}: {len(records)} record(s)")
        if self.unmatched:
            lines.append(f"  (unmatched): {self.unmatched} record(s)")
        return "\n".join(lines)


SplitKey = Callable[[RequestRecord], Optional[str]]


def _by_method(record: RequestRecord) -> str:
    return record.method.upper()


def _by_status_class(record: RequestRecord) -> str:
    if record.status_code is None:
        return "unknown"
    return f"{record.status_code // 100}xx"


def _by_path_prefix(depth: int = 1) -> SplitKey:
    def _key(record: RequestRecord) -> str:
        parts = record.path.strip("/").split("/")
        prefix = "/" + "/".join(parts[:depth])
        return prefix or "/"
    return _key


def split(
    storage: LogStorage,
    key_fn: SplitKey,
    *,
    output_dir: Optional[str] = None,
    persist: bool = False,
) -> SplitResult:
    """Split records from *storage* into buckets determined by *key_fn*.

    If *persist* is True, each bucket is written to a separate
    :class:`LogStorage` under *output_dir*.
    """
    records = storage.load_all()
    result = SplitResult(total=len(records))

    for record in records:
        try:
            bucket_key = key_fn(record)
        except Exception:
            bucket_key = None

        if bucket_key is None:
            result.unmatched += 1
            continue

        result.buckets.setdefault(bucket_key, []).append(record)

    if persist and output_dir is not None:
        import os
        os.makedirs(output_dir, exist_ok=True)
        for bucket_key, bucket_records in result.buckets.items():
            safe_name = bucket_key.replace("/", "_").strip("_") or "root"
            bucket_path = os.path.join(output_dir, f"{safe_name}.jsonl")
            bucket_storage = LogStorage(bucket_path)
            for rec in bucket_records:
                bucket_storage.save(rec)

    return result
