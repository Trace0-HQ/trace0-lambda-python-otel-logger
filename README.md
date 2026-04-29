# trace0-lambda-otel-logger

OpenTelemetry-based logger for AWS Lambda Python functions.

Automatically captures all `logging` output, injects OTel trace context (traceId, spanId), and exports logs as OTLP JSON to the Trace0 ingest endpoint.

> See the [Background](#background) section for more details on why this library is needed.

## How it works

```
logging.info() 
  → Trace0LogHandler (logging.Handler bridge)
    → BatchLogProcessor (buffers during invocation)
      → OTLPJsonLogExporter (POST to Trace0 ingest endpoint)
```

Based on the [OpenTelemetry Logs API specification](https://opentelemetry.io/docs/specs/otel/logs/api/).

## Installation

```bash
pip install trace0-lambda-otel-logger
```

## Usage

**1. Add as the first import in your Lambda handler module:**

```python
import trace0_lambda_otel_logger  # must be first
from trace0_lambda_otel_logger import flush
```

**2. Call `flush()` at the end of every invocation:**

```python
import logging

logger = logging.getLogger(__name__)

def handler(event, context):
    try:
        return your_handler(event, context)
    finally:
        flush()  # always flush before Lambda freezes
```

**3. Set environment variables:**

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=https://app.trace0hq.com/api
OTEL_EXPORTER_OTLP_HEADERS=X-API-KEY=YOUR_TRACE0_ENV_API_KEY
```

That's it. No changes to your existing `logging` calls required.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Yes | — | Your Trace0 ingest endpoint |
| `OTEL_EXPORTER_OTLP_HEADERS` | Yes | — | Your Trace0 API key |

## Log Record Format

Each log record is exported as OTLP JSON with the following fields:

```json
{
  "timeUnixNano": "1234567890000000000",
  "severityNumber": 9,
  "severityText": "INFO",
  "body": { "stringValue": "User created" },
  "attributes": [
    { "key": "logger.name", "value": { "stringValue": "app.users" } },
    { "key": "code.function", "value": { "stringValue": "create_user" } },
    { "key": "code.lineno", "value": { "intValue": 42 } }
  ],
  "traceId": "abc123...",
  "spanId": "def456..."
}
```

## Requirements

- Python >= 3.11
- AWS Lambda with the [OpenTelemetry Lambda Layer](https://github.com/open-telemetry/opentelemetry-lambda) attached (for trace context)

## Background

To correlate logs with traces in Trace0, this library must be installed in your Lambda function. This is necessary because the OpenTelemetry Python Logs SDK is currently in an experimental state. The APIs within [opentelemetry.sdk._logs](https://opentelemetry-python.readthedocs.io/en/stable/sdk/_logs.html) are subject to change in minor/patch releases and make no backward compatibility guarantees at this time.

`trace0-lambda-otel-logger` solves this gap by installing a `logging.Handler` on the root logger that automatically injects the active OTel span's `traceId` and `spanId` into every log record, and exporting them directly to the Trace0 ingest endpoint. This enables full log-trace correlation with minimal integration effort.
