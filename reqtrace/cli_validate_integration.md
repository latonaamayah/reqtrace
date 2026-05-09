# `reqtrace validate` — CLI Integration Notes

## Overview

The `validate` sub-command checks a recorded log file against a set of
built-in (and optionally user-supplied) rules, printing a human-readable
summary and optionally exiting with a non-zero code when violations are
found — making it easy to integrate into CI pipelines.

## Usage

```bash
# Basic: check all records for 5xx responses and empty paths
reqtrace validate requests.jsonl

# Fail the build if any violation is detected
reqtrace validate requests.jsonl --exit-nonzero

# Also enforce a maximum response time
reqtrace validate requests.jsonl --max-duration 500 --exit-nonzero

# Scope to a specific path prefix
reqtrace validate requests.jsonl --path-prefix /api/v2 --exit-nonzero
```

## Built-in Rules

| Rule | Flag | Description |
|---|---|---|
| `no_server_error` | `--no-5xx` (default on) | Fails any record with HTTP 5xx status. |
| `non_empty_path` | always active | Fails records whose `path` is blank/whitespace. |
| `duration_below_Nms` | `--max-duration N` | Fails records slower than *N* milliseconds. |

## Programmatic API

```python
from reqtrace.validator import Validator, require_status_below_500, require_duration_below

v = Validator()
v.add_rule(require_status_below_500())
v.add_rule(require_duration_below(300))

result = v.validate(records)
print(result)          # human-readable summary
print(result.errors)   # list of ValidationError objects
```

## Exit Codes

- `0` — all records passed (or `--exit-nonzero` not set).
- `1` — one or more validation errors found and `--exit-nonzero` was supplied.
