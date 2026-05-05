"""Tests for reqtrace.exporter module."""

import json
import csv
import io
from datetime import datetime
from reqtrace.storage import RequestRecord
from reqtrace.exporter import export_json, export_csv, export_curl


def make_record(method="GET", path="/test", body="", host="localhost"):
    return RequestRecord(
        id="abc-123",
        timestamp=datetime.utcnow().isoformat(),
        method=method,
        path=path,
        query_string="q=1",
        request_headers={"Host": host, "Content-Type": "application/json"},
        request_body=body,
        status_code=200,
        response_headers={"Content-Type": "application/json"},
        response_body='{"ok": true}',
        duration_ms=42.5,
    )


def test_export_json_valid():
    records = [make_record(), make_record(method="POST")]
    result = export_json(records)
    parsed = json.loads(result)
    assert len(parsed) == 2
    assert parsed[0]["method"] == "GET"
    assert parsed[1]["method"] == "POST"


def test_export_json_empty():
    result = export_json([])
    assert result == "[]"


def test_export_csv_headers():
    records = [make_record()]
    result = export_csv(records)
    reader = csv.DictReader(io.StringIO(result))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["method"] == "GET"
    assert rows[0]["path"] == "/test"
    assert rows[0]["status_code"] == "200"


def test_export_csv_multiple_rows():
    records = [make_record(path="/a"), make_record(path="/b")]
    result = export_csv(records)
    reader = csv.DictReader(io.StringIO(result))
    rows = list(reader)
    assert len(rows) == 2


def test_export_curl_get():
    record = make_record(method="GET", path="/api/items")
    result = export_curl([record])
    assert "curl -X GET" in result
    assert "/api/items" in result
    assert "-H 'Host: localhost'" in result


def test_export_curl_post_with_body():
    record = make_record(method="POST", path="/api/items", body='{"name": "test"}')
    result = export_curl([record])
    assert "-d '" in result
    assert "name" in result


def test_export_curl_multiple_records():
    records = [make_record(path="/a"), make_record(path="/b")]
    result = export_curl(records)
    assert result.count("curl -X") == 2
