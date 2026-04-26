"""CLI entry point: route results from a JSON file to configured channels.

Usage examples::

    pipewatch-route results.json --status CRITICAL WARNING --log
    pipewatch-route results.json --source db --no-fallthrough
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import List

from pipewatch.metrics import Metric, MetricResult, MetricStatus
from pipewatch.alerts import LogAlertChannel
from pipewatch.router import ResultRouter, RoutingRule

logger = logging.getLogger(__name__)


def _load_results(path: str) -> List[MetricResult]:
    with open(path) as fh:
        raw = json.load(fh)
    results = []
    for item in raw:
        metric = Metric(
            name=item["name"],
            source=item["source"],
            value=item.get("value"),
        )
        results.append(
            MetricResult(
                metric=metric,
                status=MetricStatus(item["status"]),
                value=item.get("value"),
            )
        )
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipewatch-route",
        description="Route pipeline results to alert channels based on rules.",
    )
    parser.add_argument("file", help="Path to JSON results file.")
    parser.add_argument(
        "--status",
        nargs="+",
        metavar="STATUS",
        default=["WARNING", "CRITICAL"],
        help="Status values to match (default: WARNING CRITICAL).",
    )
    parser.add_argument(
        "--source",
        default=None,
        metavar="SOURCE",
        help="Restrict routing to a specific source name.",
    )
    parser.add_argument(
        "--no-fallthrough",
        dest="fallthrough",
        action="store_false",
        default=True,
        help="Stop routing after the first matching rule.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s %(message)s",
    )

    try:
        results = _load_results(args.file)
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        logger.error("Failed to load results: %s", exc)
        sys.exit(1)

    statuses = []
    for s in args.status:
        try:
            statuses.append(MetricStatus(s.lower()))
        except ValueError:
            logger.error("Unknown status %r", s)
            sys.exit(1)

    router = ResultRouter(fallthrough=args.fallthrough)
    log_channel = LogAlertChannel()

    predicate = ResultRouter.status_predicate(*statuses)
    if args.source:
        source_pred = ResultRouter.source_predicate(args.source)
        predicate = lambda r, _p=predicate, _s=source_pred: _p(r) and _s(r)  # noqa: E731

    router.add_rule(RoutingRule(name="cli-rule", predicate=predicate, channels=[log_channel]))

    matched = router.route_many(results)
    logger.info("Routing complete: %d/%d results matched.", matched, len(results))


if __name__ == "__main__":  # pragma: no cover
    main()
