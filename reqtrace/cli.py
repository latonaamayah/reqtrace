"""Command-line interface for reqtrace."""

import argparse
import sys
from typing import List

from reqtrace.storage import LogStorage, RequestRecord
from reqtrace.filter import RecordFilter
from reqtrace.exporter import export_json, export_csv, export_curl
from reqtrace.summarizer import format_summary, summarize
from reqtrace.replayer import Replayer
from reqtrace.grouper import (
    group_by_method,
    group_by_status,
    group_by_path_prefix,
    format_groups,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reqtrace", description="Lightweight HTTP request logger and replayer."
    )
    parser.add_argument("--storage", default="reqtrace_log.jsonl", help="Storage file path")
    sub = parser.add_subparsers(dest="command")

    # list
    ls = sub.add_parser("list", help="List recorded requests")
    ls.add_argument("--method", help="Filter by HTTP method")
    ls.add_argument("--path-prefix", help="Filter by path prefix")
    ls.add_argument("--status", type=int, help="Filter by status code")

    # summary
    sub.add_parser("summary", help="Show summary statistics")

    # export
    exp = sub.add_parser("export", help="Export records")
    exp.add_argument("format", choices=["json", "csv", "curl"])
    exp.add_argument("--output", "-o", help="Output file (default: stdout)")

    # replay
    rep = sub.add_parser("replay", help="Replay recorded requests")
    rep.add_argument("target", help="Target base URL, e.g. http://localhost:8080")

    # group
    grp = sub.add_parser("group", help="Group requests by a dimension")
    grp.add_argument(
        "by", choices=["method", "status", "path"], help="Dimension to group by"
    )
    grp.add_argument(
        "--depth", type=int, default=1, help="Path prefix depth (used with 'path')"
    )

    return parser


def _load_filtered(storage: LogStorage, args: argparse.Namespace) -> List[RequestRecord]:
    records = storage.load_all()
    f = RecordFilter(
        method=getattr(args, "method", None),
        path_prefix=getattr(args, "path_prefix", None),
        status_code=getattr(args, "status", None),
    )
    return f.apply(records)


def on_record(record: RequestRecord) -> None:  # pragma: no cover
    print(f"[reqtrace] {record.method} {record.path} -> {record.status_code}")


def main(argv=None) -> int:  # pragma: no cover
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    storage = LogStorage(args.storage)

    if args.command == "list":
        records = _load_filtered(storage, args)
        for r in records:
            print(f"{r.timestamp} {r.method:7} {r.path} {r.status_code} {r.duration_ms:.1f}ms")
        return 0

    if args.command == "summary":
        records = storage.load_all()
        print(format_summary(summarize(records)))
        return 0

    if args.command == "export":
        records = storage.load_all()
        if args.format == "json":
            out = export_json(records)
        elif args.format == "csv":
            out = export_csv(records)
        else:
            out = export_curl(records)
        if args.output:
            with open(args.output, "w") as fh:
                fh.write(out)
        else:
            print(out)
        return 0

    if args.command == "replay":
        records = storage.load_all()
        replayer = Replayer(args.target)
        results = replayer.replay_all(records)
        for res in results:
            status = res.status_code if res.status_code else "ERR"
            print(f"{res.record.method} {res.record.path} -> {status}")
        return 0

    if args.command == "group":
        records = storage.load_all()
        if args.by == "method":
            groups = group_by_method(records)
        elif args.by == "status":
            groups = group_by_status(records)
        else:
            groups = group_by_path_prefix(records, depth=args.depth)
        print(format_groups(groups))
        return 0

    return 0
