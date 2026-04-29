"""
OTel trace context extraction.

Extracts the active span's traceId and spanId from the current OTel context,
so they can be injected into log records for log-trace correlation.
"""

from __future__ import annotations

from dataclasses import dataclass

from opentelemetry import trace
from opentelemetry.trace import SpanContext, INVALID_SPAN_ID, INVALID_TRACE_ID


@dataclass(frozen=True)
class TraceContext:
    trace_id: str
    span_id: str


def get_trace_context() -> TraceContext | None:
    """
    Returns the active OTel span's traceId and spanId, or None if there
    is no active span or the span context is invalid.
    """
    span = trace.get_current_span()
    ctx: SpanContext = span.get_span_context()

    if ctx.trace_id == INVALID_TRACE_ID or ctx.span_id == INVALID_SPAN_ID:
        return None

    return TraceContext(
        trace_id=format(ctx.trace_id, "032x"),
        span_id=format(ctx.span_id, "016x"),
    )
