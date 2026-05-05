"""Tests for ReqTraceMiddleware."""

import json
import pytest
from io import BytesIO

from reqtrace.middleware import ReqTraceMiddleware
from reqtrace.storage import LogStorage


@pytest.fixture
def tmp_storage(tmp_path):
    return LogStorage(str(tmp_path / "test_log.jsonl"))


def make_wsgi_environ(method="GET", path="/api/test", query="", body=b"", headers=None):
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
        "wsgi.input": BytesIO(body),
        "CONTENT_LENGTH": str(len(body)),
        "HTTP_ACCEPT": "application/json",
    }
    if headers:
        for k, v in headers.items():
            environ[f"HTTP_{k.upper().replace('-', '_')}"] = v
    return environ


def simple_app(environ, start_response):
    start_response("200 OK", [("Content-Type", "application/json")])
    return [b'{"ok": true}']


def test_middleware_logs_request(tmp_storage):
    middleware = ReqTraceMiddleware(simple_app, tmp_storage, service_name="test-svc")
    environ = make_wsgi_environ(method="GET", path="/api/items")
    responses = list(middleware(environ, lambda s, h, *a: None))
    assert b'{"ok": true}' in responses

    records = tmp_storage.load_all()
    assert len(records) == 1
    record = records[0]
    assert record.method == "GET"
    assert record.url == "/api/items"
    assert record.response_status == 200
    assert record.service == "test-svc"
    assert record.duration_ms >= 0


def test_middleware_logs_post_body(tmp_storage):
    middleware = ReqTraceMiddleware(simple_app, tmp_storage)
    body = b'{"name": "widget"}'
    environ = make_wsgi_environ(method="POST", path="/api/items", body=body)
    environ["CONTENT_TYPE"] = "application/json"
    list(middleware(environ, lambda s, h, *a: None))

    records = tmp_storage.load_all()
    assert records[0].request_body == '{"name": "widget"}'
    assert records[0].method == "POST"


def test_middleware_with_query_string(tmp_storage):
    middleware = ReqTraceMiddleware(simple_app, tmp_storage)
    environ = make_wsgi_environ(path="/search", query="q=hello&page=2")
    list(middleware(environ, lambda s, h, *a: None))

    records = tmp_storage.load_all()
    assert records[0].url == "/search?q=hello&page=2"


def test_middleware_response_body_captured(tmp_storage):
    middleware = ReqTraceMiddleware(simple_app, tmp_storage)
    environ = make_wsgi_environ()
    list(middleware(environ, lambda s, h, *a: None))

    records = tmp_storage.load_all()
    assert '{"ok": true}' in records[0].response_body
