"""CLI sub-command: compare two log files for regressions."""

import argparse
import sys

from reqtrace.storage import LogStorage
from reqtrace.comparator import compare_record_sets, format_comparison_report


def build_compare_parser(subparsers=None) -> argparse.ArgumentParser:
    description = "Compare a baseline log against a current log to detect regressions."
    if subparsers is not None:
        parser = subparsers.add_parser("compare", help=description)
    else:
        parser = argparse.ArgumentParser(prog="reqtrace compare", description=description)

    parser.add_argument(
        "baseline",
        help="Path to the baseline log file (JSON).",
    )
    parser.add_argument(
        "current",
        help="Path to the current log file (JSON).",
    )
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        default=False,
        help="Exit with code 1 if any regressions are detected.",
    )
    return parser


def run_compare(args: argparse.Namespace) -> int:
    """Execute the compare command. Returns an exit code."""
    baseline_storage = LogStorage(args.baseline)
    current_storage = LogStorage(args.current)

    baseline_records = baseline_storage.load_all()
    current_records = current_storage.load_all()

    if not baseline_records:
        print(f"[warn] No records found in baseline: {args.baseline}", file=sys.stderr)

    if not current_records:
        print(f"[warn] No records found in current: {args.current}", file=sys.stderr)

    report = compare_record_sets(baseline_records, current_records)
    print(format_comparison_report(report))

    if args.fail_on_regression and report.regression_count > 0:
        return 1
    return 0


def main(argv=None) -> None:
    parser = build_compare_parser()
    args = parser.parse_args(argv)
    sys.exit(run_compare(args))


if __name__ == "__main__":  # pragma: no cover
    main()
