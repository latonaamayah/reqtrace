"""CLI entry-point for reqtrace validate command."""
from __future__ import annotations

import argparse
import sys

from reqtrace.storage import LogStorage
from reqtrace.filter import RecordFilter
from reqtrace.validator import (
    Validator,
    require_status_below_500,
    require_non_empty_path,
    require_duration_below,
)


def build_validate_parser(parent: argparse._SubParsersAction | None = None) -> argparse.ArgumentParser:  # type: ignore[type-arg]
    kwargs = dict(description="Validate logged requests against built-in rules.")
    parser = (
        parent.add_parser("validate", **kwargs)
        if parent
        else argparse.ArgumentParser(**kwargs)
    )
    parser.add_argument("log_file", help="Path to the reqtrace JSONL log file.")
    parser.add_argument("--method", help="Filter by HTTP method.")
    parser.add_argument("--path-prefix", dest="path_prefix", help="Filter by path prefix.")
    parser.add_argument(
        "--max-duration",
        dest="max_duration",
        type=float,
        default=None,
        help="Fail records slower than this many milliseconds.",
    )
    parser.add_argument(
        "--no-5xx",
        dest="no_5xx",
        action="store_true",
        default=True,
        help="Fail records with 5xx status (default: on).",
    )
    parser.add_argument(
        "--exit-nonzero",
        dest="exit_nonzero",
        action="store_true",
        help="Exit with code 1 if any validation errors are found.",
    )
    return parser


def run_validate(args: argparse.Namespace) -> int:
    storage = LogStorage(args.log_file)
    records = storage.load_all()

    f = RecordFilter(
        method=getattr(args, "method", None),
        path_prefix=getattr(args, "path_prefix", None),
    )
    records = f.apply(records)

    validator = Validator()
    if getattr(args, "no_5xx", True):
        validator.add_rule(require_status_below_500())
    validator.add_rule(require_non_empty_path())
    if getattr(args, "max_duration", None) is not None:
        validator.add_rule(require_duration_below(args.max_duration))

    result = validator.validate(records)
    print(str(result))

    if args.exit_nonzero and result.error_count > 0:
        return 1
    return 0


def main() -> None:  # pragma: no cover
    parser = build_validate_parser()
    args = parser.parse_args()
    sys.exit(run_validate(args))


if __name__ == "__main__":  # pragma: no cover
    main()
