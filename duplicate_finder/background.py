"""Run blocking work off the Tk thread and hand results back safely.

Tkinter is not thread-safe: widgets may only be touched from the main thread.
The worker therefore only puts messages on a queue, and the main thread
drains that queue with ``after()``. Scanning and removal both use this one
class, so the threading logic is written once.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from typing import Any, Callable

from .errors import OperationCancelled
from .progress import ProgressCallback, Stage

POLL_INTERVAL_MS = 100

Work = Callable[[ProgressCallback, threading.Event], Any]


class BackgroundTask:
    def __init__(
        self,
        root: tk.Misc,
        work: Work,
        *,
        on_progress: Callable[[Stage, int, int], None],
        on_success: Callable[[Any], None],
        on_error: Callable[[BaseException], None],
        on_cancelled: Callable[[], None],
    ) -> None:
        self._root = root
        self._work = work
        self._handlers = {
            "progress": lambda payload: on_progress(*payload),
            "success": on_success,
            "error": on_error,
            "cancelled": lambda _payload: on_cancelled(),
        }
        self._messages: queue.Queue = queue.Queue()
        self._cancel_event = threading.Event()
        self._finished = False

    def start(self) -> None:
        threading.Thread(target=self._run, daemon=True).start()
        self._root.after(POLL_INTERVAL_MS, self._poll)

    def cancel(self) -> None:
        self._cancel_event.set()

    def _run(self) -> None:
        def report(stage: Stage, done: int, total: int) -> None:
            self._messages.put(("progress", (stage, done, total)))

        try:
            result = self._work(report, self._cancel_event)
            self._messages.put(("success", result))
        except OperationCancelled:
            self._messages.put(("cancelled", None))
        except Exception as exc:  # surfaced to the user, never swallowed
            self._messages.put(("error", exc))

    def _poll(self) -> None:
        try:
            while True:
                kind, payload = self._messages.get_nowait()
                if kind != "progress":
                    self._finished = True
                self._handlers[kind](payload)
        except queue.Empty:
            pass
        if not self._finished:
            self._root.after(POLL_INTERVAL_MS, self._poll)
