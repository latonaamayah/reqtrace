"""CLI entry-point for the pivot sub-command."""
from __future__ import annotations

import argparse
import sys
from typing import List

from reqtrace.filter import RecordFilter
from reqtrace.pivot import pivot
from reqtrace.storage import LogStorage

_BUILTIN_CHOICES = ["method", "status_class", "status"]


def build_pivot_parser(parent: argparse._SubParsersAction | None = None) -> argparse.ArgumentParser:  # type: ignore[type-arg]
    kwargs = dict(description="Pivot request records into a 2-D frequency table.")
    if parent is not None:
        parser = parent.add_parser("pivot", **kwargs)
    else:
        parser = argparse.ArgumentParser(prog="reqtrace-pivot", **kwargs)
    parser.add_argument("log_file", help="Path to the JSONL log file.")
    parser.add_argument(
        "--rows",
        default="method",
        choices=_BUILTIN_CHOICES,
        help="Dimension for table rows (default: method).",
    )
    parser.add_argument(
        "--cols",
        default="status_class",
        choices=_BUILTIN_CHOICES,
        help="Dimension for table columns (default: status_class).",
    )
    parser.add_argument("--method", default=None, help="Filter by HTTP method.")
    parser.add_argument("--status", type=int, default=None, help="Filter by status code.")
    parser.add_argument("--path-prefix", default=None, dest="path_prefix", help="Filter by path prefix.")
    return parser


def run_pivot(args: argparse.Namespace, out=sys.stdout) -> int:
    storage = LogStorage(args.log_file)
    records = storage.load_all()

    f = RecordFilter(
        method=args.method,
        status_code=args.status,
        path_prefix=args.path_prefix,
    )
    records = f.apply(records)

    if not records:
        out.write("No records found.\n")
        return 0

    table = pivot(records, row_by=args.rows, col_by=args.cols)
    out.write(str(table) + "\n")
    return 0


def main(argv: List[str] | None = None) -> None:
    parser = build_pivot_parser()
    args = parser.parse_args(argv)
    sys.exit(run_pivot(args))


if __name__ == "__main__":  # pragma: no cover
    main()
