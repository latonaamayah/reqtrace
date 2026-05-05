"""CLI entry point for reqtrace."""

import argparse
import sys

from reqtrace.storage import LogStorage
from reqtrace.filter import RecordFilter
from reqtrace.exporter import export_json, export_csv, export_curl
from reqtrace.summarizer import format_summary, summarize
from reqtrace.replayer import Replayer
from reqtrace.watcher import StorageWatcher


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reqtrace",
        description="Lightweight HTTP request logger and replayer.",
    )
    parser.add_argument("--log-file", default="reqtrace.json", help="Path to log file")

    sub = parser.add_subparsers(dest="command")

    # show
    show = sub.add_parser("show", help="Display logged requests")
    show.add_argument("--method", help="Filter by HTTP method")
    show.add_argument("--path-prefix", help="Filter by path prefix")
    show.add_argument("--status", type=int, help="Filter by status code")
    show.add_argument("--format", choices=["json", "csv", "curl"], default="json")

    # summary
    sub.add_parser("summary", help="Show summary statistics")

    # replay
    replay = sub.add_parser("replay", help="Replay logged requests")
    replay.add_argument("host", help="Target host (e.g. localhost)")
    replay.add_argument("port", type=int, help="Target port")
    replay.add_argument("--method", help="Filter by HTTP method")
    replay.add_argument("--path-prefix", help="Filter by path prefix")

    # watch
    watch = sub.add_parser("watch", help="Watch log file and print new requests live")
    watch.add_argument("--method", help="Filter by HTTP method")
    watch.add_argument("--path-prefix", help="Filter by path prefix")

    return parser


def _load_filtered(storage, args):
    f = RecordFilter(
        method=getattr(args, "method", None),
        path_prefix=getattr(args, "path_prefix", None),
        status_code=getattr(args, "status", None),
    )
    return f.apply(storage.load_all())


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    storage = LogStorage(args.log_file)

    if args.command == "show":
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
        print(format_summary(summarize(records)))

    elif args.command == "replay":
        records = _load_filtered(storage, args)
        replayer = Replayer(args.host, args.port)
        results = replayer.replay_all(records)
        for r in results:
            status = r.response_status if r.success else f"ERR: {r.error}"
            print(f"{r.record.method} {r.record.path} -> {status}")

    elif args.command == "watch":
        method = getattr(args, "method", None)
        path_prefix = getattr(args, "path_prefix", None)
        f = RecordFilter(method=method, path_prefix=path_prefix)

        def on_record(record):
            if f.matches(record):
                print(f"[NEW] {record.method} {record.path} {record.status_code} ({record.duration_ms:.1f}ms)")
                sys.stdout.flush()

        print(f"Watching {args.log_file} for new requests... (Ctrl+C to stop)")
        with StorageWatcher(storage, on_record, poll_interval=1.0):
            try:
                while True:
                    import time; time.sleep(1)
            except KeyboardInterrupt:
                print("\nStopped.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
