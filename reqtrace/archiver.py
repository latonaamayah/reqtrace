"""Archive and restore log storage snapshots to/from zip files."""

import io
import json
import zipfile
from pathlib import Path
from typing import List

from reqtrace.storage import LogStorage, RequestRecord


def archive(storage: LogStorage, dest: Path) -> int:
    """Write all records from *storage* into a zip archive at *dest*.

    Each record is stored as a separate JSON file named by its id.
    Returns the number of records archived.
    """
    records: List[RequestRecord] = storage.load_all()
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for record in records:
            data = json.dumps(record.to_dict(), indent=2)
            zf.writestr(f"{record.id}.json", data)
    return len(records)


def restore(src: Path, storage: LogStorage) -> int:
    """Load records from a zip archive at *src* into *storage*.

    Existing records in the storage are preserved; duplicates (same id)
    are skipped.  Returns the number of records actually written.
    """
    existing_ids = {r.id for r in storage.load_all()}
    written = 0
    with zipfile.ZipFile(src, "r") as zf:
        for name in zf.namelist():
            if not name.endswith(".json"):
                continue
            raw = zf.read(name)
            data = json.loads(raw)
            record = RequestRecord.from_dict(data)
            if record.id in existing_ids:
                continue
            storage.save(record)
            existing_ids.add(record.id)
            written += 1
    return written


def list_archive(src: Path) -> List[str]:
    """Return a list of record ids contained in the archive."""
    with zipfile.ZipFile(src, "r") as zf:
        return [
            name[: -len(".json")]
            for name in zf.namelist()
            if name.endswith(".json")
        ]
