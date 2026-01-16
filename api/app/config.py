"""
Application configuration using Pydantic Settings.

All configuration values are loaded from environment variables with sensible defaults
for local development.

Secrets can be loaded from Docker secret files (/run/secrets/) when available,
falling back to environment variables for development.
"""

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def read_secret(name: str, default: str | None = None) -> str | None:
    """
    Read a secret from Docker secret file or fall back to environment variable.

    Docker Compose secrets are mounted to /run/secrets/<name>.
    This function checks for the file first, then falls back to env var.

    Args:
        name: The secret name (used as filename and env var name).
        default: Default value if neither file nor env var exists.

    Returns:
        The secret value, or default if not found.
    """
    # Check Docker secret file first (production pattern)
    secret_path = Path(f"/run/secrets/{name}")
    if secret_path.exists():
        return secret_path.read_text().strip()

    # Fall back to environment variable (development pattern)
    env_value = os.getenv(name.upper())
    if env_value is not None:
        return env_value

    return default


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Secrets are loaded with priority:
    1. Docker secret files (/run/secrets/<name>) - for production
    2. Environment variables - for development
    3. Default values - for local testing only

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

    def __init__(self, **kwargs):
        """Initialize settings, loading secrets from files if available."""
        super().__init__(**kwargs)
        # Override with Docker secrets if available
        self._load_secrets_from_files()

    def _load_secrets_from_files(self) -> None:
        """Load sensitive settings from Docker secret files if they exist."""
        secret_mappings = {
            "jwt_secret": "secret_key",
            "jwt_secret": "SECRET_KEY",
            "postgres_password": None,  # Used in database_url
            "minio_password": "minio_secret_key",
            "paperless_secret": None,  # Not directly used
            "paperless_admin_pass": None,  # Not directly used
            "nextcloud_admin_pass": "nextcloud_admin_password",
            "onlyoffice_jwt": "onlyoffice_jwt_secret",
        }

        for secret_name, attr_name in secret_mappings.items():
            secret_value = read_secret(secret_name)
            if secret_value and attr_name:
                object.__setattr__(self, attr_name, secret_value)

        # Special handling for database_url (contains password)
        db_password = read_secret("postgres_password")
        if db_password and "auditcaseos_secret" in self.database_url:
            new_url = self.database_url.replace("auditcaseos_secret", db_password)
            object.__setattr__(self, "database_url", new_url)

    # Application settings
    app_name: str = "AuditCaseOS"
    debug: bool = False
    secret_key: str = "change-me-in-production"
    environment: str = "development"  # development, staging, production

    # CORS settings - comma-separated list of allowed origins
    # In production, set to actual frontend URL(s)
    cors_origins: str = "http://localhost:13000,http://localhost:3000"

    # Rate limiting settings (requests per minute)
    rate_limit_per_minute: int = 60
    rate_limit_auth_per_minute: int = 10  # Stricter for auth endpoints

    # JWT settings
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    SECRET_KEY: str = "change-me-in-production"  # Alias for JWT signing

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a list."""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    # Database settings (DATABASE_URL from docker-compose)
    database_url: str = "postgresql+asyncpg://auditcaseos:auditcaseos_secret@postgres:5432/auditcaseos"

    # MinIO settings
    # INTERNAL: Used by API container to reach MinIO
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "evidence"
    minio_secure: bool = False

    # Ollama settings
    # INTERNAL: Used by API container to reach Ollama
    ollama_host: str = "http://ollama:11434"

    # Paperless-ngx settings
    # INTERNAL: Used by API container to reach Paperless
    paperless_url: str = "http://paperless:8000"
    paperless_api_token: str = ""

    # Nextcloud settings
    # INTERNAL: Used by API container for server-to-server communication
    nextcloud_url: str = "http://nextcloud"
    # EXTERNAL: Used by browsers to access Nextcloud (set via NEXTCLOUD_EXTERNAL_URL env var)
    nextcloud_external_url: str = "http://localhost:18081"
    nextcloud_admin_user: str = "admin"
    nextcloud_admin_password: str = "admin123"

    # ONLYOFFICE settings
    # EXTERNAL: Used by browsers to access ONLYOFFICE Document Server
    onlyoffice_url: str = "http://localhost:18082"
    # INTERNAL: Used by API/Nextcloud for server-to-server communication
    onlyoffice_internal_url: str = "http://onlyoffice"
    onlyoffice_jwt_secret: str = "auditcaseos-onlyoffice-secret"

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


# Singleton settings instance for easy import
settings = get_settings()
