"""
AuditCaseOS API - Main FastAPI Application.

This module initializes the FastAPI application with all routers,
middleware, and startup/shutdown events.

Production Features:
- Rate limiting (slowapi)
- Security headers (OWASP)
- Structured logging (structlog)
- Prometheus metrics
- CORS hardening
"""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from minio import Minio
from minio.error import S3Error
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.utils.logging import configure_logging, get_logger
from app.utils.metrics import setup_prometheus
from app.utils.rate_limit import limiter
from app.utils.sentry import set_user_context, setup_sentry

# Initialize structured logging
configure_logging()
logger = get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Headers added:
    - X-Content-Type-Options: Prevents MIME type sniffing
    - X-Frame-Options: Prevents clickjacking
    - X-XSS-Protection: Legacy XSS protection
    - Strict-Transport-Security: Enforces HTTPS (in production)
    - Content-Security-Policy: Restricts resource loading
    - Referrer-Policy: Controls referrer information
    - Permissions-Policy: Restricts browser features

    Source: https://owasp.org/www-project-secure-headers/
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        settings = get_settings()

        # Always add these headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # Add HSTS header in production (requires HTTPS)
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Content Security Policy - adjust based on your needs
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self' data:; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp

        return response


class SentryUserContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to attach user context to Sentry error reports.

    Extracts the current user from the JWT token in the Authorization header
    and sets the Sentry user context for error attribution.

    This enables:
    - Identifying which user triggered an error
    - Filtering errors by user in Sentry dashboard
    - User impact analysis for error prioritization
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Try to extract user from JWT token
        try:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                # Import here to avoid circular imports
                from app.routers.auth import decode_access_token

                token_data = decode_access_token(token)
                if token_data and token_data.user_id:
                    set_user_context(
                        user_id=str(token_data.user_id),
                        email=token_data.email,
                    )
        except Exception:
            # Don't let user context extraction break the request
            pass

        response = await call_next(request)
        return response


def get_minio_client() -> Minio:
    """
    Create and return a MinIO client instance.

    Returns:
        Minio: Configured MinIO client.
    """
    settings = get_settings()
    return Minio(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


async def init_minio_bucket() -> None:
    """
    Initialize the MinIO bucket for evidence storage.

    Creates the configured bucket if it doesn't already exist.
    Logs the result of the operation.
    """
    settings = get_settings()
    client = get_minio_client()
    bucket_name = settings.minio_bucket

    try:
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            logger.info(f"Created MinIO bucket: {bucket_name}")
        else:
            logger.info(f"MinIO bucket already exists: {bucket_name}")
    except S3Error as e:
        logger.error(f"Failed to initialize MinIO bucket: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Handles startup and shutdown events for the FastAPI application.

    Startup:
        - Initializes MinIO bucket for evidence storage
        - Starts the workflow scheduler

    Shutdown:
        - Stops the workflow scheduler
        - Performs cleanup operations

    Args:
        app: The FastAPI application instance.

    Yields:
        None
    """
    # Startup
    logger.info("Starting AuditCaseOS API...")
    try:
        await init_minio_bucket()
        logger.info("MinIO initialization complete")
    except Exception as e:
        logger.warning(f"MinIO initialization skipped: {e}")

    # Start workflow scheduler
    try:
        from app.services.scheduler_service import scheduler_service
        scheduler_service.start()
        logger.info("Workflow scheduler started")
    except Exception as e:
        logger.warning(f"Scheduler initialization skipped: {e}")

    yield

    # Shutdown
    logger.info("Shutting down AuditCaseOS API...")

    # Stop workflow scheduler
    try:
        from app.services.scheduler_service import scheduler_service
        scheduler_service.stop()
        logger.info("Workflow scheduler stopped")
    except Exception as e:
        logger.warning(f"Error stopping scheduler: {e}")


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured FastAPI application instance.
    """
    settings = get_settings()

    # Initialize Sentry error tracking (before app creation for early error capture)
    # Source: https://docs.sentry.io/platforms/python/integrations/fastapi/
    sentry_enabled = setup_sentry(settings)
    if sentry_enabled:
        logger.info("Sentry error tracking enabled")
    else:
        logger.debug("Sentry disabled (no DSN configured)")

    # Conditionally disable docs in production
    # Source: FastAPI security best practices
    docs_url = None if settings.is_production else "/docs"
    redoc_url = None if settings.is_production else "/redoc"
    openapi_url = None if settings.is_production else "/openapi.json"

    app = FastAPI(
        title="AuditCaseOS API",
        description="Internal audit case management system with AI-powered analysis",
        version="0.8.1",
        lifespan=lifespan,
        debug=settings.debug,
        redirect_slashes=False,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )

    # Add rate limiter state and exception handler
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Add Sentry user context middleware (attaches user info to errors)
    if sentry_enabled:
        app.add_middleware(SentryUserContextMiddleware)

    # Add security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)

    # Configure CORS middleware with proper origins
    # In production, use specific origins from CORS_ORIGINS env var
    # Source: https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/11-Client-side_Testing/07-Testing_Cross_Origin_Resource_Sharing
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
        expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
    )

    # Import and include routers
    # These imports are done here to avoid circular imports
    # Note: Routers define their own prefixes and tags
    from app.routers import (
        ai,
        analytics,
        auth,
        cases,
        entities,
        evidence,
        health,
        nextcloud,
        notifications,
        onlyoffice,
        reports,
        scopes,
        search,
        sync,
        users,
        websocket,
        workflows,
    )

    app.include_router(health.router, tags=["Health"])
    app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])
    app.include_router(users.router, prefix="/api/v1", tags=["Users"])
    app.include_router(cases.router, prefix="/api/v1", tags=["Cases"])
    app.include_router(evidence.router, prefix="/api/v1", tags=["Evidence"])
    app.include_router(entities.router, prefix="/api/v1", tags=["Entities"])
    app.include_router(scopes.router, prefix="/api/v1", tags=["Scopes"])
    app.include_router(sync.router, prefix="/api/v1", tags=["Sync"])
    app.include_router(ai.router, prefix="/api/v1", tags=["AI"])
    app.include_router(analytics.router, prefix="/api/v1", tags=["Analytics"])
    app.include_router(notifications.router, prefix="/api/v1", tags=["Notifications"])
    app.include_router(workflows.router, prefix="/api/v1", tags=["Workflows"])
    app.include_router(reports.router, prefix="/api/v1", tags=["Reports"])
    app.include_router(search.router, prefix="/api/v1", tags=["Search"])
    app.include_router(nextcloud.router, prefix="/api/v1", tags=["Nextcloud"])
    app.include_router(onlyoffice.router, prefix="/api/v1", tags=["ONLYOFFICE"])
    app.include_router(websocket.router, prefix="/api/v1/ws", tags=["WebSocket"])

    # Setup Prometheus metrics (exposes /metrics endpoint)
    setup_prometheus(app)

    return app


# Create the application instance
app = create_application()


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, Any]:
    """
    Health check endpoint.

    Returns basic health status of the API service.
    Use this endpoint for container health checks and load balancer probes.

    Returns:
        dict: Health status with service name and status indicator.
    """
    return {
        "status": "healthy",
        "service": "auditcaseos-api",
        "version": "0.8.1",
    }
