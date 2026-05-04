"""Storage module for persisting HTTP request/response logs."""

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class RequestRecord:
    """Represents a captured HTTP request/response pair."""

    id: str
    timestamp: float
    method: str
    url: str
    request_headers: Dict[str, str]
    request_body: Optional[str]
    response_status: int
    response_headers: Dict[str, str]
    response_body: Optional[str]
    duration_ms: float
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RequestRecord":
        return cls(**data)


class LogStorage:
    """File-based storage for request records."""

    def __init__(self, log_dir: str = ".reqtrace"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._log_file = self.log_dir / "requests.jsonl"

    def save(self, record: RequestRecord) -> None:
        """Append a request record to the log file."""
        with open(self._log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict()) + "\n")

    def load_all(self) -> List[RequestRecord]:
        """Load all request records from the log file."""
        if not self._log_file.exists():
            return []
        records = []
        with open(self._log_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if line:
                    try:
                        records.append(RequestRecord.from_dict(json.loads(line)))
                    except (json.JSONDecodeError, TypeError) as e:
                        raise ValueError(
                            f"Failed to parse record on line {line_num} of {self._log_file}: {e}"
                        ) from e
        return records

    def find_by_id(self, record_id: str) -> Optional[RequestRecord]:
        """Find a single record by its ID."""
        for record in self.load_all():
            if record.id == record_id:
                return record
        return None

    def clear(self) -> None:
        """Delete all stored records."""
        if self._log_file.exists():
            self._log_file.unlink()

    def count(self) -> int:
        """Return the total number of stored records."""
        return len(self.load_all())
