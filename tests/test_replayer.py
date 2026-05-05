"""Tests for the Replayer using a mock HTTP server."""

import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone

import pytest

from reqtrace.replayer import Replayer
from reqtrace.storage import LogStorage, RequestRecord


class EchoHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def do_POST(self):
        self.send_response(201)
        self.end_headers()
        self.wfile.write(b"created")

    def log_message(self, *args):
        pass  # suppress server output in tests


@pytest.fixture(scope="module")
def mock_server():
    server = HTTPServer(("127.0.0.1", 0), EchoHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


def make_record(method="GET", url="/ping", status=200):
    return RequestRecord(
        request_id="abc-123",
        timestamp=datetime.now(timezone.utc).isoformat(),
        method=method,
        url=url,
        request_headers={"Accept": "application/json"},
        request_body="",
        response_status=status,
        response_headers={},
        response_body="ok",
        duration_ms=10.0,
        service="test",
    )


@pytest.fixture
def tmp_storage(tmp_path):
    return LogStorage(str(tmp_path / "replay_log.jsonl"))


def test_replay_matched(mock_server, tmp_storage):
    record = make_record(method="GET", url="/anything", status=200)
    tmp_storage.save(record)
    replayer = Replayer(tmp_storage, mock_server)
    results = replayer.replay_all()
    assert len(results) == 1
    assert results[0].response_status == 200
    assert results[0].matched is True


def test_replay_unmatched_status(mock_server, tmp_storage):
    record = make_record(method="GET", url="/anything", status=404)
    tmp_storage.save(record)
    replayer = Replayer(tmp_storage, mock_server)
    results = replayer.replay_all()
    assert results[0].matched is False


def test_replay_connection_error(tmp_storage):
    record = make_record(method="GET", url="/test", status=200)
    tmp_storage.save(record)
    replayer = Replayer(tmp_storage, "http://127.0.0.1:1")
    results = replayer.replay_all()
    assert results[0].error is not None
    assert results[0].matched is False
