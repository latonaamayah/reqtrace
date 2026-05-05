"""Export request records to different formats."""

import csv
import json
import io
from typing import List
from reqtrace.storage import RequestRecord, to_dict


def export_json(records: List[RequestRecord], indent: int = 2) -> str:
    """Serialize records to a JSON string."""
    return json.dumps([to_dict(r) for r in records], indent=indent, default=str)


def export_csv(records: List[RequestRecord]) -> str:
    """Serialize records to CSV with common fields as columns."""
    fieldnames = [
        "id",
        "timestamp",
        "method",
        "path",
        "query_string",
        "status_code",
        "duration_ms",
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()

    for record in records:
        row = {
            "id": record.id,
            "timestamp": record.timestamp,
            "method": record.method,
            "path": record.path,
            "query_string": record.query_string,
            "status_code": record.status_code,
            "duration_ms": record.duration_ms,
        }
        writer.writerow(row)

    return output.getvalue()


def export_curl(records: List[RequestRecord]) -> str:
    """Generate curl command equivalents for each record."""
    lines = []
    for record in records:
        parts = [f"curl -X {record.method}"]

        for key, value in record.request_headers.items():
            parts.append(f"  -H '{key}: {value}'")

        host = record.request_headers.get("Host", "localhost")
        url = f"http://{host}{record.path}"
        if record.query_string:
            url += f"?{record.query_string}"

        if record.request_body:
            body = record.request_body.replace("'", "'\\''")
            parts.append(f"  -d '{body}'")

        parts.append(f"  '{url}'")
        lines.append(" \\
".join(parts))

    return "\n\n".join(lines)
