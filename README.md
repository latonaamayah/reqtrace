# reqtrace

Lightweight HTTP request logger and replayer for debugging microservice interactions during local development.

---

## Installation

```bash
pip install reqtrace
```

---

## Usage

Start the proxy logger on a given port and point your service at it:

```python
from reqtrace import Tracer

tracer = Tracer(target="http://localhost:8080", port=9090)
tracer.start()
```

Or use the CLI to capture and replay requests:

```bash
# Start logging requests
reqtrace record --target http://localhost:8080 --port 9090 --output session.json

# Replay a captured session
reqtrace replay --file session.json --target http://localhost:8080

# Diff two captured sessions
reqtrace diff --before baseline.json --after current.json
```

Captured logs include method, headers, body, response status, and latency — stored as plain JSON for easy inspection and diffing.

```json
{
  "timestamp": "2024-05-10T14:32:01Z",
  "method": "POST",
  "path": "/api/orders",
  "status": 201,
  "latency_ms": 42
}
```

---

## Why reqtrace?

- Zero-config setup for local dev environments
- Framework-agnostic — works with any HTTP-based service
- Replay traffic to reproduce bugs without re-triggering upstream calls
- Diff two sessions to spot regressions between deployments

---

## License

MIT © 2024 reqtrace contributors
