"""Tests for pipewatch.notifier."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from pipewatch.alerts import AlertEvent, AlertManager
from pipewatch.metrics import Metric, MetricResult, MetricStatus
from pipewatch.notifier import Notifier, NotifierConfig


def make_result(
    source: str = "src",
    name: str = "lag",
    status: MetricStatus = MetricStatus.WARNING,
    value: float = 5.0,
) -> MetricResult:
    metric = Metric(name=name, source=source, value=value)
    return MetricResult(metric=metric, status=status)


def make_notifier(cooldown: float = 60.0, max_repeats: int = 0) -> tuple:
    manager = MagicMock(spec=AlertManager)
    cfg = NotifierConfig(cooldown_seconds=cooldown, max_repeats=max_repeats)
    notifier = Notifier(manager, cfg)
    return notifier, manager


# ---------------------------------------------------------------------------
# Basic forwarding
# ---------------------------------------------------------------------------

def test_first_alert_is_forwarded():
    notifier, manager = make_notifier()
    event = AlertEvent(result=make_result())
    assert notifier.process(event) is True
    manager.handle.assert_called_once_with(event)


def test_second_alert_suppressed_within_cooldown():
    notifier, manager = make_notifier(cooldown=300.0)
    event = AlertEvent(result=make_result())
    notifier.process(event)
    result = notifier.process(event)
    assert result is False
    assert manager.handle.call_count == 1


def test_alert_forwarded_after_cooldown_expires():
    notifier, manager = make_notifier(cooldown=0.05)
    event = AlertEvent(result=make_result())
    notifier.process(event)
    time.sleep(0.1)
    result = notifier.process(event)
    assert result is True
    assert manager.handle.call_count == 2


# ---------------------------------------------------------------------------
# max_repeats
# ---------------------------------------------------------------------------

def test_max_repeats_caps_forwarding():
    notifier, manager = make_notifier(cooldown=0.0, max_repeats=2)
    event = AlertEvent(result=make_result())
    results = [notifier.process(event) for _ in range(4)]
    assert results == [True, True, False, False]
    assert manager.handle.call_count == 2


def test_zero_max_repeats_means_unlimited():
    notifier, manager = make_notifier(cooldown=0.0, max_repeats=0)
    event = AlertEvent(result=make_result())
    for _ in range(5):
        notifier.process(event)
    assert manager.handle.call_count == 5


# ---------------------------------------------------------------------------
# reset helpers
# ---------------------------------------------------------------------------

def test_reset_clears_cooldown_for_pair():
    notifier, manager = make_notifier(cooldown=300.0)
    event = AlertEvent(result=make_result(source="s", name="n"))
    notifier.process(event)
    notifier.reset("s", "n")
    result = notifier.process(event)
    assert result is True


def test_reset_all_clears_everything():
    notifier, manager = make_notifier(cooldown=300.0)
    for name in ("a", "b", "c"):
        notifier.process(AlertEvent(result=make_result(name=name)))
    notifier.reset_all()
    for name in ("a", "b", "c"):
        assert notifier.process(AlertEvent(result=make_result(name=name))) is True


def test_different_statuses_tracked_independently():
    notifier, manager = make_notifier(cooldown=300.0)
    warn_event = AlertEvent(result=make_result(status=MetricStatus.WARNING))
    crit_event = AlertEvent(result=make_result(status=MetricStatus.CRITICAL))
    notifier.process(warn_event)
    result = notifier.process(crit_event)
    assert result is True
    assert manager.handle.call_count == 2
