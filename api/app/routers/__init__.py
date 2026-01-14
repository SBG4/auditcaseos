"""AuditCaseOS API Routers.

This module exports all API routers for the AuditCaseOS application.
"""

from .ai import router as ai_router
from .cases import router as cases_router
from .evidence import router as evidence_router
from .scopes import router as scopes_router
from .users import router as users_router

__all__ = [
    "ai_router",
    "cases_router",
    "evidence_router",
    "scopes_router",
    "users_router",
]
