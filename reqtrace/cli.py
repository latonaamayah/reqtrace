"""Main CLI entry point for reqtrace."""

import argparse
import sys

from reqtrace.filter import RecordFilter
from reqtrace.storage import LogStorage


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reqtrace",
        description="Lightweight HTTP request logger and replayer.",
    )
    parser.add_argument("--log-dir", default=".reqtrace", help="Log directory.")
    sub = parser.add_subparsers(dest="command")

    # list
    list_p = sub.add_parser("list", help="List recorded requests.")
    list_p.add_argument("--method", help="Filter by HTTP method.")
    list_p.add_argument("--path-prefix", help="Filter by path prefix.")
    list_p.add_argument("--status", type=int, help="Filter by status code.")
    list_p.add_argument("--min-duration", type=float, default=0.0)
    list_p.add_argument("--max-duration", type=float, default=float("inf"))

    # export
    exp_p = sub.add_parser("export", help="Export recorded requests.")
    exp_p.add_argument("--format", choices=["json", "csv", "curl"], default="json")
    exp_p.add_argument("--method", help="Filter by HTTP method.")
    exp_p.add_argument("--path-prefix", help="Filter by path prefix.")
    exp_p.add_argument("--status", type=int, help="Filter by status code.")
    exp_p.add_argument("--min-duration", type=float, default=0.0)
    exp_p.add_argument("--max-duration", type=float, default=float("inf"))

    # watch
    watch_p = sub.add_parser("watch", help="Watch for new requests in real time.")
    watch_p.add_argument("--interval", type=float, default=1.0)

    # archive sub-command group
    from reqtrace.cli_archive import build_archive_parser
    build_archive_parser(sub)

    return parser


def _load_filtered(args: argparse.Namespace):
    storage = LogStorage(args.log_dir)
    records = storage.load_all()
    f = RecordFilter(
        method=getattr(args, "method", None),
        path_prefix=getattr(args, "path_prefix", None),
        status_code=getattr(args, "status", None),
        min_duration=getattr(args, "min_duration", 0.0),
        max_duration=getattr(args, "max_duration", float("inf")),
    )
    return f.apply(records)


def on_record(record) -> None:  # pragma: no cover
    print(f"[NEW] {record.timestamp} {record.method} {record.path} -> {record.status_code}")


def main() -> None:  # pragma: no cover
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "list":
        records = _load_filtered(args)
        if not records:
            print("No records found.")
        for r in records:
            print(f"{r.timestamp}  {r.method:<7} {r.path:<40} {r.status_code}  {r.duration:.3f}s")

    elif args.command == "export":
        from reqtrace.exporter import export_csv, export_curl, export_json
        records = _load_filtered(args)
        if args.format == "json":
            print(export_json(records))
        elif args.format == "csv":
            print(export_csv(records))
        else:
            print(export_curl(records))

    elif args.command == "watch":
        from reqtrace.watcher import StorageWatcher
        storage = LogStorage(args.log_dir)
        watcher = StorageWatcher(storage, on_record, interval=args.interval)
        print(f"Watching {args.log_dir} (Ctrl-C to stop)…")
        watcher.start()
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            watcher.stop()

    elif args.command == "archive":
        from reqtrace.cli_archive import run_archive
        sys.exit(run_archive(args))

    else:
        parser.print_help()


if __name__ == "__main__":  # pragma: no cover
    main()
