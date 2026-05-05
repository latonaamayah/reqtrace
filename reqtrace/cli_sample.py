"""CLI sub-command: sample — down-sample a request log and write the result."""

from __future__ import annotations

import argparse
import sys

from reqtrace.filter import RecordFilter
from reqtrace.sampler import Sampler, SamplerConfig
from reqtrace.storage import LogStorage


def build_sample_parser(parent: argparse._SubParsersAction = None) -> argparse.ArgumentParser:  # type: ignore[type-arg]
    description = "Down-sample a request log and write the surviving records to an output file."
    if parent is not None:
        parser = parent.add_parser("sample", help=description)
    else:
        parser = argparse.ArgumentParser(prog="reqtrace-sample", description=description)

    parser.add_argument("input", help="Path to source log file")
    parser.add_argument("output", help="Path to destination log file")
    parser.add_argument(
        "--rate",
        type=float,
        default=0.5,
        metavar="RATE",
        help="Fraction of records to keep (0.0–1.0, default: 0.5)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        metavar="SEED",
        help="Random seed for deterministic sampling",
    )
    parser.add_argument("--method", default=None, help="Keep only records with this HTTP method")
    parser.add_argument("--status", type=int, default=None, help="Keep only records with this status code")
    return parser


def run_sample(args: argparse.Namespace) -> int:
    src = LogStorage(args.input)
    records = src.load_all()

    # Optional pre-filter before sampling
    rf = RecordFilter(method=args.method, status_code=args.status)
    records = rf.apply(records)

    try:
        config = SamplerConfig(rate=args.rate, seed=args.seed)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    sampler = Sampler(config)
    kept = sampler.apply(records)

    dst = LogStorage(args.output)
    for record in kept:
        dst.save(record)

    print(f"Sampled {len(kept)}/{len(records)} records → {args.output}")
    return 0


def main() -> None:  # pragma: no cover
    parser = build_sample_parser()
    sys.exit(run_sample(parser.parse_args()))


if __name__ == "__main__":  # pragma: no cover
    main()
