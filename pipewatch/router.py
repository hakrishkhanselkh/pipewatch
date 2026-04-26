"""Route MetricResults to different alert channels based on configurable rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from pipewatch.metrics import MetricResult, MetricStatus
from pipewatch.alerts import AlertChannel, AlertEvent


@dataclass
class RoutingRule:
    """A single routing rule mapping a predicate to one or more channels."""

    name: str
    predicate: Callable[[MetricResult], bool]
    channels: List[AlertChannel]

    def matches(self, result: MetricResult) -> bool:
        return self.predicate(result)

    def dispatch(self, result: MetricResult) -> None:
        event = AlertEvent(
            source=result.metric.source,
            metric_name=result.metric.name,
            status=result.status,
            value=result.value,
            message=f"Routed alert: {result.metric.name} is {result.status.value}",
        )
        for channel in self.channels:
            channel.send(event)


class ResultRouter:
    """Routes MetricResults to channels based on ordered routing rules."""

    def __init__(self, fallthrough: bool = True) -> None:
        """Args:
            fallthrough: if True, a result may match multiple rules;
                         if False, routing stops after the first match.
        """
        self._rules: List[RoutingRule] = []
        self.fallthrough = fallthrough

    def add_rule(self, rule: RoutingRule) -> None:
        """Register a routing rule (evaluated in insertion order)."""
        self._rules.append(rule)

    def route(self, result: MetricResult) -> int:
        """Dispatch *result* to all matching channels.

        Returns:
            Number of rules that matched.
        """
        matched = 0
        for rule in self._rules:
            if rule.matches(result):
                rule.dispatch(result)
                matched += 1
                if not self.fallthrough:
                    break
        return matched

    def route_many(self, results: List[MetricResult]) -> int:
        """Route a collection of results; returns total match count."""
        return sum(self.route(r) for r in results)

    @staticmethod
    def status_predicate(*statuses: MetricStatus) -> Callable[[MetricResult], bool]:
        """Helper: build a predicate that matches any of the given statuses."""
        status_set = set(statuses)
        return lambda r: r.status in status_set

    @staticmethod
    def source_predicate(source: str) -> Callable[[MetricResult], bool]:
        """Helper: build a predicate that matches a specific source name."""
        return lambda r: r.metric.source == source
