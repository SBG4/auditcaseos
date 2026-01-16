"""
Structured logging configuration for AuditCaseOS API.

Uses structlog for structured, JSON-formatted logs in production.
Source: https://www.structlog.org/en/stable/

Benefits:
- Consistent log format across all services
- JSON output for log aggregation (ELK, Datadog, etc.)
- Request correlation IDs for tracing
- Contextual logging with bound variables
"""

import logging
import sys

import structlog
from structlog.types import Processor

from app.config import get_settings


def configure_logging() -> None:
    """
    Configure structured logging for the application.

    In development: Pretty-printed, colored console output
    In production: JSON-formatted logs for aggregation

    Source: https://www.structlog.org/en/stable/standard-library.html
    """
    settings = get_settings()

    # Shared processors for all environments
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.is_production:
        # Production: JSON logs for aggregation
        shared_processors.append(structlog.processors.format_exc_info)
        shared_processors.append(structlog.processors.JSONRenderer())

        # Configure standard logging
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=logging.INFO,
        )
    else:
        # Development: Pretty console output
        shared_processors.append(structlog.dev.ConsoleRenderer(colors=True))

        # Configure standard logging with more detail
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            stream=sys.stdout,
            level=logging.DEBUG if settings.debug else logging.INFO,
        )

    # Configure structlog
    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        BoundLogger: Structured logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("User logged in", user_id="123", ip="192.168.1.1")
    """
    return structlog.get_logger(name)


def bind_request_context(request_id: str, user_id: str | None = None) -> None:
    """
    Bind request context variables to all subsequent log calls.

    Args:
        request_id: Unique request identifier
        user_id: Optional authenticated user ID

    Example:
        bind_request_context(request_id="abc123", user_id="user456")
        logger.info("Processing request")  # Automatically includes request_id and user_id
    """
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        user_id=user_id,
    )


def clear_request_context() -> None:
    """Clear all bound context variables (call at end of request)."""
    structlog.contextvars.clear_contextvars()


class RequestLoggingMiddleware:
    """
    Middleware to add request logging and correlation IDs.

    Adds:
    - Unique request ID to all logs during request handling
    - Request timing information
    - User ID if authenticated

    Source: OWASP Logging Cheat Sheet
    """

    def __init__(self, app):
        self.app = app
        self.logger = get_logger(__name__)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        import time
        import uuid

        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        # Bind request context
        bind_request_context(request_id=request_id)

        # Log request start
        self.logger.info(
            "Request started",
            method=scope.get("method", ""),
            path=scope.get("path", ""),
            client=scope.get("client", ("unknown", 0))[0],
        )

        # Track response status
        response_status = 500

        async def send_wrapper(message):
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = (time.time() - start_time) * 1000

            # Log request completion
            self.logger.info(
                "Request completed",
                method=scope.get("method", ""),
                path=scope.get("path", ""),
                status=response_status,
                duration_ms=round(duration_ms, 2),
            )

            # Clear context
            clear_request_context()
