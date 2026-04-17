"""JSON structured logging for Cloud Logging compatibility."""

import json
import logging
import os
import sys


class JsonFormatter(logging.Formatter):
    """Format log records as JSON for Cloud Logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "funcName": record.funcName,
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging() -> None:
    """Configure root logger with JSON formatter.

    Uses LOG_LEVEL env var (default: WARNING for PII protection in Cloud Run).
    """
    level = os.environ.get("LOG_LEVEL", "WARNING").upper()
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
