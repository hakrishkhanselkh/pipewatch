"""Notification rate-limiting and deduplication for alert events."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from pipewatch.alerts import AlertEvent, AlertManager
from pipewatch.metrics import MetricStatus


@dataclass
class NotifierConfig:
    """Configuration for the Notifier."""
    cooldown_seconds: float = 300.0   # minimum seconds between repeated alerts
    max_repeats: int = 0              # 0 = unlimited; >0 caps repeated fires


@dataclass
class _AlertState:
    last_fired: float = 0.0
    repeat_count: int = 0


class Notifier:
    """Wraps an AlertManager and suppresses duplicate / too-frequent alerts.

    A (source, name, status) triplet is used as the deduplication key.
    Once the status changes the cooldown resets.
    """

    def __init__(
        self,
        manager: AlertManager,
        config: Optional[NotifierConfig] = None,
    ) -> None:
        self._manager = manager
        self._config = config or NotifierConfig()
        self._state: Dict[Tuple[str, str, MetricStatus], _AlertState] = {}

    def _make_key(
        self, event: AlertEvent
    ) -> Tuple[str, str, MetricStatus]:
        r = event.result
        return (r.source, r.name, r.status)

    def process(self, event: AlertEvent) -> bool:
        """Evaluate the event and fire via the manager if allowed.

        Returns True if the alert was forwarded, False if suppressed.
        """
        key = self._make_key(event)
        now = time.monotonic()
        state = self._state.get(key)

        if state is None:
            state = _AlertState()
            self._state[key] = state

        elapsed = now - state.last_fired
        if elapsed < self._config.cooldown_seconds and state.repeat_count > 0:
            return False

        if (
            self._config.max_repeats > 0
            and state.repeat_count >= self._config.max_repeats
        ):
            return False

        self._manager.handle(event)
        state.last_fired = now
        state.repeat_count += 1
        return True

    def reset(self, source: str, name: str) -> None:
        """Clear all cooldown state for a given (source, name) pair."""
        keys_to_remove = [
            k for k in self._state if k[0] == source and k[1] == name
        ]
        for k in keys_to_remove:
            del self._state[k]

    def reset_all(self) -> None:
        """Clear all tracked state."""
        self._state.clear()
