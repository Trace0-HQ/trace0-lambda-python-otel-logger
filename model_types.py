"""
OTel Logs data model types.

Based on the OpenTelemetry Logs data model specification:
https://opentelemetry.io/docs/specs/otel/logs/data-model/
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class SeverityNumber(IntEnum):
    """
    OTel severity numbers.
    https://opentelemetry.io/docs/specs/otel/logs/data-model/#field-severitynumber
    """
    UNSPECIFIED = 0
    TRACE = 1
    DEBUG = 5
    INFO = 9
    WARN = 13
    ERROR = 17
    FATAL = 21


@dataclass
class OTelAttribute:
    """A single key-value attribute on a log record."""
    key: str
    value: dict[str, Any]


@dataclass
class OTelLogRecord:
    """
    OTel LogRecord following the OpenTelemetry Logs data model.
    https://opentelemetry.io/docs/specs/otel/logs/data-model/#log-and-event-record-definition
    """
    time_unix_nano: str
    observed_time_unix_nano: str
    severity_number: SeverityNumber
    severity_text: str
    body: dict[str, str]
    attributes: list[OTelAttribute] = field(default_factory=list)
    trace_id: str | None = None
    span_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        record: dict[str, Any] = {
            "timeUnixNano": self.time_unix_nano,
            "observedTimeUnixNano": self.observed_time_unix_nano,
            "severityNumber": int(self.severity_number),
            "severityText": self.severity_text,
            "body": self.body,
            "attributes": [{"key": a.key, "value": a.value} for a in self.attributes],
        }
        if self.trace_id:
            record["traceId"] = self.trace_id
        if self.span_id:
            record["spanId"] = self.span_id
        return record


@dataclass
class Trace0Config:
    """Configuration for the Trace0 Lambda OTel Logger."""
    endpoint: str
    api_key: str
    max_batch_size: int = 512
    export_timeout_seconds: float = 5.0
    service_name: str = "unknown_service"
    service_version: str = "0.0.0"
