"""Score HTTP records by anomaly indicators for debugging triage."""

from dataclasses import dataclass, field
from typing import List
from reqtrace.storage import RequestRecord


@dataclass
class ScoreResult:
    record: RequestRecord
    score: int
    reasons: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        tag = "HIGH" if self.score >= 10 else "MED" if self.score >= 5 else "LOW"
        lines = [f"[{tag}] score={self.score} {self.record.method} {self.record.path}"]
        for r in self.reasons:
            lines.append(f"  - {r}")
        return "\n".join(lines)


SERVER_ERROR_THRESHOLD = 500
CLIENT_ERROR_THRESHOLD = 400
SLOW_REQUEST_MS = 1000
VERY_SLOW_REQUEST_MS = 3000


def score_record(record: RequestRecord) -> ScoreResult:
    """Assign an anomaly score to a single RequestRecord."""
    points = 0
    reasons: List[str] = []

    status = record.response_status
    if status >= SERVER_ERROR_THRESHOLD:
        points += 10
        reasons.append(f"Server error status {status}")
    elif status >= CLIENT_ERROR_THRESHOLD:
        points += 4
        reasons.append(f"Client error status {status}")

    duration = record.duration_ms
    if duration >= VERY_SLOW_REQUEST_MS:
        points += 6
        reasons.append(f"Very slow response {duration}ms (>={VERY_SLOW_REQUEST_MS}ms)")
    elif duration >= SLOW_REQUEST_MS:
        points += 3
        reasons.append(f"Slow response {duration}ms (>={SLOW_REQUEST_MS}ms)")

    if record.method == "DELETE":
        points += 1
        reasons.append("Destructive method DELETE")

    body = record.request_body or ""
    if len(body) > 10_000:
        points += 2
        reasons.append(f"Large request body ({len(body)} bytes)")

    return ScoreResult(record=record, score=points, reasons=reasons)


def score_all(records: List[RequestRecord], min_score: int = 0) -> List[ScoreResult]:
    """Score all records and return sorted by score descending."""
    results = [score_record(r) for r in records]
    results = [r for r in results if r.score >= min_score]
    results.sort(key=lambda r: r.score, reverse=True)
    return results
