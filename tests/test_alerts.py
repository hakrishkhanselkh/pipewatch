"""Tests for the alert manager and channels."""

import pytest
from pipewatch.metrics import Metric, MetricResult, MetricStatus
from pipewatch.alerts import (
    AlertEvent,
    AlertManager,
    CallbackAlertChannel,
    LogAlertChannel,
)


def make_result(name: str, value: float, status: MetricStatus, message: str = "") -> MetricResult:
    metric = Metric(name=name, source="test_source")
    return MetricResult(metric=metric, value=value, status=status, message=message)


def test_alert_event_str():
    metric = Metric(name="row_count", source="db")
    event = AlertEvent(
        source="db",
        metric_name="row_count",
        status=MetricStatus.CRITICAL,
        value=0.0,
        message="below threshold",
    )
    text = str(event)
    assert "CRITICAL" in text
    assert "row_count" in text
    assert "below threshold" in text


def test_callback_channel_receives_event():
    received = []
    channel = CallbackAlertChannel(callback=received.append)
    metric = Metric(name="latency", source="api")
    event = AlertEvent(
        source="api",
        metric_name="latency",
        status=MetricStatus.WARNING,
        value=3.5,
        message="high latency",
    )
    channel.send(event)
    assert len(received) == 1
    assert received[0].metric_name == "latency"


def test_alert_manager_fires_on_warning_and_critical():
    received = []
    manager = AlertManager(channels=[CallbackAlertChannel(received.append)])
    results = [
        make_result("ok_metric", 10.0, MetricStatus.OK),
        make_result("warn_metric", 5.0, MetricStatus.WARNING, "slightly off"),
        make_result("crit_metric", 0.0, MetricStatus.CRITICAL, "totally broken"),
    ]
    manager.process("pipeline_a", results)
    assert len(received) == 2
    statuses = {e.status for e in received}
    assert MetricStatus.WARNING in statuses
    assert MetricStatus.CRITICAL in statuses


def test_alert_manager_skips_ok_by_default():
    received = []
    manager = AlertManager(channels=[CallbackAlertChannel(received.append)])
    results = [make_result("healthy", 99.0, MetricStatus.OK)]
    manager.process("src", results)
    assert received == []


def test_alert_manager_custom_notify_on():
    received = []
    manager = AlertManager(
        channels=[CallbackAlertChannel(received.append)],
        notify_on=[MetricStatus.OK],
    )
    results = [
        make_result("healthy", 99.0, MetricStatus.OK),
        make_result("broken", 0.0, MetricStatus.CRITICAL),
    ]
    manager.process("src", results)
    assert len(received) == 1
    assert received[0].status == MetricStatus.OK


def test_alert_manager_add_channel():
    received_a, received_b = [], []
    manager = AlertManager(channels=[CallbackAlertChannel(received_a.append)])
    manager.add_channel(CallbackAlertChannel(received_b.append))
    results = [make_result("m", 1.0, MetricStatus.CRITICAL)]
    manager.process("src", results)
    assert len(received_a) == 1
    assert len(received_b) == 1
