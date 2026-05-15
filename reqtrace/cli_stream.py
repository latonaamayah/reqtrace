"""CLI entry point for streaming records in batches."""
from __future__ import annotations

import argparse
import sys
from typing import List

from reqtrace.storage import LogStorage
from reqtrace.streamer import StreamConfig, StreamResult, stream_records
from reqtrace.formatter import format_record


def build_stream_parser(parent: argparse._SubParsersAction = None) -> argparse.ArgumentParser:  # type: ignore[type-arg]
    kwargs = dict(description="Stream records from storage in batches")
    parser = (
        parent.add_parser("stream", **kwargs) if parent else argparse.ArgumentParser(**kwargs)
    )
    parser.add_argument("--log-file", default="reqtrace.log", help="Path to log file")
    parser.add_argument("--batch-size", type=int, default=10, help="Records per batch")
    parser.add_argument("--max-records", type=int, default=None, help="Max total records to stream")
    parser.add_argument("--method", default=None, help="Filter by HTTP method")
    parser.add_argument("--status", type=int, default=None, help="Filter by status code")
    parser.add_argument("--headers", action="store_true", help="Show headers in output")
    return parser


def run_stream(args: argparse.Namespace) -> int:
    storage = LogStorage(args.log_file)

    predicate = None
    filters: List = []
    if args.method:
        m = args.method.upper()
        filters.append(lambda r, _m=m: r.method == _m)
    if args.status:
        s = args.status
        filters.append(lambda r, _s=s: r.response_status == _s)
    if filters:
        def predicate(record):  # type: ignore[misc]
            return all(f(record) for f in filters)

    try:
        config = StreamConfig(batch_size=args.batch_size, max_records=args.max_records, predicate=predicate)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    gen = stream_records(storage, config)
    result: StreamResult = StreamResult()
    try:
        while True:
            batch = next(gen)
            for record in batch:
                print(format_record(record, show_headers=args.headers))
    except StopIteration as exc:
        result = exc.value

    print(f"\n{result}")
    return 0


def main() -> None:
    parser = build_stream_parser()
    args = parser.parse_args()
    sys.exit(run_stream(args))


if __name__ == "__main__":
    main()
