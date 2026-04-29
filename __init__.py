"""
trace0-lambda-otel-logger
=========================

OpenTelemetry-based logger for AWS Lambda Python functions.

Automatically:
- Installs a logging.Handler on the root logger to capture all log output
- Injects the active OTel span's traceId and spanId into every log record
- Buffers log records during the Lambda invocation (BatchLogProcessor)
- Exports logs as OTLP JSON to your Trace0 ingest endpoint on flush

Based on the OpenTelemetry Logs API specification:
https://opentelemetry.io/docs/specs/otel/logs/api/

Usage
-----
Install as the first import in your Lambda handler module:

    import trace0_lambda_otel_logger  # must be first
    from trace0_lambda_otel_logger import flush

    def handler(event, context):
        try:
            return your_handler(event, context)
        finally:
            flush()

Configuration (via environment variables)
-----------------------------------------
    OTEL_EXPORTER_OTLP_ENDPOINT         — your Trace0 ingest endpoint (required)
    OTEL_EXPORTER_OTLP_HEADERS          — your Trace0 API key (required)
"""

from __future__ import annotations

import logging

from .buffer import LogBuffer
from .config import resolve_config
from .exporter import OTLPJsonLogExporter
from .log_handler import install_handler
from .logger_provider import Trace0LoggerProvider
from .processor import BatchLogProcessor
from .model_types import Trace0Config

__version__ = "1.0.1"
__all__ = ["init", "flush"]

_provider: Trace0LoggerProvider | None = None

_logger = logging.getLogger("trace0")


def init(
    endpoint: str | None = None,
    api_key: str | None = None,
    max_batch_size: int = 512,
    export_timeout_seconds: float = 5.0,
    service_name: str | None = None,
    service_version: str | None = None,
) -> None:
    """
    Initialises the Trace0 OTel logger.

    Called automatically on import using environment variables. Can also be
    called explicitly to provide programmatic configuration — explicit values
    take precedence over environment variables.

    Args:
        endpoint: Trace0 ingest endpoint URL.
        api_key: Trace0 API key.
        max_batch_size: Maximum log records to buffer per invocation (default: 512).
        export_timeout_seconds: HTTP export timeout in seconds (default: 5.0).
        service_name: Service name for log records (default: AWS_LAMBDA_FUNCTION_NAME).
        service_version: Service version for log records (default: AWS_LAMBDA_FUNCTION_VERSION).
    """
    global _provider

    config = resolve_config(
        endpoint=endpoint,
        api_key=api_key,
        max_batch_size=max_batch_size,
        export_timeout_seconds=export_timeout_seconds,
        service_name=service_name,
        service_version=service_version,
    )

    buffer = LogBuffer(config.max_batch_size)
    exporter = OTLPJsonLogExporter(config)
    processor = BatchLogProcessor(buffer, exporter)
    provider = Trace0LoggerProvider(processor)
    otel_logger = provider.get_logger("trace0-lambda-otel-logger")

    install_handler(otel_logger)

    _provider = provider


def flush() -> None:
    """
    Flushes all buffered log records to the Trace0 ingest endpoint.

    Must be called at the end of every Lambda handler invocation to ensure
    all logs are exported before the Lambda process is frozen.

        def handler(event, context):
            try:
                return your_handler(event, context)
            finally:
                flush()
    """
    if _provider is None:
        return
    _provider.force_flush()


# Auto-initialise on import using environment variables.
# Errors are caught so a missing config does not crash the Lambda on import.
try:
    init()
except ValueError as e:
    logging.getLogger("trace0").warning(str(e))
