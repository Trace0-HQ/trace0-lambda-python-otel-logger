"""
Configuration resolution for the Trace0 Lambda OTel Logger.

Environment variables:
  OTEL_EXPORTER_OTLP_ENDPOINT         — your Trace0 ingest endpoint (required)
  OTEL_EXPORTER_OTLP_HEADERS          — your Trace0 API key (required)
"""

from __future__ import annotations

import os

from .types import Trace0Config


def resolve_config(
    endpoint: str | None = None,
    api_key: str | None = None,
    max_batch_size: int = 512,
    export_timeout_seconds: float = 5.0,
    service_name: str | None = None,
    service_version: str | None = None,
) -> Trace0Config:
    """
    Resolves configuration from provided arguments and environment variables.
    Arguments take precedence over environment variables.

    Raises:
        ValueError: If endpoint or api_key are not provided via args or env vars.
    """
    resolved_endpoint = endpoint or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    resolved_api_key = api_key
    if resolved_api_key is None:
        header_str = os.environ.get("OTEL_EXPORTER_OTLP_HEADERS")
        headers = dict(pair.split("=", 1) for pair in header_str.split(",")) if header_str else {}
        resolved_api_key = headers.get("X-API-KEY")

    if not resolved_endpoint:
        raise ValueError(
            "[Trace0] Missing endpoint. Set OTEL_EXPORTER_OTLP_ENDPOINT env var or pass endpoint to init()."
        )
    if not resolved_api_key:
        raise ValueError(
            "[Trace0] Missing API key. Set OTEL_EXPORTER_OTLP_HEADERS env var or pass api_key to init()."
        )

    return Trace0Config(
        endpoint=resolved_endpoint,
        api_key=resolved_api_key,
        max_batch_size=max_batch_size,
        export_timeout_seconds=export_timeout_seconds,
        service_name=(
            service_name
            or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
            or "unknown_service"
        ),
        service_version=(
            service_version
            or os.environ.get("AWS_LAMBDA_FUNCTION_VERSION")
            or "0.0.0"
        ),
    )
