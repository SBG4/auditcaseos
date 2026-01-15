"""AuditCaseOS API Routers.

This module exports all API routers for the AuditCaseOS application.
"""

from .ai import router as ai_router
from .cases import router as cases_router
from .entities import router as entities_router
from .evidence import router as evidence_router
from .reports import router as reports_router
from .scopes import router as scopes_router
from .sync import router as sync_router
from .users import router as users_router

__all__ = [
    "ai_router",
    "cases_router",
    "entities_router",
    "evidence_router",
    "reports_router",
    "scopes_router",
    "sync_router",
    "users_router",
]
