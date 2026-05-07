"""CLI command to truncate large bodies in a reqtrace log file."""
from __future__ import annotations

import argparse
import sys

from reqtrace.storage import LogStorage
from reqtrace.truncator import truncate_all, _DEFAULT_MAX_BYTES


def build_truncate_parser(parent: argparse._SubParsersAction | None = None) -> argparse.ArgumentParser:  # noqa: E501
    kwargs = dict(
        prog="reqtrace truncate",
        description="Truncate oversized request/response bodies in a log file.",
    )
    if parent is not None:
        parser = parent.add_parser("truncate", **kwargs)
    else:
        parser = argparse.ArgumentParser(**kwargs)

    parser.add_argument("log_file", help="Path to the reqtrace log file.")
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=_DEFAULT_MAX_BYTES,
        metavar="N",
        help=f"Maximum body size in bytes before truncation (default: {_DEFAULT_MAX_BYTES}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be truncated without modifying the file.",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        default=None,
        help="Write truncated records to a different file instead of overwriting.",
    )
    return parser


def run_truncate(args: argparse.Namespace) -> int:
    storage = LogStorage(args.log_file)
    records = storage.load_all()

    if not records:
        print("No records found.")
        return 0

    result = truncate_all(records, max_bytes=args.max_bytes)
    print(str(result))

    if args.dry_run:
        print("Dry-run mode — no changes written.")
        return 0

    dest_path = args.output if args.output else args.log_file
    dest = LogStorage(dest_path)
    # Clear existing records only when overwriting the same file.
    if dest_path == args.log_file:
        import os
        try:
            os.remove(dest_path)
        except FileNotFoundError:
            pass
        dest = LogStorage(dest_path)

    for record in result.records:
        dest.save(record)

    print(f"Saved {len(result.records)} record(s) to '{dest_path}'.")
    return 0


def main() -> None:
    parser = build_truncate_parser()
    args = parser.parse_args()
    sys.exit(run_truncate(args))


if __name__ == "__main__":
    main()
