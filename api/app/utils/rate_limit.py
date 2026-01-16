"""
Rate limiting utilities for AuditCaseOS API.

Uses slowapi for rate limiting based on client IP address.
Source: OWASP API Security Top 10 - API4:2023 Unrestricted Resource Consumption
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize rate limiter with IP-based key function
# This limiter instance is shared across all routers
limiter = Limiter(key_func=get_remote_address)
