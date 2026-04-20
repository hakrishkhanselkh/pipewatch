"""CLI entry-point: run pipeline checks and send rate-limited alerts."""

from __future__ import annotations

import argparse
import logging
import sys
from typing import List

from pipewatch.alerts import AlertEvent, AlertManager, LogAlertChannel
from pipewatch.collector import MetricCollector
from pipewatch.metrics import MetricStatus
from pipewatch.notifier import Notifier, NotifierConfig
from pipewatch.runner import PipelineRunner

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipewatch-notify",
        description="Run pipeline checks and fire rate-limited alerts.",
    )
    parser.add_argument(
        "--cooldown",
        type=float,
        default=300.0,
        metavar="SECONDS",
        help="Minimum seconds between repeated alerts for the same metric (default: 300).",
    )
    parser.add_argument(
        "--max-repeats",
        type=int,
        default=0,
        metavar="N",
        help="Cap repeated alerts per metric; 0 = unlimited (default: 0).",
    )
    parser.add_argument(
        "--alert-on",
        nargs="+",
        choices=["warning", "critical"],
        default=["warning", "critical"],
        metavar="STATUS",
        help="Statuses that trigger an alert (default: warning critical).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO).",
    )
    return parser


def _status_set(names: List[str]) -> set:
    mapping = {
        "warning": MetricStatus.WARNING,
        "critical": MetricStatus.CRITICAL,
    }
    return {mapping[n] for n in names}


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    alert_statuses = _status_set(args.alert_on)
    channel = LogAlertChannel()
    manager = AlertManager(channels=[channel], fire_on=alert_statuses)

    cfg = NotifierConfig(
        cooldown_seconds=args.cooldown,
        max_repeats=args.max_repeats,
    )
    notifier = Notifier(manager, cfg)

    collector = MetricCollector()
    runner = PipelineRunner(collector)
    results = runner.run()

    fired = 0
    for result in results:
        if result.status in alert_statuses:
            event = AlertEvent(result=result)
            if notifier.process(event):
                fired += 1

    logger.info("Notify run complete: %d result(s), %d alert(s) fired.", len(results), fired)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
