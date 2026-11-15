"""Progress reporting and cancellation shared by every long-running operation."""

from __future__ import annotations

import threading
import time
from enum import Enum
from typing import Callable, Optional

from .errors import OperationCancelled


class Stage(Enum):
    COLLECTING = "collecting"
    PARTIAL_HASH = "partial_hash"
    FULL_HASH = "full_hash"
    REMOVING = "removing"


# (stage, done, total); total == 0 means "unknown".
ProgressCallback = Callable[[Stage, int, int], None]


class ProgressReporter:
    """Throttles progress callbacks and exposes a single cancellation check.

    Throttling keeps a scan of a million files from flooding the GUI queue.
    """

    def __init__(
        self,
        callback: Optional[ProgressCallback] = None,
        cancel_event: Optional[threading.Event] = None,
        min_interval: float = 0.1,
    ) -> None:
        self._callback = callback
        self._cancel_event = cancel_event
        self._min_interval = min_interval
        self._last_report = 0.0

    def check_cancelled(self) -> None:
        if self._cancel_event is not None and self._cancel_event.is_set():
            raise OperationCancelled()

    def report(self, stage: Stage, done: int, total: int = 0) -> None:
        if self._callback is None:
            return
        now = time.monotonic()
        is_final = total > 0 and done >= total
        if is_final or now - self._last_report >= self._min_interval:
            self._last_report = now
            self._callback(stage, done, total)
