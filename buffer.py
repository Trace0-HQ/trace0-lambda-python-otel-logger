"""
In-memory log record buffer for the BatchLogProcessor.

Accumulates OTel LogRecords during a Lambda invocation and provides
them as a batch for export on flush.
"""

from __future__ import annotations

from collections import deque

from .types import OTelLogRecord


class LogBuffer:
    """
    Thread-safe in-memory buffer for OTel LogRecords.

    Implements a max size cap using a deque with maxlen — when the buffer
    is full, the oldest record is automatically dropped to make room,
    preventing unbounded memory growth during high-volume invocations.
    """

    def __init__(self, max_size: int) -> None:
        self._records: deque[OTelLogRecord] = deque(maxlen=max_size)

    def add(self, record: OTelLogRecord) -> None:
        """Adds a log record to the buffer."""
        self._records.append(record)

    def flush(self) -> list[OTelLogRecord]:
        """Returns all buffered records and clears the buffer."""
        records = list(self._records)
        self._records.clear()
        return records

    def size(self) -> int:
        """Returns the number of records currently buffered."""
        return len(self._records)

    def is_empty(self) -> bool:
        """Returns True if the buffer contains no records."""
        return len(self._records) == 0
