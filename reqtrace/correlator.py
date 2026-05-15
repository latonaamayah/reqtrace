"""correlator.py — Groups related HTTP request records into correlation chains.

A correlation chain links requests that share a common trace/correlation ID
found in request headers (e.g. X-Correlation-ID, X-Request-ID, X-Trace-ID).
Records without any correlation header are placed in an "uncorrelated" bucket.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from reqtrace.storage import RequestRecord

# Headers inspected (in priority order) when extracting a correlation ID.
_CORRELATION_HEADERS = (
    "x-correlation-id",
    "x-request-id",
    "x-trace-id",
    "traceparent",  # W3C Trace Context
)

_UNCORRELATED_KEY = "__uncorrelated__"


def _extract_correlation_id(record: RequestRecord) -> Optional[str]:
    """Return the first correlation-style header value found in the record's
    request headers, or *None* if none is present."""
    headers = {k.lower(): v for k, v in record.request_headers.items()}
    for header in _CORRELATION_HEADERS:
        value = headers.get(header)
        if value:
            return value
    return None


@dataclass
class CorrelationChain:
    """A group of records that share the same correlation ID."""

    correlation_id: str
    records: List[RequestRecord] = field(default_factory=list)

    @property
    def is_uncorrelated(self) -> bool:
        """True when this chain holds records with no correlation header."""
        return self.correlation_id == _UNCORRELATED_KEY

    def __len__(self) -> int:  # pragma: no cover
        return len(self.records)

    def __str__(self) -> str:  # pragma: no cover
        label = "(uncorrelated)" if self.is_uncorrelated else self.correlation_id
        return f"CorrelationChain({label}, {len(self.records)} records)"


@dataclass
class CorrelationResult:
    """Result returned by :func:`correlate`."""

    chains: Dict[str, CorrelationChain] = field(default_factory=dict)

    @property
    def total_chains(self) -> int:
        """Number of distinct correlation IDs (including the uncorrelated bucket)."""
        return len(self.chains)

    @property
    def correlated_count(self) -> int:
        """Number of records that carried a correlation header."""
        return sum(
            len(c.records)
            for key, c in self.chains.items()
            if key != _UNCORRELATED_KEY
        )

    @property
    def uncorrelated_count(self) -> int:
        """Number of records without any correlation header."""
        bucket = self.chains.get(_UNCORRELATED_KEY)
        return len(bucket.records) if bucket else 0

    def __str__(self) -> str:  # pragma: no cover
        lines = [
            f"CorrelationResult: {self.total_chains} chain(s), "
            f"{self.correlated_count} correlated, "
            f"{self.uncorrelated_count} uncorrelated",
        ]
        for cid, chain in self.chains.items():
            label = "(uncorrelated)" if cid == _UNCORRELATED_KEY else cid
            lines.append(f"  [{label}] {len(chain.records)} record(s)")
        return "\n".join(lines)


def correlate(records: List[RequestRecord]) -> CorrelationResult:
    """Group *records* by correlation ID.

    Parameters
    ----------
    records:
        The list of :class:`~reqtrace.storage.RequestRecord` objects to group.

    Returns
    -------
    CorrelationResult
        A result object whose ``chains`` dict maps each correlation ID (or the
        special ``'__uncorrelated__'`` sentinel) to a
        :class:`CorrelationChain`.
    """
    result = CorrelationResult()

    for record in records:
        cid = _extract_correlation_id(record) or _UNCORRELATED_KEY
        if cid not in result.chains:
            result.chains[cid] = CorrelationChain(correlation_id=cid)
        result.chains[cid].records.append(record)

    return result
