"""
Application configuration using Pydantic Settings.

All configuration values are loaded from environment variables with sensible defaults
for local development.
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Attributes:
        app_name: The name of the application.
        debug: Enable debug mode for development.
        secret_key: Secret key for signing tokens and sessions.
        database_url: PostgreSQL async connection URL.
        minio_endpoint: MinIO server endpoint (host:port).
        minio_access_key: MinIO access key for authentication.
        minio_secret_key: MinIO secret key for authentication.
        minio_bucket: Default bucket name for evidence storage.
        minio_secure: Use HTTPS for MinIO connections.
        ollama_host: Ollama API host URL for LLM inference.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application settings
    app_name: str = "AuditCaseOS"
    debug: bool = False
    secret_key: str = "change-me-in-production"

    # Database settings (DATABASE_URL from docker-compose)
    database_url: str = "postgresql+asyncpg://auditcaseos:auditcaseos_secret@postgres:5432/auditcaseos"

    # MinIO settings
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "evidence"
    minio_secure: bool = False

    # Ollama settings
    ollama_host: str = "http://localhost:11434"

    @property
    def async_database_url(self) -> str:
        """Return the database URL configured for async operations."""
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings.

    Uses LRU cache to ensure settings are only loaded once from environment
    variables and reused throughout the application lifecycle.

    Returns:
        Settings: The application settings instance.
    """
    return Settings()
