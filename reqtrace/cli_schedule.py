"""CLI entry-point for scheduled replay."""
from __future__ import annotations

import argparse
import signal
import sys
from typing import List

from reqtrace.replayer import ReplayResult
from reqtrace.scheduler import Scheduler, SchedulerConfig
from reqtrace.storage import LogStorage


def build_schedule_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="reqtrace-schedule",
        description="Replay stored requests on a fixed interval.",
    )
    p.add_argument("--log-file", required=True, help="Path to the reqtrace log file.")
    p.add_argument("--target", required=True, help="Base URL of the target service.")
    p.add_argument(
        "--interval",
        type=float,
        default=60.0,
        help="Seconds between replay runs (default: 60).",
    )
    p.add_argument(
        "--max-runs",
        type=int,
        default=None,
        help="Stop after N runs (default: run until interrupted).",
    )
    p.add_argument("--verbose", action="store_true", help="Print each replay result.")
    return p


def _print_results(results: List[ReplayResult], verbose: bool) -> None:
    ok = sum(1 for r in results if r.status_code and r.status_code < 400)
    fail = len(results) - ok
    print(f"  Replayed {len(results)} request(s): {ok} ok, {fail} failed.")
    if verbose:
        for r in results:
            status = r.status_code or "ERR"
            err = f" [{r.error}]" if r.error else ""
            print(f"    {r.record.method} {r.record.path} -> {status}{err}")


def run_schedule(args: argparse.Namespace) -> None:
    storage = LogStorage(args.log_file)
    verbose: bool = args.verbose

    def on_results(results: List[ReplayResult]) -> None:
        print(f"[reqtrace-schedule] run #{scheduler.run_count}")
        _print_results(results, verbose)

    config = SchedulerConfig(
        interval_seconds=args.interval,
        max_runs=args.max_runs,
        on_results=on_results,
    )
    scheduler = Scheduler(storage, args.target, config)

    def _handle_signal(sig, frame):  # noqa: ANN001
        print("\n[reqtrace-schedule] stopping…")
        scheduler.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    print(f"[reqtrace-schedule] starting — interval={args.interval}s target={args.target}")
    scheduler.start()
    scheduler._thread.join()  # type: ignore[union-attr]


def main() -> None:
    run_schedule(build_schedule_parser().parse_args())


if __name__ == "__main__":
    main()
