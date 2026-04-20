"""CLI entry-point: pipewatch-summary — print a health summary to stdout."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import List

from pipewatch.exporters import _result_to_dict
from pipewatch.filters import ResultFilter
from pipewatch.metrics import MetricResult, MetricStatus
from pipewatch.summarizer import Summarizer

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipewatch-summary",
        description="Print a health summary of pipeline metrics.",
    )
    parser.add_argument(
        "--input",
        metavar="FILE",
        default=None,
        help="JSON file produced by pipewatch-export (default: stdin).",
    )
    parser.add_argument(
        "--status",
        nargs="+",
        choices=[s.value for s in MetricStatus],
        default=None,
        help="Filter results to these statuses before summarising.",
    )
    parser.add_argument(
        "--fail-on-critical",
        action="store_true",
        default=False,
        help="Exit with code 2 when any critical metric is present.",
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser


def _load_results(path: str | None) -> List[MetricResult]:
    """Deserialise a JSON array of result dicts back into MetricResult objects."""
    from pipewatch.metrics import Metric

    stream = open(path) if path else sys.stdin  # noqa: WPS515
    try:
        records = json.load(stream)
    finally:
        if path:
            stream.close()

    results: List[MetricResult] = []
    for rec in records:
        metric = Metric(name=rec["name"], source=rec["source"], value=rec["value"])
        results.append(
            MetricResult(
                metric=metric,
                status=MetricStatus(rec["status"]),
            )
        )
    return results


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=args.log_level)

    results = _load_results(args.input)

    if args.status:
        statuses = [MetricStatus(s) for s in args.status]
        results = ResultFilter(results).by_status(statuses)

    summarizer = Summarizer()
    summary = summarizer.summarize(results)
    print(summarizer.format_report(summary))

    if args.fail_on_critical and summary.critical > 0:
        sys.exit(2)


if __name__ == "__main__":  # pragma: no cover
    main()
