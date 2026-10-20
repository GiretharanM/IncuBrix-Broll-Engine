import logging
import json
import time
import uuid
from datetime import datetime, timezone
from contextvars import ContextVar
from typing import Optional, Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variables for logging correlation
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")
job_id_ctx: ContextVar[str] = ContextVar("job_id", default="")

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_ctx.get(""),
            "job_id": getattr(record, "job_id", job_id_ctx.get("")),
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Include custom extra fields if provided
        for key, value in record.__dict__.items():
            if key not in (
                "args", "asctime", "created", "exc_info", "exc_text", "filename",
                "funcName", "id", "levelname", "levelno", "lineno", "module",
                "msecs", "message", "msg", "name", "pathname", "process",
                "processName", "relativeCreated", "stack_info", "thread",
                "threadName", "job_id", "correlation_id"
            ):
                log_data[key] = value

        return json.dumps(log_data)

def setup_logging(level: str = "INFO"):
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)

    # Set specific third-party noisy loggers to WARNING
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        corr_id = request.headers.get("X-Correlation-Id") or str(uuid.uuid4())
        correlation_id_ctx.set(corr_id)

        start_time = time.time()
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000

        response.headers["X-Correlation-Id"] = corr_id
        response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"

        # Structured request logging
        logger = logging.getLogger("incubrix.api")
        logger.info(
            f"{request.method} {request.url.path} -> {response.status_code} in {process_time:.2f}ms",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "process_time_ms": round(process_time, 2),
            }
        )
        return response
