"""Silencer: temporarily suppress alerts for specific metrics or sources."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from pipewatch.metrics import MetricResult


@dataclass
class SilenceRule:
    """A rule that suppresses alerts matching a source and/or metric name."""

    source: Optional[str] = None
    metric_name: Optional[str] = None
    expires_at: Optional[float] = None  # Unix timestamp; None = never expires
    reason: str = ""

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def matches(self, result: MetricResult) -> bool:
        if self.is_expired():
            return False
        if self.source is not None and result.source != self.source:
            return False
        if self.metric_name is not None and result.metric.name != self.metric_name:
            return False
        return True

    def __str__(self) -> str:
        parts = []
        if self.source:
            parts.append(f"source={self.source!r}")
        if self.metric_name:
            parts.append(f"metric={self.metric_name!r}")
        expiry = (
            f"expires={self.expires_at:.0f}" if self.expires_at else "no-expiry"
        )
        parts.append(expiry)
        if self.reason:
            parts.append(f"reason={self.reason!r}")
        return f"SilenceRule({', '.join(parts)})"


class Silencer:
    """Manages a collection of silence rules and tests results against them."""

    def __init__(self) -> None:
        self._rules: list[SilenceRule] = []

    def add_rule(self, rule: SilenceRule) -> None:
        """Register a new silence rule."""
        self._rules.append(rule)

    def is_silenced(self, result: MetricResult) -> bool:
        """Return True if *result* is covered by any active silence rule."""
        self._purge_expired()
        return any(rule.matches(result) for rule in self._rules)

    def active_rules(self) -> list[SilenceRule]:
        """Return all non-expired rules."""
        self._purge_expired()
        return list(self._rules)

    def clear(self) -> None:
        """Remove all rules, including non-expired ones."""
        self._rules.clear()

    def _purge_expired(self) -> None:
        self._rules = [r for r in self._rules if not r.is_expired()]

    def __len__(self) -> int:
        self._purge_expired()
        return len(self._rules)
