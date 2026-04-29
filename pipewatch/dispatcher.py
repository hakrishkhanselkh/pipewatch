"""Result dispatcher: fan-out MetricResults to multiple handlers in one pass."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List

from pipewatch.metrics import MetricResult


Handler = Callable[[MetricResult], None]


@dataclass
class DispatchReport:
    """Summary produced after a single dispatch run."""

    total: int = 0
    handler_count: int = 0
    errors: List[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    def __str__(self) -> str:
        status = "OK" if self.success else f"{len(self.errors)} error(s)"
        return (
            f"DispatchReport(total={self.total}, "
            f"handlers={self.handler_count}, status={status})"
        )


class ResultDispatcher:
    """Fan-out a list of MetricResults to one or more registered handlers.

    Each handler is a plain callable that accepts a single MetricResult.
    Errors raised by individual handlers are captured and included in the
    DispatchReport rather than propagating, so all handlers always run.
    """

    def __init__(self) -> None:
        self._handlers: List[tuple[str, Handler]] = []

    def register(self, name: str, handler: Handler) -> None:
        """Register a named handler."""
        if not callable(handler):
            raise TypeError(f"handler '{name}' must be callable")
        self._handlers.append((name, handler))

    def unregister(self, name: str) -> bool:
        """Remove a handler by name.  Returns True if it was found."""
        before = len(self._handlers)
        self._handlers = [(n, h) for n, h in self._handlers if n != name]
        return len(self._handlers) < before

    @property
    def handler_names(self) -> List[str]:
        return [n for n, _ in self._handlers]

    def dispatch(self, results: List[MetricResult]) -> DispatchReport:
        """Send every result to every registered handler."""
        report = DispatchReport(total=len(results), handler_count=len(self._handlers))
        for result in results:
            for name, handler in self._handlers:
                try:
                    handler(result)
                except Exception as exc:  # noqa: BLE001
                    report.errors.append(f"[{name}] {type(exc).__name__}: {exc}")
        return report
