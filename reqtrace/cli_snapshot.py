"""CLI sub-commands for snapshot management."""
from __future__ import annotations

import argparse
import sys

from reqtrace.snapshotter import (
    delete_snapshot,
    list_snapshots,
    load_snapshot,
    save_snapshot,
)
from reqtrace.storage import LogStorage


def build_snapshot_parser(sub: "argparse._SubParsersAction") -> argparse.ArgumentParser:  # type: ignore[type-arg]
    p = sub.add_parser("snapshot", help="Manage point-in-time snapshots of request logs")
    sp = p.add_subparsers(dest="snapshot_cmd", required=True)

    save_p = sp.add_parser("save", help="Save current logs as a named snapshot")
    save_p.add_argument("name", help="Snapshot name")
    save_p.add_argument("--log-file", default="reqtrace.log", help="Source log file")
    save_p.add_argument("--snapshot-dir", default=".reqtrace_snapshots", help="Snapshot directory")

    load_p = sp.add_parser("load", help="Print records from a named snapshot")
    load_p.add_argument("name", help="Snapshot name")
    load_p.add_argument("--snapshot-dir", default=".reqtrace_snapshots")

    list_p = sp.add_parser("list", help="List available snapshots")
    list_p.add_argument("--snapshot-dir", default=".reqtrace_snapshots")

    del_p = sp.add_parser("delete", help="Delete a named snapshot")
    del_p.add_argument("name", help="Snapshot name")
    del_p.add_argument("--snapshot-dir", default=".reqtrace_snapshots")

    return p


def run_snapshot(args: argparse.Namespace) -> int:
    cmd = args.snapshot_cmd

    if cmd == "save":
        storage = LogStorage(args.log_file)
        result = save_snapshot(storage, args.name, args.snapshot_dir)
        print(result)
        return 0

    if cmd == "load":
        try:
            records = load_snapshot(args.name, args.snapshot_dir)
        except FileNotFoundError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        for r in records:
            print(f"{r.timestamp}  {r.method:6s}  {r.path}  -> {r.status_code}")
        print(f"\n{len(records)} record(s) in snapshot '{args.name}'.")
        return 0

    if cmd == "list":
        metas = list_snapshots(args.snapshot_dir)
        if not metas:
            print("No snapshots found.")
            return 0
        for m in metas:
            print(m)
        return 0

    if cmd == "delete":
        removed = delete_snapshot(args.name, args.snapshot_dir)
        if removed:
            print(f"Snapshot '{args.name}' deleted.")
        else:
            print(f"Snapshot '{args.name}' not found.", file=sys.stderr)
            return 1
        return 0

    print(f"Unknown snapshot sub-command: {cmd}", file=sys.stderr)
    return 2


def main() -> None:  # pragma: no cover
    parser = argparse.ArgumentParser(prog="reqtrace-snapshot")
    sub = parser.add_subparsers(dest="snapshot_cmd", required=True)
    build_snapshot_parser(sub)
    args = parser.parse_args()
    sys.exit(run_snapshot(args))
