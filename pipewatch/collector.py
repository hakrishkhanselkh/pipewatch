"""Metric collector that aggregates results from multiple sources."""

from typing import Callable, Dict, List, Optional

from pipewatch.metrics import Metric, MetricResult, evaluate_metric


SourceFn = Callable[[], List[Metric]]


class MetricCollector:
    """Collects and evaluates metrics from registered sources."""

    def __init__(self) -> None:
        self._sources: Dict[str, SourceFn] = {}
        self._thresholds: Dict[str, Dict[str, Optional[float]]] = {}

    def register_source(self, name: str, fn: SourceFn) -> None:
        """Register a callable that returns a list of Metric objects."""
        if name in self._sources:
            raise ValueError(f"Source '{name}' is already registered.")
        self._sources[name] = fn

    def set_thresholds(
        self,
        metric_name: str,
        warning: Optional[float] = None,
        critical: Optional[float] = None,
    ) -> None:
        """Set evaluation thresholds for a named metric."""
        self._thresholds[metric_name] = {"warning": warning, "critical": critical}

    def collect(self) -> List[MetricResult]:
        """Run all registered sources and return evaluated MetricResults."""
        results: List[MetricResult] = []
        for source_name, fn in self._sources.items():
            try:
                metrics = fn()
            except Exception as exc:  # noqa: BLE001
                print(f"[pipewatch] Error collecting from '{source_name}': {exc}")
                continue
            for metric in metrics:
                thresholds = self._thresholds.get(metric.name, {})
                result = evaluate_metric(
                    metric,
                    warning_threshold=thresholds.get("warning"),
                    critical_threshold=thresholds.get("critical"),
                )
                results.append(result)
        return results

    @property
    def source_names(self) -> List[str]:
        return list(self._sources.keys())
