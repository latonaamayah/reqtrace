"""CLI entry point for the highlighter: print records with matching rules emphasized."""
from __future__ import annotations

import argparse
import sys
from typing import List

from reqtrace.storage import LogStorage
from reqtrace.highlighter import HighlightRule, Highlighter
from reqtrace.formatter import format_record

RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"

_BUILTIN_RULES: List[HighlightRule] = [
    HighlightRule("server-error", RED, lambda r: r.status_code >= 500),
    HighlightRule("client-error", YELLOW, lambda r: 400 <= r.status_code < 500),
    HighlightRule("slow", CYAN, lambda r: r.duration_ms > 1000),
]


def build_highlight_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reqtrace highlight",
        description="Print logged requests with highlighted anomalies.",
    )
    parser.add_argument("log_file", help="Path to the reqtrace log file.")
    parser.add_argument(
        "--only-highlighted",
        action="store_true",
        default=False,
        help="Print only records that match a highlight rule.",
    )
    parser.add_argument(
        "--show-headers",
        action="store_true",
        default=False,
        help="Include request/response headers in output.",
    )
    return parser


def run_highlight(args: argparse.Namespace) -> int:
    storage = LogStorage(args.log_file)
    records = storage.load_all()

    if not records:
        print("No records found.", file=sys.stderr)
        return 0

    highlighter = Highlighter()
    for rule in _BUILTIN_RULES:
        highlighter.add_rule(rule)

    results = (
        highlighter.highlighted_only(records)
        if args.only_highlighted
        else highlighter.highlight_all(records)
    )

    for result in results:
        label = result.format_label()
        prefix = f"{label} " if label else ""
        line = format_record(result.record, show_headers=args.show_headers)
        print(f"{prefix}{line}")

    highlighted_count = sum(1 for r in results if r.is_highlighted)
    print(
        f"\n{len(results)} record(s) shown, {highlighted_count} highlighted.",
        file=sys.stderr,
    )
    return 0


def main() -> None:
    parser = build_highlight_parser()
    args = parser.parse_args()
    sys.exit(run_highlight(args))


if __name__ == "__main__":
    main()
