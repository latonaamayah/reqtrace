"""CLI command for aggregating request records per endpoint."""
from __future__ import annotations

import argparse
import sys

from reqtrace.aggregator import aggregate
from reqtrace.filter import RecordFilter
from reqtrace.storage import LogStorage


def build_aggregate_parser(parent: argparse._SubParsersAction | None = None) -> argparse.ArgumentParser:
    kwargs = dict(description="Aggregate request records per endpoint")
    parser = (
        parent.add_parser("aggregate", **kwargs) if parent else argparse.ArgumentParser(**kwargs)
    )
    parser.add_argument("--log-file", default="reqtrace.log", help="Path to log file")
    parser.add_argument("--method", help="Filter by HTTP method")
    parser.add_argument("--path-prefix", help="Filter by path prefix")
    parser.add_argument("--sort", choices=["count", "duration"], default="count",
                        help="Sort output by count or avg duration (default: count)")
    parser.add_argument("--top", type=int, default=0, help="Show only top N endpoints (0 = all)")
    return parser


def run_aggregate(args: argparse.Namespace, out=sys.stdout) -> None:
    storage = LogStorage(args.log_file)
    records = storage.load_all()

    f = RecordFilter(
        method=args.method,
        path_prefix=args.path_prefix,
    )
    records = f.apply(records)

    result = aggregate(records)

    if not result.endpoints:
        out.write("No records found.\n")
        return

    stats_list = (
        result.sorted_by_avg_duration()
        if args.sort == "duration"
        else result.sorted_by_count()
    )

    if args.top > 0:
        stats_list = stats_list[: args.top]

    out.write(f"Aggregated {result.total_requests} request(s) across {len(result.endpoints)} endpoint(s):\n")
    for stats in stats_list:
        out.write(f"  {stats}\n")


def main() -> None:  # pragma: no cover
    parser = build_aggregate_parser()
    args = parser.parse_args()
    run_aggregate(args)


if __name__ == "__main__":  # pragma: no cover
    main()
