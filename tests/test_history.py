"""Tests for pipewatch.history and cli_history."""

import json
import pytest
from unittest.mock import patch

from pipewatch.history import MetricHistory, TrendInfo, _detect_direction
from pipewatch.metrics import Metric, MetricResult, MetricStatus


# ---------------------------------------------------------------------------
def make_result(source="src", name="lag", value=1.0, status=MetricStatus.OK):
    metric = Metric(name=name, source=source, value=value)
    return MetricResult(metric=metric, status=status, message="")


# ---------------------------------------------------------------------------
class TestMetricHistory:
    def test_record_and_retrieve(self):
        h = MetricHistory()
        r = make_result(value=5.0)
        h.record(r)
        assert h.get("src", "lag") == [r]

    def test_len_counts_all_records(self):
        h = MetricHistory()
        h.record(make_result(name="a", value=1.0))
        h.record(make_result(name="b", value=2.0))
        assert len(h) == 2

    def test_rolling_window_respected(self):
        h = MetricHistory(maxlen=3)
        for i in range(5):
            h.record(make_result(value=float(i)))
        stored = h.get("src", "lag")
        assert len(stored) == 3
        assert stored[-1].value == 4.0

    def test_trend_returns_none_with_single_sample(self):
        h = MetricHistory()
        h.record(make_result(value=1.0))
        assert h.trend("src", "lag") is None

    def test_trend_rising(self):
        h = MetricHistory()
        for v in [1.0, 2.0, 3.0, 4.0, 5.0]:
            h.record(make_result(value=v))
        t = h.trend("src", "lag")
        assert isinstance(t, TrendInfo)
        assert t.direction == "rising"

    def test_trend_falling(self):
        h = MetricHistory()
        for v in [5.0, 4.0, 3.0, 2.0, 1.0]:
            h.record(make_result(value=v))
        t = h.trend("src", "lag")
        assert t.direction == "falling"

    def test_trend_stable(self):
        h = MetricHistory()
        for v in [3.0, 3.0, 3.0, 3.0]:
            h.record(make_result(value=v))
        t = h.trend("src", "lag")
        assert t.direction == "stable"

    def test_all_trends_returns_one_per_metric(self):
        h = MetricHistory()
        for v in [1.0, 2.0]:
            h.record(make_result(name="a", value=v))
            h.record(make_result(name="b", value=v))
        trends = h.all_trends()
        assert len(trends) == 2

    def test_invalid_maxlen_raises(self):
        with pytest.raises(ValueError):
            MetricHistory(maxlen=1)

    def test_record_all(self):
        h = MetricHistory()
        results = [make_result(value=float(i)) for i in range(3)]
        h.record_all(results)
        assert len(h) == 3


# ---------------------------------------------------------------------------
class TestDetectDirection:
    def test_single_value_stable(self):
        assert _detect_direction([5.0]) == "stable"

    def test_empty_stable(self):
        assert _detect_direction([]) == "stable"


# ---------------------------------------------------------------------------
class TestTrendInfoStr:
    def test_str_contains_direction(self):
        t = TrendInfo(
            source="db", name="lag", window=3,
            values=[1.0, 2.0, 3.0], direction="rising"
        )
        assert "rising" in str(t)
        assert "db/lag" in str(t)


# ---------------------------------------------------------------------------
class TestCliHistory:
    def test_main_no_files_returns_error(self, tmp_path):
        from pipewatch.cli_history import main
        # Pass a non-existent file
        result = main([str(tmp_path / "missing.json")])
        assert result == 1

    def test_main_valid_file(self, tmp_path):
        from pipewatch.cli_history import main
        data = [
            {"name": "lag", "source": "db", "value": 1.0, "status": "OK", "message": ""},
            {"name": "lag", "source": "db", "value": 2.0, "status": "OK", "message": ""},
        ]
        f = tmp_path / "export.json"
        f.write_text(json.dumps(data))
        result = main([str(f), "--window", "2"])
        assert result == 0
