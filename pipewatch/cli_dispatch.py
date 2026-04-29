"""CLI entry-point: dispatch results from a JSON file to configured handlers.

Usage examples
--------------
  pipewatch-dispatch results.json --log
  pipewatch-dispatch results.json --log --json-out out.json
  pipewatch-dispatch results.json --log --json-out out.json --status WARNING CRITICAL
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List

from pipewatch.dispatcher import ResultDispatcher
from pipewatch.metrics import MetricResult, MetricStatus

logger = logging.getLogger(__name__)


def _load_results(path: str) -> List[MetricResult]:
    data = json.loads(Path(path).read_text())
    results: List[MetricResult] = []
    for item in data:
        ts = item.get("timestamp")
        results.append(
            MetricResult(
                name=item["name"],
                source=item["source"],
                value=item.get("value"),
                status=MetricStatus[item["status"].upper()],
                timestamp=datetime.fromisoformat(ts) if ts else None,
            )
        )
    return results


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pipewatch-dispatch",
        description="Fan-out metric results to one or more handlers.",
    )
    p.add_argument("file", help="JSON file containing MetricResults")
    p.add_argument(
        "--log",
        action="store_true",
        default=False,
        help="Attach a logging handler that prints each result",
    )
    p.add_argument(
        "--json-out",
        metavar="PATH",
        help="Append dispatched results to a JSON-lines file",
    )
    p.add_argument(
        "--status",
        nargs="+",
        metavar="STATUS",
        default=None,
        help="Only dispatch results with these statuses (e.g. WARNING CRITICAL)",
    )
    p.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return p


def main(argv: List[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s %(message)s",
    )

    results = _load_results(args.file)

    if args.status:
        allowed = {MetricStatus[s.upper()] for s in args.status}
        results = [r for r in results if r.status in allowed]

    dispatcher = ResultDispatcher()

    if args.log:
        def _log_handler(r: MetricResult) -> None:
            logger.info("[%s] %s=%s (%s)", r.source, r.name, r.value, r.status.name)

        dispatcher.register("log", _log_handler)

    if args.json_out:
        out_path = Path(args.json_out)

        def _json_handler(r: MetricResult) -> None:
            record = {
                "name": r.name,
                "source": r.source,
                "value": r.value,
                "status": r.status.name,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            }
            with out_path.open("a") as fh:
                fh.write(json.dumps(record) + "\n")

        dispatcher.register("json_out", _json_handler)

    if not dispatcher.handler_names:
        parser.error("At least one handler (--log, --json-out) must be specified.")

    report = dispatcher.dispatch(results)
    print(report)

    if not report.success:
        for err in report.errors:
            logger.error(err)
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
