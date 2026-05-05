"""CLI entry point for reqtrace."""

import argparse
import sys
from reqtrace.storage import LogStorage
from reqtrace.filter import RecordFilter
from reqtrace.exporter import export_json, export_csv, export_curl
from reqtrace.summarizer import summarize, format_summary
from reqtrace.replayer import Replayer
from reqtrace.scorer import score_all


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reqtrace",
        description="Lightweight HTTP request logger and replayer.",
    )
    parser.add_argument("--storage", default="reqtrace_log.json", help="Storage file path")

    sub = parser.add_subparsers(dest="command")

    # list
    ls = sub.add_parser("list", help="List recorded requests")
    ls.add_argument("--method", help="Filter by HTTP method")
    ls.add_argument("--path-prefix", dest="path_prefix", help="Filter by path prefix")
    ls.add_argument("--status", type=int, help="Filter by status code")

    # export
    exp = sub.add_parser("export", help="Export records")
    exp.add_argument("--format", choices=["json", "csv", "curl"], default="json")
    exp.add_argument("--method", help="Filter by HTTP method")
    exp.add_argument("--path-prefix", dest="path_prefix")

    # summary
    sub.add_parser("summary", help="Show summary statistics")

    # replay
    rep = sub.add_parser("replay", help="Replay recorded requests")
    rep.add_argument("host", help="Target host, e.g. http://localhost:8080")
    rep.add_argument("--method", help="Filter by HTTP method")

    # score
    sc = sub.add_parser("score", help="Score records by anomaly indicators")
    sc.add_argument("--min-score", dest="min_score", type=int, default=0)

    return parser


def _load_filtered(storage: LogStorage, method=None, path_prefix=None, status=None):
    records = storage.load_all()
    f = RecordFilter(method=method, path_prefix=path_prefix, status_code=status)
    return f.apply(records)


def on_record(record):
    print(f"  [{record.response_status}] {record.method} {record.path} ({record.duration_ms}ms)")


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    storage = LogStorage(args.storage)

    if args.command == "list":
        records = _load_filtered(storage, method=getattr(args, "method", None),
                                 path_prefix=getattr(args, "path_prefix", None),
                                 status=getattr(args, "status", None))
        for r in records:
            print(f"{r.timestamp}  [{r.response_status}] {r.method} {r.path} ({r.duration_ms}ms)")
        print(f"\nTotal: {len(records)} record(s)")

    elif args.command == "export":
        records = _load_filtered(storage, method=getattr(args, "method", None),
                                 path_prefix=getattr(args, "path_prefix", None))
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

    elif args.command == "replay":
        records = _load_filtered(storage, method=getattr(args, "method", None))
        replayer = Replayer(args.host)
        results = replayer.replay_all(records)
        for res in results:
            status = res.response_status if res.response_status else "ERR"
            print(f"  [{status}] {res.record.method} {res.record.path}")
        print(f"\nReplayed: {len(results)} request(s)")

    elif args.command == "score":
        records = storage.load_all()
        results = score_all(records, min_score=args.min_score)
        if not results:
            print("No records meet the minimum score threshold.")
        for res in results:
            print(str(res))
            print()
        print(f"Scored: {len(results)} record(s)")


if __name__ == "__main__":
    main()
