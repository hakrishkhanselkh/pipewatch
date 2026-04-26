"""Tests for the cli_route entry point."""

import json
import sys
from io import StringIO
from pathlib import Path

import pytest

from pipewatch.metrics import MetricResult, MetricStatus
from pipewatch.cli_route import build_parser, main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_result(
    name: str = "latency",
    source: str = "db",
    value: float = 1.0,
    status: MetricStatus = MetricStatus.OK,
):
    return MetricResult(
        name=name,
        source=source,
        value=value,
        status=status,
        timestamp=None,
    )


def _write_results(path: Path, results: list) -> None:
    """Serialise a list of MetricResult objects to a JSON file."""
    data = [
        {
            "name": r.name,
            "source": r.source,
            "value": r.value,
            "status": r.status.value,
            "timestamp": r.timestamp,
        }
        for r in results
    ]
    path.write_text(json.dumps(data))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def results_file(tmp_path):
    """A temporary JSON file with a mixed set of results."""
    results = [
        make_result("latency", "db", 5.0, MetricStatus.CRITICAL),
        make_result("error_rate", "api", 0.2, MetricStatus.WARNING),
        make_result("throughput", "queue", 100.0, MetricStatus.OK),
        make_result("latency", "cache", 1.0, MetricStatus.OK),
    ]
    p = tmp_path / "results.json"
    _write_results(p, results)
    return p


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------

def test_parser_requires_file():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_parser_defaults(results_file):
    parser = build_parser()
    args = parser.parse_args([str(results_file)])
    assert args.file == str(results_file)
    assert args.status is None
    assert args.source is None
    assert args.name is None


def test_parser_accepts_status_filter(results_file):
    parser = build_parser()
    args = parser.parse_args([str(results_file), "--status", "critical"])
    assert args.status == "critical"


def test_parser_accepts_source_filter(results_file):
    parser = build_parser()
    args = parser.parse_args([str(results_file), "--source", "db"])
    assert args.source == "db"


def test_parser_accepts_name_filter(results_file):
    parser = build_parser()
    args = parser.parse_args([str(results_file), "--name", "latency"])
    assert args.name == "latency"


# ---------------------------------------------------------------------------
# main() integration tests
# ---------------------------------------------------------------------------

def test_main_routes_critical_only(results_file, capsys):
    sys.argv = ["pipewatch-route", str(results_file), "--status", "critical"]
    main()
    captured = capsys.readouterr()
    assert "CRITICAL" in captured.out
    assert "WARNING" not in captured.out
    assert "OK" not in captured.out


def test_main_routes_by_source(results_file, capsys):
    sys.argv = ["pipewatch-route", str(results_file), "--source", "api"]
    main()
    captured = capsys.readouterr()
    assert "api" in captured.out
    assert "db" not in captured.out


def test_main_routes_by_name(results_file, capsys):
    sys.argv = ["pipewatch-route", str(results_file), "--name", "latency"]
    main()
    captured = capsys.readouterr()
    assert "latency" in captured.out
    assert "error_rate" not in captured.out
    assert "throughput" not in captured.out


def test_main_no_filters_returns_all(results_file, capsys):
    sys.argv = ["pipewatch-route", str(results_file)]
    main()
    captured = capsys.readouterr()
    # All four sources should appear
    for source in ("db", "api", "queue", "cache"):
        assert source in captured.out


def test_main_missing_file_exits(tmp_path):
    missing = tmp_path / "nope.json"
    sys.argv = ["pipewatch-route", str(missing)]
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code != 0
