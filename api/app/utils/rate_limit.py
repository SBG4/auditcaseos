"""
Rate limiting utilities for AuditCaseOS API.

Uses slowapi for rate limiting based on client IP address.
Source: OWASP API Security Top 10 - API4:2023 Unrestricted Resource Consumption

Rate limits are configured via environment:
- development: 60/min general, 100/min auth
- testing: 20/min general, 5/min auth (for verification tests)
- production: 60/min general, 10/min auth
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

# Initialize rate limiter with IP-based key function
# This limiter instance is shared across all routers
limiter = Limiter(key_func=get_remote_address)


def get_auth_rate_limit() -> str:
    """Get the authentication rate limit string based on environment."""
    return f"{settings.effective_rate_limit_auth_per_minute}/minute"


def get_general_rate_limit() -> str:
    """Get the general rate limit string based on environment."""
    return f"{settings.effective_rate_limit_per_minute}/minute"


# Pre-computed rate limit strings for use in decorators
# Note: These are evaluated at import time
AUTH_RATE_LIMIT = get_auth_rate_limit()
GENERAL_RATE_LIMIT = get_general_rate_limit()
