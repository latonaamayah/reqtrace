"""Scheduled replay: run stored requests on a cron-like interval."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from reqtrace.replayer import ReplayResult, Replayer
from reqtrace.storage import LogStorage


@dataclass
class SchedulerConfig:
    interval_seconds: float = 60.0
    max_runs: Optional[int] = None  # None = run forever
    on_results: Optional[Callable[[List[ReplayResult]], None]] = None

    def __post_init__(self) -> None:
        if self.interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")


class Scheduler:
    """Replay all stored requests repeatedly on a fixed interval."""

    def __init__(self, storage: LogStorage, target_base_url: str, config: SchedulerConfig) -> None:
        self._storage = storage
        self._target_base_url = target_base_url
        self._config = config
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.run_count: int = 0
        self.last_results: List[ReplayResult] = []

    def _run_once(self) -> List[ReplayResult]:
        replayer = Replayer(self._storage, self._target_base_url)
        results = replayer.replay_all()
        self.last_results = results
        self.run_count += 1
        if self._config.on_results:
            self._config.on_results(results)
        return results

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            self._run_once()
            if self._config.max_runs is not None and self.run_count >= self._config.max_runs:
                break
            self._stop_event.wait(timeout=self._config.interval_seconds)

    def start(self) -> None:
        """Start the scheduler in a background thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Signal the scheduler to stop and wait for the thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def run_once_sync(self) -> List[ReplayResult]:
        """Run a single replay cycle synchronously (useful for testing)."""
        return self._run_once()
