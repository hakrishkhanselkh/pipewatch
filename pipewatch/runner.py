"""High-level pipeline runner that ties collector and alert manager together."""

from typing import Optional
from pipewatch.collector import MetricCollector
from pipewatch.alerts import AlertManager


class PipelineRunner:
    """Collects metrics from all registered sources and dispatches alerts."""

    def __init__(
        self,
        collector: Optional[MetricCollector] = None,
        alert_manager: Optional[AlertManager] = None,
    ) -> None:
        self.collector = collector or MetricCollector()
        self.alert_manager = alert_manager or AlertManager()

    def run(self) -> dict:
        """Run a single collection cycle.

        Returns a summary dict: {source: [MetricResult, ...]}.
        """
        summary: dict = {}
        all_results = self.collector.collect_all()
        for source, results in all_results.items():
            self.alert_manager.process(source, results)
            summary[source] = results
        return summary

    def run_and_report(self) -> bool:
        """Run collection and print a brief health report.

        Returns True if all metrics are healthy, False otherwise.
        """
        from pipewatch.metrics import MetricStatus

        summary = self.run()
        all_healthy = True
        for source, results in summary.items():
            for result in results:
                if not result.is_healthy():
                    all_healthy = False
                print(
                    f"  {source}/{result.metric.name}: "
                    f"{result.status.value} ({result.value})"
                )
        status_label = "OK" if all_healthy else "DEGRADED"
        print(f"\nOverall pipeline status: {status_label}")
        return all_healthy
