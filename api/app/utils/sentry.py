"""
Sentry error tracking setup for AuditCaseOS.

This module configures Sentry for centralized error tracking, performance
monitoring, and debugging. Sentry integration is optional and controlled
via the SENTRY_DSN environment variable.

Features:
- Automatic exception capture for unhandled errors
- Performance monitoring with configurable sampling rate
- SQLAlchemy integration for database query breadcrumbs
- FastAPI integration for request context
- Logging integration for log message breadcrumbs
- User context attachment via middleware

Source: https://docs.sentry.io/platforms/python/
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.config import Settings

# Logger for this module
logger = logging.getLogger(__name__)


def setup_sentry(settings: "Settings") -> bool:
    """
    Initialize Sentry error tracking.

    Configures Sentry with integrations for FastAPI, SQLAlchemy, and logging.
    Sentry is only initialized if a DSN is provided, making it safe to call
    in development environments without configuration.

    Args:
        settings: Application settings containing Sentry configuration.

    Returns:
        bool: True if Sentry was initialized, False if disabled (no DSN).

    Example:
        >>> from app.config import get_settings
        >>> settings = get_settings()
        >>> if setup_sentry(settings):
        ...     print("Sentry enabled")
        ... else:
        ...     print("Sentry disabled (no DSN)")
    """
    if not settings.sentry_enabled:
        logger.debug("Sentry disabled (no DSN configured)")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.sentry_environment,
            release=f"auditcaseos@{settings.sentry_release}",
            traces_sample_rate=settings.sentry_traces_sample_rate,
            integrations=[
                # FastAPI integration for automatic request context
                FastApiIntegration(transaction_style="endpoint"),
                # SQLAlchemy integration for database query breadcrumbs
                SqlalchemyIntegration(),
                # Logging integration for log message breadcrumbs
                # INFO level for breadcrumbs, ERROR level for events
                LoggingIntegration(
                    level=logging.INFO,
                    event_level=logging.ERROR,
                ),
            ],
            # Attach stack traces to all error messages
            attach_stacktrace=True,
            # Don't send PII by default (GDPR compliance)
            send_default_pii=False,
            # Enable profiling for performance insights (10% sample rate)
            profiles_sample_rate=0.1 if settings.sentry_traces_sample_rate > 0 else 0.0,
        )

        logger.info(
            f"Sentry initialized: environment={settings.sentry_environment}, "
            f"release=auditcaseos@{settings.sentry_release}, "
            f"traces_sample_rate={settings.sentry_traces_sample_rate}"
        )
        return True

    except ImportError as e:
        logger.warning(f"Sentry SDK not installed, skipping initialization: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")
        return False


def set_user_context(user_id: str | None, email: str | None = None) -> None:
    """
    Set the current user context for Sentry error reports.

    This function should be called when a user is authenticated to associate
    subsequent errors with that user. The context is automatically cleared
    between requests by the Sentry SDK.

    Args:
        user_id: The unique identifier of the authenticated user.
        email: Optional email address of the user.

    Example:
        >>> set_user_context("user-123", "user@example.com")
    """
    try:
        import sentry_sdk

        if user_id:
            sentry_sdk.set_user({
                "id": str(user_id),
                "email": email,
            })
        else:
            sentry_sdk.set_user(None)
    except ImportError:
        pass  # Sentry not installed


def capture_message(message: str, level: str = "info") -> None:
    """
    Capture a message in Sentry.

    Use this for non-exception events that you want to track in Sentry.

    Args:
        message: The message to capture.
        level: The severity level (debug, info, warning, error, fatal).

    Example:
        >>> capture_message("User performed unusual action", level="warning")
    """
    try:
        import sentry_sdk

        sentry_sdk.capture_message(message, level=level)
    except ImportError:
        pass  # Sentry not installed


def add_breadcrumb(
    message: str,
    category: str = "custom",
    level: str = "info",
    data: dict | None = None,
) -> None:
    """
    Add a breadcrumb to the current Sentry scope.

    Breadcrumbs are events that happened before an error, providing context
    for debugging. They appear in the Sentry issue timeline.

    Args:
        message: Description of the event.
        category: Category for grouping (e.g., "http", "database", "custom").
        level: Severity level (debug, info, warning, error).
        data: Additional data to attach to the breadcrumb.

    Example:
        >>> add_breadcrumb(
        ...     message="Case created",
        ...     category="case",
        ...     data={"case_id": "FIN-USB-0001"}
        ... )
    """
    try:
        import sentry_sdk

        sentry_sdk.add_breadcrumb(
            message=message,
            category=category,
            level=level,
            data=data or {},
        )
    except ImportError:
        pass  # Sentry not installed
