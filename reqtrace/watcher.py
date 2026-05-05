"""File-based watcher that monitors the log storage and triggers callbacks on new records."""

import time
import threading
from typing import Callable, Optional

from reqtrace.storage import LogStorage, RequestRecord


class StorageWatcher:
    """Watches a LogStorage file for new records and invokes a callback."""

    def __init__(
        self,
        storage: LogStorage,
        on_new_record: Callable[[RequestRecord], None],
        poll_interval: float = 1.0,
    ) -> None:
        self.storage = storage
        self.on_new_record = on_new_record
        self.poll_interval = poll_interval
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._seen_ids: set = set()

    def _scan(self) -> None:
        try:
            records = self.storage.load_all()
        except Exception:
            return
        for record in records:
            if record.id not in self._seen_ids:
                self._seen_ids.add(record.id)
                try:
                    self.on_new_record(record)
                except Exception:
                    pass

    def _run(self) -> None:
        # Populate initial seen set without triggering callbacks
        try:
            for record in self.storage.load_all():
                self._seen_ids.add(record.id)
        except Exception:
            pass

        while not self._stop_event.is_set():
            self._scan()
            self._stop_event.wait(self.poll_interval)

    def start(self) -> None:
        """Start watching in a background thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        """Stop the background watcher thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)
            self._thread = None

    def __enter__(self) -> "StorageWatcher":
        self.start()
        return self

    def __exit__(self, *args) -> None:
        self.stop()
