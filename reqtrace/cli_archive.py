"""CLI sub-commands for archiving and restoring reqtrace logs."""

import argparse
import sys
from pathlib import Path

from reqtrace.archiver import archive, list_archive, restore
from reqtrace.storage import LogStorage


def build_archive_parser(parent: argparse._SubParsersAction = None):  # type: ignore[type-arg]
    desc = "Archive or restore reqtrace log snapshots."
    if parent is not None:
        parser = parent.add_parser("archive", help=desc)
    else:
        parser = argparse.ArgumentParser(prog="reqtrace-archive", description=desc)

    sub = parser.add_subparsers(dest="archive_cmd", required=True)

    # save sub-command
    save_p = sub.add_parser("save", help="Archive logs to a zip file.")
    save_p.add_argument("--log-dir", default=".reqtrace", help="Log directory.")
    save_p.add_argument("dest", help="Destination zip file path.")

    # load sub-command
    load_p = sub.add_parser("load", help="Restore logs from a zip file.")
    load_p.add_argument("--log-dir", default=".reqtrace", help="Log directory.")
    load_p.add_argument("src", help="Source zip file path.")

    # list sub-command
    list_p = sub.add_parser("list", help="List record ids in a zip archive.")
    list_p.add_argument("src", help="Source zip file path.")

    return parser


def run_archive(args: argparse.Namespace) -> int:
    if args.archive_cmd == "save":
        storage = LogStorage(args.log_dir)
        n = archive(storage, Path(args.dest))
        print(f"Archived {n} record(s) to {args.dest}")
        return 0

    if args.archive_cmd == "load":
        storage = LogStorage(args.log_dir)
        n = restore(Path(args.src), storage)
        print(f"Restored {n} record(s) from {args.src}")
        return 0

    if args.archive_cmd == "list":
        ids = list_archive(Path(args.src))
        if not ids:
            print("(empty archive)")
        else:
            for rid in ids:
                print(rid)
        return 0

    return 1


def main() -> None:  # pragma: no cover
    parser = build_archive_parser()
    args = parser.parse_args()
    sys.exit(run_archive(args))


if __name__ == "__main__":  # pragma: no cover
    main()
