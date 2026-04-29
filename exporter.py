"""
OTLP JSON log exporter.

Exports a batch of OTel LogRecords to the Trace0 ingest endpoint
as an OTLP JSON payload over HTTP.

https://opentelemetry.io/docs/specs/otlp/#otlphttp
"""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from typing import Any

from .model_types import OTelLogRecord, Trace0Config

# Use the root logger directly to avoid infinite recursion —
# we must not use our own patched logger here
_logger = logging.getLogger("trace0.exporter")

LIBRARY_NAME = "trace0-lambda-otel-logger"
LIBRARY_VERSION = "1.0.2"


class OTLPJsonLogExporter:
    """
    Exports OTel LogRecords as OTLP JSON to the Trace0 ingest endpoint.

    Uses the standard library urllib to avoid any third-party HTTP dependency,
    keeping the library lightweight for Lambda cold starts.
    """

    def __init__(self, config: Trace0Config) -> None:
        self._config = config

    def export(self, records: list[OTelLogRecord]) -> None:
        """
        Exports a batch of log records synchronously.
        Logs a warning on failure but never raises — a failed export must
        never crash the Lambda function.
        """
        if not records:
            return

        payload = self._build_payload(records)
        body = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(
            url=self._config.endpoint + '/v1/logs',
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": self._config.api_key,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request, timeout=self._config.export_timeout_seconds
            ) as response:
                if response.status >= 400:
                    _logger.warning(
                        "[Trace0] Export failed with status %d", response.status
                    )
        except urllib.error.HTTPError as e:
            _logger.warning("[Trace0] Export HTTP error: %s %s", e.code, e.reason)
        except urllib.error.URLError as e:
            _logger.warning("[Trace0] Export URL error: %s", e.reason)
        except TimeoutError:
            _logger.warning(
                "[Trace0] Export timed out after %ss",
                self._config.export_timeout_seconds,
            )

    def _build_payload(self, records: list[OTelLogRecord]) -> dict[str, Any]:
        """Builds the OTLP JSON export request body."""
        return {
            "resourceLogs": [
                {
                    "resource": {
                        "attributes": self._resource_attributes(),
                    },
                    "scopeLogs": [
                        {
                            "scope": {
                                "name": LIBRARY_NAME,
                                "version": LIBRARY_VERSION,
                            },
                            "logRecords": [r.to_dict() for r in records],
                        }
                    ],
                }
            ]
        }

    def _resource_attributes(self) -> list[dict[str, Any]]:
        """Builds the OTel resource attributes identifying this Lambda function."""
        import os

        attrs = [
            {"key": "service.name", "value": {"stringValue": self._config.service_name}},
            {"key": "service.version", "value": {"stringValue": self._config.service_version}},
            {"key": "cloud.provider", "value": {"stringValue": "aws"}},
            {"key": "cloud.platform", "value": {"stringValue": "aws_lambda"}},
        ]

        if region := os.environ.get("AWS_REGION"):
            attrs.append({"key": "cloud.region", "value": {"stringValue": region}})

        return attrs
