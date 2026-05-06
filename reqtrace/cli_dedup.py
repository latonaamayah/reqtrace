"""CLI sub-command: deduplicate stored request logs."""
from __future__ import annotations

import argparse
import sys

from reqtrace.deduplicator import deduplicate, find_duplicate_groups
from reqtrace.storage import LogStorage


def build_dedup_parser(parent: argparse._SubParsersAction | None = None) -> argparse.ArgumentParser:
    kwargs = dict(
        prog="reqtrace dedup",
        description="Remove duplicate request records from a log file.",
    )
    parser = parent.add_parser("dedup", **kwargs) if parent else argparse.ArgumentParser(**kwargs)
    parser.add_argument("log_file", help="Path to the .jsonl log file")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report duplicates without modifying the file",
    )
    parser.add_argument(
        "--show-groups",
        action="store_true",
        help="Print each group of duplicate records",
    )
    return parser


def run_dedup(args: argparse.Namespace) -> int:
    storage = LogStorage(args.log_file)
    records = storage.load_all()

    if not records:
        print("No records found.")
        return 0

    result = deduplicate(records)
    print(str(result))

    if args.show_groups:
        groups = find_duplicate_groups(records)
        for i, group in enumerate(groups, 1):
            print(f"\nDuplicate group {i} ({len(group)} records):")
            for rec in group:
                print(f"  [{rec.timestamp}] {rec.method} {rec.path} -> {rec.status_code}")

    if args.dry_run:
        print("Dry-run mode: no changes written.")
        return 0

    for rec in result.unique:
        pass  # already filtered

    # Overwrite storage with unique records only
    import os
    tmp = args.log_file + ".tmp"
    tmp_storage = LogStorage(tmp)
    for rec in result.unique:
        tmp_storage.save(rec)
    os.replace(tmp, args.log_file)
    print(f"Wrote {result.unique_count} unique records to {args.log_file}.")
    return 0


def main() -> None:
    parser = build_dedup_parser()
    args = parser.parse_args()
    sys.exit(run_dedup(args))


if __name__ == "__main__":
    main()
