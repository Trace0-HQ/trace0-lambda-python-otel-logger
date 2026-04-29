"""
Trace0 logging.Handler bridge.

Installs a custom logging.Handler on the root logger that bridges Python's
standard logging module into the OTel Logs pipeline.

This is the Python equivalent of the Node.js console monkey-patch. By
attaching to the root logger, all log records from any logger in the
application (including third-party libraries) are captured automatically —
no changes to existing logging calls are required.

https://docs.python.org/3/library/logging.html#handler-objects
"""

from __future__ import annotations

import logging
from typing import Any

from .logger_provider import Trace0Logger
from .types import SeverityNumber

# Maps Python logging levels to OTel severity numbers
_SEVERITY_MAP: dict[int, tuple[SeverityNumber, str]] = {
    logging.DEBUG: (SeverityNumber.DEBUG, "DEBUG"),
    logging.INFO: (SeverityNumber.INFO, "INFO"),
    logging.WARNING: (SeverityNumber.WARN, "WARN"),
    logging.ERROR: (SeverityNumber.ERROR, "ERROR"),
    logging.CRITICAL: (SeverityNumber.FATAL, "FATAL"),
}


class Trace0LogHandler(logging.Handler):
    """
    A logging.Handler that emits OTel LogRecords via the Trace0Logger.

    Attached to the root logger so all application and library log output
    is captured and exported to the Trace0 ingest endpoint on flush.
    """

    def __init__(self, logger: Trace0Logger) -> None:
        super().__init__(level=logging.DEBUG)
        self._otel_logger = logger

    def emit(self, record: logging.LogRecord) -> None:
        """
        Called by the logging framework for each log record.
        Converts the Python LogRecord to an OTel LogRecord.
        """
        try:
            severity_number, severity_text = _SEVERITY_MAP.get(
                record.levelno,
                (SeverityNumber.INFO, "INFO"),
            )

            message = self.format(record)
            attributes = _extract_attributes(record)

            self._otel_logger.emit(
                severity_number=severity_number,
                severity_text=severity_text,
                body=message,
                attributes=attributes,
            )
        except Exception:  # noqa: BLE001
            # Never let the handler crash the application
            self.handleError(record)


def install_handler(logger: Trace0Logger) -> None:
    """
    Installs the Trace0LogHandler on the root logger.

    Sets the root logger level to DEBUG so all records reach the handler —
    individual loggers and handlers can still filter at their own levels.
    """
    root_logger = logging.getLogger()

    # Avoid installing multiple handlers if init() is called more than once
    for handler in root_logger.handlers:
        if isinstance(handler, Trace0LogHandler):
            return

    handler = Trace0LogHandler(logger)
    handler.setFormatter(logging.Formatter("%(message)s"))
    root_logger.addHandler(handler)

    # Ensure the root logger passes all records down to our handler
    if root_logger.level == logging.NOTSET or root_logger.level > logging.DEBUG:
        root_logger.setLevel(logging.DEBUG)


def _extract_attributes(record: logging.LogRecord) -> dict[str, Any]:
    """
    Extracts structured attributes from a Python LogRecord.
    Includes logger name, module, function, and line number for traceability.
    """
    attributes: dict[str, Any] = {
        "logger.name": record.name,
        "code.namespace": record.module,
        "code.function": record.funcName,
        "code.lineno": record.lineno,
    }

    # Include any extra fields passed via logging.info("msg", extra={...})
    standard_keys = {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread", "threadName",
        "processName", "process", "message", "taskName",
    }
    for key, value in record.__dict__.items():
        if key not in standard_keys and not key.startswith("_"):
            attributes[key] = value

    return attributes
