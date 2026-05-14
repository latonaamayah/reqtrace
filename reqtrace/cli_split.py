"""CLI entry-point for the splitter module."""
from __future__ import annotations

import argparse
import sys

from reqtrace.splitter import _by_method, _by_path_prefix, _by_status_class, split
from reqtrace.storage import LogStorage


def build_split_parser(parent: argparse._SubParsersAction | None = None) -> argparse.ArgumentParser:
    description = "Split a request log into per-bucket files."
    if parent is not None:
        parser = parent.add_parser("split", help=description, description=description)
    else:
        parser = argparse.ArgumentParser(prog="reqtrace split", description=description)

    parser.add_argument("log", help="Path to the source .jsonl log file.")
    parser.add_argument(
        "--by",
        choices=["method", "status", "path"],
        default="method",
        help="Field to split on (default: method).",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=1,
        metavar="N",
        help="Path prefix depth when --by=path (default: 1).",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        metavar="DIR",
        help="Directory to write per-bucket .jsonl files (optional).",
    )
    return parser


def run_split(args: argparse.Namespace) -> int:
    storage = LogStorage(args.log)

    if args.by == "method":
        key_fn = _by_method
    elif args.by == "status":
        key_fn = _by_status_class
    else:
        key_fn = _by_path_prefix(depth=args.depth)

    persist = args.output_dir is not None
    result = split(storage, key_fn, output_dir=args.output_dir, persist=persist)

    print(str(result))
    if persist:
        print(f"\nBucket files written to: {args.output_dir}")

    return 0


def main() -> None:  # pragma: no cover
    parser = build_split_parser()
    args = parser.parse_args()
    sys.exit(run_split(args))


if __name__ == "__main__":  # pragma: no cover
    main()
