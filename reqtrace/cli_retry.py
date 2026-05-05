"""CLI subcommand: retry — replay failed requests with automatic retry logic."""

from __future__ import annotations

import argparse
import json
import sys
from typing import List

from reqtrace.filter import RecordFilter
from reqtrace.replayer import Replayer
from reqtrace.retry_report import format_retry_report, retry_summary_dict
from reqtrace.retrier import RetryConfig, Retrier
from reqtrace.storage import LogStorage


def build_retry_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("retry", help="Replay requests with retry logic")
    p.add_argument("--storage", required=True, help="Path to storage directory")
    p.add_argument("--target", required=True, help="Base URL to replay against")
    p.add_argument("--max-attempts", type=int, default=3)
    p.add_argument("--backoff", type=float, default=0.5, help="Initial backoff in seconds")
    p.add_argument("--multiplier", type=float, default=2.0)
    p.add_argument("--method", default=None, help="Filter by HTTP method")
    p.add_argument("--path-prefix", default=None)
    p.add_argument("--status", type=int, default=None, help="Filter by recorded status")
    p.add_argument("--json", dest="output_json", action="store_true",
                   help="Output JSON summary instead of text")
    p.set_defaults(func=run_retry)


def run_retry(args: argparse.Namespace) -> None:
    storage = LogStorage(args.storage)
    records = storage.load_all()

    f = RecordFilter(
        method=args.method,
        path_prefix=args.path_prefix,
        status_code=args.status,
    )
    records = f.apply(records)

    if not records:
        print("No records matched the filter.", file=sys.stderr)
        sys.exit(0)

    replayer = Replayer(base_url=args.target)
    config = RetryConfig(
        max_attempts=args.max_attempts,
        backoff_base=args.backoff,
        backoff_multiplier=args.multiplier,
    )
    retrier = Retrier(replayer, config=config)
    outcomes = retrier.retry_all(records)

    if args.output_json:
        print(json.dumps(retry_summary_dict(outcomes), indent=2))
    else:
        print(format_retry_report(outcomes))

    failed = sum(1 for o in outcomes if not o.succeeded)
    sys.exit(1 if failed else 0)
