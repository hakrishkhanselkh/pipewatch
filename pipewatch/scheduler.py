"""Scheduler for periodic pipeline metric collection and alerting."""

import time
import logging
import threading
from typing import Optional, Callable

from pipewatch.runner import PipelineRunner

logger = logging.getLogger(__name__)


class ScheduledRunner:
    """Runs a PipelineRunner on a fixed interval in a background thread."""

    def __init__(
        self,
        runner: PipelineRunner,
        interval_seconds: float,
        on_tick: Optional[Callable] = None,
    ):
        self.runner = runner
        self.interval = interval_seconds
        self.on_tick = on_tick
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.tick_count = 0

    def start(self) -> None:
        """Start the background scheduling thread."""
        if self._thread and self._thread.is_alive():
            raise RuntimeError("ScheduledRunner is already running.")
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("ScheduledRunner started (interval=%.1fs)", self.interval)

    def stop(self, timeout: float = 5.0) -> None:
        """Signal the runner to stop and wait for the thread to finish."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)
        logger.info("ScheduledRunner stopped after %d tick(s).", self.tick_count)

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                results = self.runner.run_and_report()
                self.tick_count += 1
                if self.on_tick:
                    self.on_tick(results)
            except Exception as exc:  # pragma: no cover
                logger.error("Error during scheduled tick: %s", exc)
            self._stop_event.wait(timeout=self.interval)

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
