"""Tests for pipewatch.router."""

import pytest
from pipewatch.metrics import Metric, MetricResult, MetricStatus
from pipewatch.alerts import AlertEvent, AlertChannel
from pipewatch.router import RoutingRule, ResultRouter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_result(
    name: str = "latency",
    source: str = "db",
    status: MetricStatus = MetricStatus.OK,
    value: float = 1.0,
) -> MetricResult:
    metric = Metric(name=name, source=source, value=value)
    return MetricResult(metric=metric, status=status, value=value)


class CapturingChannel(AlertChannel):
    def __init__(self):
        self.received: list[AlertEvent] = []

    def send(self, event: AlertEvent) -> None:
        self.received.append(event)


# ---------------------------------------------------------------------------
# RoutingRule
# ---------------------------------------------------------------------------

def test_routing_rule_matches_predicate():
    rule = RoutingRule(
        name="critical-only",
        predicate=ResultRouter.status_predicate(MetricStatus.CRITICAL),
        channels=[],
    )
    assert rule.matches(make_result(status=MetricStatus.CRITICAL))
    assert not rule.matches(make_result(status=MetricStatus.OK))


def test_routing_rule_dispatches_to_channel():
    ch = CapturingChannel()
    rule = RoutingRule(
        name="warn-rule",
        predicate=ResultRouter.status_predicate(MetricStatus.WARNING),
        channels=[ch],
    )
    result = make_result(status=MetricStatus.WARNING, value=95.0)
    rule.dispatch(result)
    assert len(ch.received) == 1
    assert ch.received[0].status == MetricStatus.WARNING


# ---------------------------------------------------------------------------
# ResultRouter — fallthrough=True (default)
# ---------------------------------------------------------------------------

def test_router_returns_zero_when_no_rules():
    router = ResultRouter()
    assert router.route(make_result()) == 0


def test_router_matches_single_rule():
    ch = CapturingChannel()
    router = ResultRouter()
    router.add_rule(RoutingRule(
        name="critical",
        predicate=ResultRouter.status_predicate(MetricStatus.CRITICAL),
        channels=[ch],
    ))
    assert router.route(make_result(status=MetricStatus.CRITICAL)) == 1
    assert len(ch.received) == 1


def test_router_fallthrough_matches_multiple_rules():
    ch1, ch2 = CapturingChannel(), CapturingChannel()
    router = ResultRouter(fallthrough=True)
    router.add_rule(RoutingRule(
        name="any-non-ok",
        predicate=ResultRouter.status_predicate(MetricStatus.WARNING, MetricStatus.CRITICAL),
        channels=[ch1],
    ))
    router.add_rule(RoutingRule(
        name="critical-only",
        predicate=ResultRouter.status_predicate(MetricStatus.CRITICAL),
        channels=[ch2],
    ))
    matched = router.route(make_result(status=MetricStatus.CRITICAL))
    assert matched == 2
    assert len(ch1.received) == 1
    assert len(ch2.received) == 1


def test_router_no_fallthrough_stops_at_first_match():
    ch1, ch2 = CapturingChannel(), CapturingChannel()
    router = ResultRouter(fallthrough=False)
    router.add_rule(RoutingRule(
        name="first",
        predicate=ResultRouter.status_predicate(MetricStatus.CRITICAL),
        channels=[ch1],
    ))
    router.add_rule(RoutingRule(
        name="second",
        predicate=ResultRouter.status_predicate(MetricStatus.CRITICAL),
        channels=[ch2],
    ))
    matched = router.route(make_result(status=MetricStatus.CRITICAL))
    assert matched == 1
    assert len(ch1.received) == 1
    assert len(ch2.received) == 0


def test_router_source_predicate():
    ch = CapturingChannel()
    router = ResultRouter()
    router.add_rule(RoutingRule(
        name="db-source",
        predicate=ResultRouter.source_predicate("db"),
        channels=[ch],
    ))
    router.route(make_result(source="db"))
    router.route(make_result(source="api"))
    assert len(ch.received) == 1


def test_route_many_aggregates_counts():
    ch = CapturingChannel()
    router = ResultRouter()
    router.add_rule(RoutingRule(
        name="critical",
        predicate=ResultRouter.status_predicate(MetricStatus.CRITICAL),
        channels=[ch],
    ))
    results = [
        make_result(status=MetricStatus.CRITICAL),
        make_result(status=MetricStatus.OK),
        make_result(status=MetricStatus.CRITICAL),
    ]
    total = router.route_many(results)
    assert total == 2
    assert len(ch.received) == 2
