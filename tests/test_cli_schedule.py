"""Tests for pipewatch.cli_schedule argument parsing and wiring."""

from unittest.mock import MagicMock, patch

import pytest

from pipewatch.cli_schedule import build_parser, main


def test_default_interval():
    parser = build_parser()
    args = parser.parse_args([])
    assert args.interval == 60.0


def test_custom_interval():
    parser = build_parser()
    args = parser.parse_args(["--interval", "30"])
    assert args.interval == 30.0


def test_default_log_level():
    parser = build_parser()
    args = parser.parse_args([])
    assert args.log_level == "INFO"


def test_custom_log_level():
    parser = build_parser()
    args = parser.parse_args(["--log-level", "DEBUG"])
    assert args.log_level == "DEBUG"


def test_invalid_log_level_exits():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--log-level", "VERBOSE"])


@patch("pipewatch.cli_schedule.ScheduledRunner")
@patch("pipewatch.cli_schedule.PipelineRunner")
@patch("pipewatch.cli_schedule.AlertManager")
@patch("pipewatch.cli_schedule.MetricCollector")
def test_main_starts_and_stops(mock_collector, mock_alert, mock_runner, mock_sched):
    """main() should start the scheduler; simulate immediate stop via is_running."""
    instance = MagicMock()
    # is_running returns True once then False to exit the loop
    instance.is_running.__bool__ = MagicMock(side_effect=[True, False])
    mock_sched.return_value = instance

    import signal as _signal
    with patch("signal.signal"):
        main(["--interval", "5", "--log-level", "WARNING"])

    instance.start.assert_called_once()
