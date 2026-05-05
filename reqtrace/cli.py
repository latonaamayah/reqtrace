"""CLI entry point for reqtrace."""

import argparse
import sys
from reqtrace.storage import LogStorage
from reqtrace.filter import RecordFilter
from reqtrace.exporter import export_json, export_csv, export_curl
from reqtrace.summarizer import summarize, format_summary
from reqtrace.differ import diff_by_index


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reqtrace", description="HTTP request logger and replayer"
    )
    parser.add_argument("--log-file", default="reqtrace.log", help="Path to log file")
    sub = parser.add_subparsers(dest="command")

    # list
    ls = sub.add_parser("list", help="List logged requests")
    ls.add_argument("--method", help="Filter by HTTP method")
    ls.add_argument("--path-prefix", help="Filter by path prefix")
    ls.add_argument("--status", type=int, help="Filter by status code")

    # export
    exp = sub.add_parser("export", help="Export requests")
    exp.add_argument("--format", choices=["json", "csv", "curl"], default="json")
    exp.add_argument("--method", help="Filter by HTTP method")
    exp.add_argument("--path-prefix", help="Filter by path prefix")

    # summary
    sub.add_parser("summary", help="Show summary statistics")

    # diff
    diff_p = sub.add_parser("diff", help="Diff two recorded requests by index")
    diff_p.add_argument("index_a", type=int, help="Index of first record")
    diff_p.add_argument("index_b", type=int, help="Index of second record")

    return parser


def _load_filtered(storage: LogStorage, args: argparse.Namespace):
    records = storage.load_all()
    method = getattr(args, "method", None)
    path_prefix = getattr(args, "path_prefix", None)
    status = getattr(args, "status", None)
    f = RecordFilter(method=method, path_prefix=path_prefix, status_code=status)
    return f.apply(records)


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    storage = LogStorage(args.log_file)

    if args.command == "list":
        records = _load_filtered(storage, args)
        if not records:
            print("No records found.")
            return
        for i, r in enumerate(records):
            print(f"[{i}] {r.timestamp} {r.method} {r.path} -> {r.status_code} ({r.duration_ms:.1f}ms)")

    elif args.command == "export":
        records = _load_filtered(storage, args)
        fmt = args.format
        if fmt == "json":
            print(export_json(records))
        elif fmt == "csv":
            print(export_csv(records))
        elif fmt == "curl":
            print(export_curl(records))

    elif args.command == "summary":
        records = storage.load_all()
        stats = summarize(records)
        print(format_summary(stats))

    elif args.command == "diff":
        records = storage.load_all()
        result = diff_by_index(records, args.index_a, args.index_b)
        if result is None:
            print("Error: one or both indices are out of range.", file=sys.stderr)
            sys.exit(1)
        print(result.format())

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
