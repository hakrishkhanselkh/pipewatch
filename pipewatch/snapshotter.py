"""Snapshot management: save and load collections of MetricResults to/from JSON."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from pipewatch.metrics import MetricResult, MetricStatus


_TIMESTAMP_FMT = "%Y%m%dT%H%M%SZ"


def _result_to_dict(result: MetricResult) -> dict:
    return {
        "source": result.metric.source,
        "name": result.metric.name,
        "value": result.value,
        "status": result.status.value,
        "timestamp": result.timestamp.strftime(_TIMESTAMP_FMT)
        if result.timestamp
        else None,
    }


def _dict_to_result(data: dict) -> MetricResult:
    from pipewatch.metrics import Metric

    metric = Metric(source=data["source"], name=data["name"])
    ts = (
        datetime.strptime(data["timestamp"], _TIMESTAMP_FMT).replace(
            tzinfo=timezone.utc
        )
        if data.get("timestamp")
        else None
    )
    return MetricResult(
        metric=metric,
        value=data["value"],
        status=MetricStatus(data["status"]),
        timestamp=ts,
    )


class Snapshotter:
    """Persist and restore pipeline metric snapshots."""

    def __init__(self, directory: str = ".") -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def save(self, results: List[MetricResult], label: Optional[str] = None) -> Path:
        """Serialise *results* to a timestamped JSON file and return its path."""
        ts = datetime.now(tz=timezone.utc).strftime(_TIMESTAMP_FMT)
        filename = f"snapshot_{label}_{ts}.json" if label else f"snapshot_{ts}.json"
        path = self.directory / filename
        payload = {"snapshot_ts": ts, "results": [_result_to_dict(r) for r in results]}
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def load(self, path: str) -> List[MetricResult]:
        """Deserialise a snapshot file and return the list of MetricResults."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return [_dict_to_result(item) for item in data["results"]]

    def list_snapshots(self) -> List[Path]:
        """Return snapshot files in the directory, sorted oldest-first."""
        return sorted(self.directory.glob("snapshot_*.json"))
