"""Minimal CLI for reqtrace — inspect, export, and summarize captured requests."""

import argparse
import sys

from reqtrace.storage import LogStorage
from reqtrace.exporter import export_json, export_csv, export_curl
from reqtrace.summarizer import summarize, format_summary
from reqtrace.filter import RecordFilter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reqtrace",
        description="Lightweight HTTP request logger and replayer.",
    )
    parser.add_argument("--log-file", default="reqtrace.json", help="Path to the log file.")

    sub = parser.add_subparsers(dest="command")

    # summary
    sub.add_parser("summary", help="Print a summary of logged requests.")

    # export
    exp = sub.add_parser("export", help="Export logged requests.")
    exp.add_argument("format", choices=["json", "csv", "curl"], help="Output format.")
    exp.add_argument("--output", "-o", default="-", help="Output file path (default: stdout).")

    # filter flags shared by summary and export
    for p in (sub.choices.get("summary"), exp):
        if p is None:
            continue
        p.add_argument("--method", help="Filter by HTTP method.")
        p.add_argument("--path-prefix", help="Filter by path prefix.")
        p.add_argument("--status", type=int, help="Filter by status code.")
        p.add_argument("--min-duration", type=float, help="Minimum duration in ms.")
        p.add_argument("--max-duration", type=float, help="Maximum duration in ms.")

    return parser


def _load_filtered(args):
    storage = LogStorage(args.log_file)
    records = storage.load_all()
    f = RecordFilter(
        method=getattr(args, "method", None),
        path_prefix=getattr(args, "path_prefix", None),
        status_code=getattr(args, "status", None),
        min_duration_ms=getattr(args, "min_duration", None),
        max_duration_ms=getattr(args, "max_duration", None),
    )
    return f.apply(records)


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "summary":
        records = _load_filtered(args)
        print(format_summary(summarize(records)))

    elif args.command == "export":
        records = _load_filtered(args)
        if args.format == "json":
            out = export_json(records)
        elif args.format == "csv":
            out = export_csv(records)
        else:
            out = export_curl(records)

        if args.output == "-":
            print(out)
        else:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(out)
            print(f"Exported {len(records)} record(s) to {args.output}", file=sys.stderr)

    else:
        parser.print_help()


if __name__ == "__main__":  # pragma: no cover
    main()
