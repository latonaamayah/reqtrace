"""CLI entry-point for the throttler: trim a log file to a max requests/sec rate."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from reqtrace.storage import LogStorage
from reqtrace.throttler import ThrottleConfig, throttle_records


def build_throttle_parser(parent: argparse._SubParsersAction | None = None) -> argparse.ArgumentParser:  # type: ignore[type-arg]
    kwargs = dict(
        prog="reqtrace throttle",
        description="Drop records that exceed a maximum requests-per-second rate.",
    )
    parser = (
        parent.add_parser("throttle", **kwargs)  # type: ignore[arg-type]
        if parent is not None
        else argparse.ArgumentParser(**kwargs)  # type: ignore[arg-type]
    )
    parser.add_argument("log_file", help="Path to the request log (JSON-lines).")
    parser.add_argument(
        "--max-rps",
        type=float,
        required=True,
        dest="max_rps",
        help="Maximum requests per second to retain.",
    )
    parser.add_argument(
        "--window-ms",
        type=float,
        default=1000.0,
        dest="window_ms",
        help="Bucket window in milliseconds (default: 1000).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Write kept records to this file (default: overwrite input).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print summary without writing any files.",
    )
    return parser


def run_throttle(args: argparse.Namespace) -> int:
    storage = LogStorage(args.log_file)
    records = storage.load_all()

    try:
        config = ThrottleConfig(max_rps=args.max_rps, window_ms=args.window_ms)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    result = throttle_records(records, config)
    print(result)

    if args.dry_run:
        return 0

    out_path = args.output or args.log_file
    out_storage = LogStorage(out_path)
    # Overwrite: clear then re-save
    Path(out_path).write_text("")
    for record in result.kept:
        out_storage.save(record)

    print(f"Written {result.kept_count} records to {out_path}")
    return 0


def main() -> None:  # pragma: no cover
    parser = build_throttle_parser()
    args = parser.parse_args()
    sys.exit(run_throttle(args))


if __name__ == "__main__":  # pragma: no cover
    main()
