"""CLI entry-point for labeling stored request records."""
from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from reqtrace.storage import LogStorage
from reqtrace.labeler import Labeler, LabelRule, default_labeler


def build_label_parser(parent: Optional[argparse._SubParsersAction] = None) -> argparse.ArgumentParser:
    description = "Label request records using built-in or custom rules."
    if parent is not None:
        parser = parent.add_parser("label", help=description)
    else:
        parser = argparse.ArgumentParser(prog="reqtrace-label", description=description)

    parser.add_argument("log_file", help="Path to the request log (JSON-lines file).")
    parser.add_argument(
        "--output",
        choices=["summary", "json"],
        default="summary",
        help="Output format (default: summary).",
    )
    parser.add_argument(
        "--slow-threshold",
        type=float,
        default=1000.0,
        metavar="MS",
        help="Duration threshold in ms for the 'slow' label (default: 1000).",
    )
    return parser


def run_label(args: argparse.Namespace) -> int:
    storage = LogStorage(args.log_file)
    records = storage.load_all()

    if not records:
        print("No records found.")
        return 0

    labeler = default_labeler()
    # Override slow threshold if provided
    labeler._rules = [
        r if r.label != "slow" else LabelRule("slow", lambda rec, t=args.slow_threshold: rec.duration_ms > t, f"duration > {args.slow_threshold}ms")
        for r in labeler._rules
    ]

    result = labeler.label_all(records)

    if args.output == "json":
        payload = {
            "label_counts": result.label_counts,
            "total_labeled": result.total_labeled(),
            "records": [
                {"id": rec.id, "labels": result.labeled.get(rec.id, [])}
                for rec in records
            ],
        }
        print(json.dumps(payload, indent=2))
    else:
        print(str(result))

    return 0


def main() -> None:
    parser = build_label_parser()
    args = parser.parse_args()
    sys.exit(run_label(args))


if __name__ == "__main__":
    main()
