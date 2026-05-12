"""Snapshot: capture and restore a named point-in-time copy of a log storage."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from reqtrace.storage import LogStorage, RequestRecord, to_dict, from_dict


@dataclass
class SnapshotMeta:
    name: str
    created_at: str
    record_count: int

    def __str__(self) -> str:
        return f"{self.name}  ({self.record_count} records, {self.created_at})"


@dataclass
class SnapshotResult:
    name: str
    record_count: int
    path: str

    def __str__(self) -> str:
        return f"Snapshot '{self.name}' saved: {self.record_count} records -> {self.path}"


def _snapshot_path(snapshot_dir: str, name: str) -> Path:
    return Path(snapshot_dir) / f"{name}.snapshot.json"


def save_snapshot(storage: LogStorage, name: str, snapshot_dir: str) -> SnapshotResult:
    """Persist all records in *storage* as a named snapshot."""
    records = storage.load_all()
    os.makedirs(snapshot_dir, exist_ok=True)
    path = _snapshot_path(snapshot_dir, name)
    payload = {
        "name": name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "records": [to_dict(r) for r in records],
    }
    path.write_text(json.dumps(payload, indent=2))
    return SnapshotResult(name=name, record_count=len(records), path=str(path))


def load_snapshot(name: str, snapshot_dir: str) -> List[RequestRecord]:
    """Return records stored in the named snapshot."""
    path = _snapshot_path(snapshot_dir, name)
    if not path.exists():
        raise FileNotFoundError(f"Snapshot '{name}' not found at {path}")
    payload = json.loads(path.read_text())
    return [from_dict(r) for r in payload["records"]]


def list_snapshots(snapshot_dir: str) -> List[SnapshotMeta]:
    """Return metadata for every snapshot in *snapshot_dir*."""
    base = Path(snapshot_dir)
    if not base.exists():
        return []
    results: List[SnapshotMeta] = []
    for p in sorted(base.glob("*.snapshot.json")):
        try:
            payload = json.loads(p.read_text())
            results.append(
                SnapshotMeta(
                    name=payload["name"],
                    created_at=payload["created_at"],
                    record_count=len(payload["records"]),
                )
            )
        except Exception:
            pass
    return results


def delete_snapshot(name: str, snapshot_dir: str) -> bool:
    """Delete the named snapshot file. Returns True if deleted."""
    path = _snapshot_path(snapshot_dir, name)
    if path.exists():
        path.unlink()
        return True
    return False
