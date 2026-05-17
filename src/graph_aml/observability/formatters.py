"""JSON structured log formatter."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from graph_aml.observability.events import normalise_event_dict


class StructuredLogFormatter(logging.Formatter):
    """Format log records as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        event = getattr(record, "event", None)
        if event is not None:
            payload["event"] = normalise_event_dict(event)

        if record.exc_info is not None:
            exc_type, exc_value, _ = record.exc_info
            payload["exception"] = {
                "type": exc_type.__name__ if exc_type is not None else None,
                "message": str(exc_value),
                "traceback": self.formatException(record.exc_info),
            }

        return json.dumps(payload, default=str, sort_keys=True)
