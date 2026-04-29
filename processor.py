"""
BatchLogProcessor.

Buffers OTel LogRecords during a Lambda invocation and exports them
as a single batch when flush() is called at the end of the invocation.

Follows the OTel BatchLogRecordProcessor specification:
https://opentelemetry.io/docs/specs/otel/logs/sdk/#batching-logrecord-processor
"""

from __future__ import annotations

from .buffer import LogBuffer
from .exporter import OTLPJsonLogExporter
from .model_types import OTelLogRecord


class BatchLogProcessor:
    """
    Buffers OTel LogRecords and exports them as a batch on flush.
    """

    def __init__(self, buffer: LogBuffer, exporter: OTLPJsonLogExporter) -> None:
        self._buffer = buffer
        self._exporter = exporter

    def on_emit(self, record: OTelLogRecord) -> None:
        """Called for each log record — adds it to the buffer."""
        self._buffer.add(record)

    def force_flush(self) -> None:
        """
        Flushes all buffered log records to the exporter.
        Must be called at the end of each Lambda invocation.
        """
        if self._buffer.is_empty():
            return
        records = self._buffer.flush()
        self._exporter.export(records)

    def shutdown(self) -> None:
        """Shuts down the processor, flushing any remaining records."""
        self.force_flush()
