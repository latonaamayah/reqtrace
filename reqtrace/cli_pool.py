"""CLI entry-point for parallel replay via the pool."""
from __future__ import annotations

import argparse
import sys

from reqtrace.filter import RecordFilter
from reqtrace.replayer_pool import PoolConfig, PoolResult, replay_pool
from reqtrace.storage import LogStorage


def build_pool_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="reqtrace-pool",
        description="Replay HTTP records concurrently against a target server.",
    )
    p.add_argument("log_file", help="Path to the .jsonl log file")
    p.add_argument("base_url", help="Base URL of the target server, e.g. http://localhost:8080")
    p.add_argument("--workers", type=int, default=4, metavar="N", help="Thread pool size (default: 4)")
    p.add_argument("--timeout", type=float, default=10.0, metavar="SEC", help="Per-request timeout in seconds (default: 10)")
    p.add_argument("--method", metavar="METHOD", help="Filter by HTTP method")
    p.add_argument("--path-prefix", metavar="PREFIX", help="Filter by path prefix")
    p.add_argument("--status", type=int, metavar="CODE", help="Filter by response status code")
    return p


def _print_result(result: PoolResult) -> None:
    for r in result.results:
        status = r.status_code if r.status_code is not None else "ERR"
        print(f"  {r.record.method} {r.record.path} -> {status}")
    for err in result.errors:
        print(f"  ERROR: {err}", file=sys.stderr)
    print(str(result))


def run_pool(args: argparse.Namespace) -> int:
    storage = LogStorage(args.log_file)
    records = storage.load_all()

    rf = RecordFilter(
        method=args.method,
        path_prefix=args.path_prefix,
        status_code=args.status,
    )
    records = rf.apply(records)

    if not records:
        print("No records to replay.")
        return 0

    config = PoolConfig(max_workers=args.workers, timeout_seconds=args.timeout)
    result = replay_pool(records, base_url=args.base_url, config=config)
    _print_result(result)
    return 1 if result.error_count > 0 else 0


def main() -> None:
    parser = build_pool_parser()
    args = parser.parse_args()
    sys.exit(run_pool(args))


if __name__ == "__main__":
    main()
