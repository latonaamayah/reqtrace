"""CLI sub-command: profile — show latency statistics for logged requests."""
from __future__ import annotations

import argparse
import sys

from reqtrace.storage import LogStorage
from reqtrace.filter import RecordFilter
from reqtrace.profiler import profile, profile_by_path


def build_profile_parser(subparsers=None) -> argparse.ArgumentParser:
    description = "Show latency percentiles and bucket distribution for captured requests."
    if subparsers is not None:
        p = subparsers.add_parser("profile", help=description)
    else:
        p = argparse.ArgumentParser(prog="reqtrace-profile", description=description)

    p.add_argument("--log-dir", default=".reqtrace", help="Storage directory (default: .reqtrace)")
    p.add_argument("--method", help="Filter by HTTP method")
    p.add_argument("--path-prefix", dest="path_prefix", help="Filter by path prefix")
    p.add_argument("--status", type=int, help="Filter by status code")
    p.add_argument(
        "--by-path",
        action="store_true",
        help="Break down statistics per (method, path) pair",
    )
    return p


def run_profile(args: argparse.Namespace, out=None) -> int:
    if out is None:
        out = sys.stdout

    storage = LogStorage(args.log_dir)
    records = storage.load_all()

    f = RecordFilter(
        method=getattr(args, "method", None),
        path_prefix=getattr(args, "path_prefix", None),
        status_code=getattr(args, "status", None),
    )
    records = f.apply(records)

    if not records:
        out.write("No records found.\n")
        return 0

    if getattr(args, "by_path", False):
        breakdown = profile_by_path(records)
        for key, result in sorted(breakdown.items()):
            out.write(f"\n=== {key} ===\n")
            out.write(str(result) + "\n")
    else:
        result = profile(records)
        out.write(str(result) + "\n")

    return 0


def main() -> None:  # pragma: no cover
    parser = build_profile_parser()
    args = parser.parse_args()
    sys.exit(run_profile(args))


if __name__ == "__main__":  # pragma: no cover
    main()
