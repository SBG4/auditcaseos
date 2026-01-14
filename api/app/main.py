"""
AuditCaseOS API - Main FastAPI Application.

This module initializes the FastAPI application with all routers,
middleware, and startup/shutdown events.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from minio import Minio
from minio.error import S3Error

from app.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


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

    Shutdown:
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

    yield

    # Shutdown
    logger.info("Shutting down AuditCaseOS API...")


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured FastAPI application instance.
    """
    settings = get_settings()

    app = FastAPI(
        title="AuditCaseOS API",
        description="Internal audit case management system with AI-powered analysis",
        version="0.1.0",
        lifespan=lifespan,
        debug=settings.debug,
    )

    # Configure CORS middleware for development
    # In production, restrict origins appropriately
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Import and include routers
    # These imports are done here to avoid circular imports
    # Note: Routers define their own prefixes and tags
    from app.routers import ai, cases, evidence, health, scopes, users

    app.include_router(health.router, tags=["Health"])
    app.include_router(users.router, prefix="/api/v1", tags=["Users"])
    app.include_router(cases.router, prefix="/api/v1", tags=["Cases"])
    app.include_router(evidence.router, prefix="/api/v1", tags=["Evidence"])
    app.include_router(scopes.router, prefix="/api/v1", tags=["Scopes"])
    app.include_router(ai.router, prefix="/api/v1", tags=["AI"])

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
        "version": "0.1.0",
    }
