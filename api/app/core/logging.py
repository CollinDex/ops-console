"""JSON structured logging and the per-request context."""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

# Extra attributes copied from the log record into the JSON line when present.
_EXTRA_FIELDS = ("method", "path", "status", "duration_ms", "actor_id")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_ctx.get(),
        }
        for field in _EXTRA_FIELDS:
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    """Send JSON lines to stdout. Safe to call more than once."""
    root = logging.getLogger()
    root.setLevel(level)
    for handler in root.handlers[:]:
        if getattr(handler, "_credisure", False):
            root.removeHandler(handler)
    handler = logging.StreamHandler(sys.stdout)
    handler._credisure = True  # type: ignore[attr-defined]
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    # We write our own access log, so silence uvicorn's.
    logging.getLogger("uvicorn.access").disabled = True
