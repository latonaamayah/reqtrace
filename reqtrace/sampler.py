"""Sampling support for reqtrace: keep only a fraction of captured records."""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from reqtrace.storage import RequestRecord


@dataclass
class SamplerConfig:
    """Configuration for the Sampler."""

    rate: float = 1.0  # 0.0 – 1.0; fraction of records to keep
    seed: Optional[int] = None  # for deterministic sampling
    # Optional extra predicate: record is kept only when both rate AND predicate pass
    predicate: Optional[Callable[[RequestRecord], bool]] = field(
        default=None, repr=False
    )

    def __post_init__(self) -> None:
        if not (0.0 <= self.rate <= 1.0):
            raise ValueError(f"rate must be between 0.0 and 1.0, got {self.rate}")


class Sampler:
    """Decides whether individual records should be retained."""

    def __init__(self, config: Optional[SamplerConfig] = None) -> None:
        self._config = config or SamplerConfig()
        self._rng = random.Random(self._config.seed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def should_keep(self, record: RequestRecord) -> bool:
        """Return True if *record* should be retained according to the sampling policy."""
        if self._config.rate == 0.0:
            return False
        if self._config.rate == 1.0:
            pass  # fall through to predicate check
        else:
            # Deterministic per-record hash so the same record always gives the
            # same decision regardless of insertion order.
            digest = int(
                hashlib.md5(record.request_id.encode(), usedforsecurity=False).hexdigest(),
                16,
            )
            bucket = (digest % 10_000) / 10_000.0
            if bucket >= self._config.rate:
                return False

        if self._config.predicate is not None:
            try:
                return bool(self._config.predicate(record))
            except Exception:
                return False
        return True

    def apply(self, records: List[RequestRecord]) -> List[RequestRecord]:
        """Filter *records*, returning only those that pass sampling."""
        return [r for r in records if self.should_keep(r)]
