"""CLI entry point for running pipewatch on a schedule."""

import argparse
import logging
import signal
import sys
import time

from pipewatch.collector import MetricCollector
from pipewatch.alerts import AlertManager, LogAlertChannel
from pipewatch.runner import PipelineRunner
from pipewatch.scheduler import ScheduledRunner

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run pipewatch metric collection on a schedule."
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=60.0,
        metavar="SECONDS",
        help="Collection interval in seconds (default: 60).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO).",
    )
    return parser


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    collector = MetricCollector()
    alert_manager = AlertManager(channels=[LogAlertChannel()])
    runner = PipelineRunner(collector=collector, alert_manager=alert_manager)
    scheduled = ScheduledRunner(runner=runner, interval_seconds=args.interval)

    def _handle_signal(sig, frame):
        print("\nShutting down pipewatch scheduler…", file=sys.stderr)
        scheduled.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    scheduled.start()
    logger.info("pipewatch scheduler running. Press Ctrl+C to stop.")

    # Keep main thread alive
    while scheduled.is_running:
        time.sleep(1)


if __name__ == "__main__":  # pragma: no cover
    main()
