"""Tests for pipewatch.scheduler.ScheduledRunner."""

import time
import threading
from unittest.mock import MagicMock, patch

import pytest

from pipewatch.scheduler import ScheduledRunner


def make_runner(results=None):
    runner = MagicMock()
    runner.run_and_report.return_value = results or []
    return runner


def test_starts_and_stops_cleanly():
    runner = make_runner()
    sr = ScheduledRunner(runner=runner, interval_seconds=10)
    sr.start()
    assert sr.is_running
    sr.stop(timeout=2)
    assert not sr.is_running


def test_raises_if_started_twice():
    runner = make_runner()
    sr = ScheduledRunner(runner=runner, interval_seconds=10)
    sr.start()
    try:
        with pytest.raises(RuntimeError, match="already running"):
            sr.start()
    finally:
        sr.stop()


def test_on_tick_callback_called():
    ticks = []
    fake_results = [object()]
    runner = make_runner(results=fake_results)

    sr = ScheduledRunner(
        runner=runner,
        interval_seconds=0.05,
        on_tick=lambda results: ticks.append(results),
    )
    sr.start()
    time.sleep(0.2)
    sr.stop()

    assert len(ticks) >= 1
    assert ticks[0] is fake_results


def test_tick_count_increments():
    runner = make_runner()
    sr = ScheduledRunner(runner=runner, interval_seconds=0.05)
    sr.start()
    time.sleep(0.22)
    sr.stop()
    assert sr.tick_count >= 2


def test_runner_called_on_each_tick():
    runner = make_runner()
    sr = ScheduledRunner(runner=runner, interval_seconds=0.05)
    sr.start()
    time.sleep(0.18)
    sr.stop()
    assert runner.run_and_report.call_count >= 2


def test_is_running_false_before_start():
    runner = make_runner()
    sr = ScheduledRunner(runner=runner, interval_seconds=5)
    assert not sr.is_running
