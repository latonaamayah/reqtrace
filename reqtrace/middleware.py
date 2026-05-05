"""WSGI/ASGI-compatible middleware for capturing HTTP requests and responses."""

import time
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional

from reqtrace.storage import LogStorage, RequestRecord


class ReqTraceMiddleware:
    """Middleware that intercepts HTTP requests and logs them via LogStorage."""

    def __init__(self, app: Callable, storage: LogStorage, service_name: str = "unknown"):
        self.app = app
        self.storage = storage
        self.service_name = service_name

    def __call__(self, environ: dict, start_response: Callable):
        request_id = str(uuid.uuid4())
        method = environ.get("REQUEST_METHOD", "GET")
        path = environ.get("PATH_INFO", "/")
        query = environ.get("QUERY_STRING", "")
        full_path = f"{path}?{query}" if query else path

        request_headers = self._extract_headers(environ)
        request_body = self._read_body(environ)

        response_status_holder = []
        response_headers_holder = []

        def capturing_start_response(status, headers, exc_info=None):
            response_status_holder.append(status)
            response_headers_holder.extend(headers)
            return start_response(status, headers, exc_info)

        started_at = time.monotonic()
        response_chunks = self.app(environ, capturing_start_response)
        response_body = b"".join(response_chunks)
        duration_ms = round((time.monotonic() - started_at) * 1000, 2)

        status_code = int(response_status_holder[0].split(" ")[0]) if response_status_holder else 0
        resp_headers = dict(response_headers_holder)

        record = RequestRecord(
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            method=method,
            url=full_path,
            request_headers=request_headers,
            request_body=request_body.decode("utf-8", errors="replace"),
            response_status=status_code,
            response_headers=resp_headers,
            response_body=response_body.decode("utf-8", errors="replace"),
            duration_ms=duration_ms,
            service=self.service_name,
        )
        self.storage.save(record)

        yield response_body

    def _extract_headers(self, environ: dict) -> dict:
        headers = {}
        for key, value in environ.items():
            if key.startswith("HTTP_"):
                header_name = key[5:].replace("_", "-").title()
                headers[header_name] = value
        if "CONTENT_TYPE" in environ:
            headers["Content-Type"] = environ["CONTENT_TYPE"]
        if "CONTENT_LENGTH" in environ:
            headers["Content-Length"] = environ["CONTENT_LENGTH"]
        return headers

    def _read_body(self, environ: dict) -> bytes:
        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
        except (ValueError, TypeError):
            length = 0
        if length > 0:
            return environ["wsgi.input"].read(length)
        return b""
