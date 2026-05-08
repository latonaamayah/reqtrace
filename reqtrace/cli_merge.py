"""CLI entry-point for the merge command."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from reqtrace.merger import merge
from reqtrace.storage import LogStorage


def build_merge_parser(parent: argparse._SubParsersAction | None = None) -> argparse.ArgumentParser:  # type: ignore[type-arg]
    description = "Merge multiple reqtrace log files into a single destination."
    if parent is not None:
        parser = parent.add_parser("merge", help=description)
    else:
        parser = argparse.ArgumentParser(prog="reqtrace-merge", description=description)

    parser.add_argument(
        "sources",
        nargs="+",
        metavar="SOURCE",
        help="Paths to source log files (JSON-lines).",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        metavar="DEST",
        help="Destination log file path.",
    )
    parser.add_argument(
        "--no-dedup",
        action="store_true",
        default=False,
        help="Disable deduplication (keep all records, including duplicates).",
    )
    return parser


def run_merge(args: argparse.Namespace) -> int:
    source_storages = []
    for path in args.sources:
        p = Path(path)
        if not p.exists():
            print(f"[error] source file not found: {path}", file=sys.stderr)
            return 1
        source_storages.append(LogStorage(str(p)))

    destination = LogStorage(args.output)
    result = merge(
        sources=source_storages,
        destination=destination,
        deduplicate=not args.no_dedup,
    )
    print(str(result))
    return 0


def main() -> None:
    parser = build_merge_parser()
    args = parser.parse_args()
    sys.exit(run_merge(args))


if __name__ == "__main__":
    main()
