"""CLI entry-point for rate-limit analysis."""
from __future__ import annotations

import argparse
import sys

from reqtrace.storage import LogStorage
from reqtrace.filter import RecordFilter
from reqtrace.ratelimiter import analyze_rate_limits


def build_ratelimit_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="reqtrace ratelimit",
        description="Detect endpoints that exceed a request-rate threshold.",
    )
    p.add_argument("log_file", help="Path to the reqtrace log file.")
    p.add_argument(
        "--max-rps",
        type=float,
        default=10.0,
        metavar="N",
        help="Maximum allowed requests-per-second per endpoint (default: 10).",
    )
    p.add_argument("--method", default=None, help="Filter by HTTP method.")
    p.add_argument("--path-prefix", default=None, help="Filter by path prefix.")
    p.add_argument(
        "--violations-only",
        action="store_true",
        help="Only print endpoints that exceed the limit.",
    )
    return p


def run_ratelimit(args: argparse.Namespace) -> int:
    storage = LogStorage(args.log_file)
    records = storage.load_all()

    f = RecordFilter(
        method=args.method,
        path_prefix=args.path_prefix,
    )
    records = f.apply(records)

    result = analyze_rate_limits(records, max_rps=args.max_rps)

    if args.violations_only:
        if not result.violating:
            print("No rate-limit violations detected.")
            return 0
        for er in result.violating:
            print(er)
        return 1

    print(result)
    return 1 if result.violation_count > 0 else 0


def main() -> None:  # pragma: no cover
    parser = build_ratelimit_parser()
    args = parser.parse_args()
    sys.exit(run_ratelimit(args))


if __name__ == "__main__":  # pragma: no cover
    main()
