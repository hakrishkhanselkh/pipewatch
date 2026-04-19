"""Alert channels for pipewatch metric results."""

from dataclasses import dataclass, field
from typing import List, Callable, Optional
from pipewatch.metrics import MetricResult, MetricStatus


@dataclass
class AlertEvent:
    source: str
    metric_name: str
    status: MetricStatus
    value: float
    message: str

    def __str__(self) -> str:
        return (
            f"[{self.status.value.upper()}] {self.source}/{self.metric_name} "
            f"= {self.value} — {self.message}"
        )


class AlertChannel:
    """Base class for alert channels."""

    def send(self, event: AlertEvent) -> None:
        raise NotImplementedError


class LogAlertChannel(AlertChannel):
    """Prints alerts to stdout."""

    def send(self, event: AlertEvent) -> None:
        print(str(event))


class CallbackAlertChannel(AlertChannel):
    """Calls a user-supplied callback with the AlertEvent."""

    def __init__(self, callback: Callable[[AlertEvent], None]) -> None:
        self._callback = callback

    def send(self, event: AlertEvent) -> None:
        self._callback(event)


class AlertManager:
    """Routes MetricResults to registered alert channels."""

    def __init__(
        self,
        channels: Optional[List[AlertChannel]] = None,
        notify_on: Optional[List[MetricStatus]] = None,
    ) -> None:
        self._channels: List[AlertChannel] = channels or [LogAlertChannel()]
        self._notify_on: List[MetricStatus] = notify_on or [
            MetricStatus.WARNING,
            MetricStatus.CRITICAL,
        ]

    def add_channel(self, channel: AlertChannel) -> None:
        self._channels.append(channel)

    def process(self, source: str, results: List[MetricResult]) -> None:
        for result in results:
            if result.status in self._notify_on:
                event = AlertEvent(
                    source=source,
                    metric_name=result.metric.name,
                    status=result.status,
                    value=result.value,
                    message=result.message or "",
                )
                for channel in self._channels:
                    channel.send(event)
