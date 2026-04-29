"""
Trace0 LoggerProvider and Logger.

Implements the OTel Logs API LoggerProvider and Logger interfaces.
https://opentelemetry.io/docs/specs/otel/logs/api/
"""

from __future__ import annotations

import time
from typing import Any

from .processor import BatchLogProcessor
from .trace_context import get_trace_context
from .model_types import OTelAttribute, OTelLogRecord, SeverityNumber


class Trace0Logger:
    """
    Logger implementation following the OTel Logs API Logger interface.
    https://opentelemetry.io/docs/specs/otel/logs/api/#logger

    Responsible for creating OTel LogRecords and passing them to the
    BatchLogProcessor.
    """

    def __init__(self, processor: BatchLogProcessor, name: str, version: str) -> None:
        self._processor = processor
        self._name = name
        self._version = version

    def emit(
        self,
        severity_number: SeverityNumber,
        severity_text: str,
        body: str,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """
        Emits a log record following the OTel LogRecord data model.
        https://opentelemetry.io/docs/specs/otel/logs/data-model/#log-and-event-record-definition
        """
        now_ns = str(int(time.time_ns()))
        trace_context = get_trace_context()

        record = OTelLogRecord(
            time_unix_nano=now_ns,
            observed_time_unix_nano=now_ns,
            severity_number=severity_number,
            severity_text=severity_text,
            body={"stringValue": body},
            attributes=[
                _to_otel_attribute(k, v) for k, v in (attributes or {}).items()
            ],
            trace_id=trace_context.trace_id if trace_context else None,
            span_id=trace_context.span_id if trace_context else None,
        )

        self._processor.on_emit(record)


class Trace0LoggerProvider:
    """
    LoggerProvider implementation following the OTel Logs API LoggerProvider interface.
    https://opentelemetry.io/docs/specs/otel/logs/api/#loggerprovider

    Entry point for acquiring Logger instances. Registered globally so any
    OTel-aware code automatically routes through Trace0.
    """

    def __init__(self, processor: BatchLogProcessor) -> None:
        self._processor = processor
        self._loggers: dict[str, Trace0Logger] = {}

    def get_logger(self, name: str, version: str = "1.0.4") -> Trace0Logger:
        """
        Returns a Logger for the given instrumentation scope.
        Identical scope parameters return the same Logger instance.
        """
        key = f"{name}@{version}"
        if key not in self._loggers:
            self._loggers[key] = Trace0Logger(self._processor, name, version)
        return self._loggers[key]

    def force_flush(self) -> None:
        self._processor.force_flush()

    def shutdown(self) -> None:
        self._processor.shutdown()


def _to_otel_attribute(key: str, value: Any) -> OTelAttribute:
    """Converts a key-value pair to an OTel attribute."""
    if isinstance(value, bool):
        return OTelAttribute(key=key, value={"boolValue": value})
    if isinstance(value, int):
        return OTelAttribute(key=key, value={"intValue": value})
    if isinstance(value, float):
        return OTelAttribute(key=key, value={"doubleValue": value})
    return OTelAttribute(key=key, value={"stringValue": str(value)})
