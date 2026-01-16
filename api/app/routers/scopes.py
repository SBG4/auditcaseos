"""Scopes router for AuditCaseOS API.

This module provides endpoints for managing audit scopes,
which represent organizational areas or departments that can be audited.

Scopes data is static and cached for 24 hours to minimize overhead.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import Field

from app.config import get_settings
from app.dependencies import get_cache
from app.schemas.common import BaseSchema
from app.services.cache_service import CacheService

router = APIRouter(prefix="/scopes", tags=["scopes"])

# Type alias for cache dependency
Cache = Annotated[CacheService, Depends(get_cache)]


# =============================================================================
# Schemas
# =============================================================================


class ScopeResponse(BaseSchema):
    """Schema for scope response."""

    code: str = Field(..., description="Scope code (e.g., FIN, HR, IT)")
    name: str = Field(..., description="Full scope name")
    description: str = Field(..., description="Scope description")


class ScopeListResponse(BaseSchema):
    """List of available scopes."""

    items: list[ScopeResponse]
    total: int


# =============================================================================
# Predefined Scopes
# =============================================================================

# Standard audit scopes - can be extended or loaded from database
PREDEFINED_SCOPES: list[ScopeResponse] = [
    ScopeResponse(
        code="FIN",
        name="Finance",
        description="Financial operations, accounting, and monetary transactions",
    ),
    ScopeResponse(
        code="HR",
        name="Human Resources",
        description="Employee data, HR processes, and personnel management",
    ),
    ScopeResponse(
        code="IT",
        name="Information Technology",
        description="IT systems, infrastructure, and technical operations",
    ),
    ScopeResponse(
        code="SEC",
        name="Security",
        description="Physical and information security, access controls",
    ),
    ScopeResponse(
        code="OPS",
        name="Operations",
        description="Business operations and process management",
    ),
    ScopeResponse(
        code="LEG",
        name="Legal",
        description="Legal compliance, contracts, and regulatory matters",
    ),
    ScopeResponse(
        code="PRO",
        name="Procurement",
        description="Purchasing, vendor management, and supply chain",
    ),
    ScopeResponse(
        code="MKT",
        name="Marketing",
        description="Marketing activities, campaigns, and communications",
    ),
    ScopeResponse(
        code="RND",
        name="Research & Development",
        description="R&D activities, innovation, and product development",
    ),
    ScopeResponse(
        code="QA",
        name="Quality Assurance",
        description="Quality control, testing, and compliance verification",
    ),
    ScopeResponse(
        code="ENV",
        name="Environmental",
        description="Environmental compliance and sustainability",
    ),
    ScopeResponse(
        code="SAF",
        name="Health & Safety",
        description="Workplace health and safety compliance",
    ),
    ScopeResponse(
        code="EXT",
        name="External",
        description="External partnerships, third-party relationships",
    ),
    ScopeResponse(
        code="GOV",
        name="Governance",
        description="Corporate governance and board-level matters",
    ),
    ScopeResponse(
        code="GEN",
        name="General",
        description="General audits not fitting other categories",
    ),
]


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "",
    response_model=ScopeListResponse,
    summary="List all scopes",
    description="Retrieve all available audit scopes.",
)
async def list_scopes(
    cache: Cache,
    search: str | None = Query(None, description="Search in code and name"),
) -> ScopeListResponse:
    """
    List all available audit scopes.

    Scopes represent organizational areas or departments that can be audited.
    Each scope has a short code (e.g., FIN, HR, IT) used in case IDs.

    Available scopes include:
    - **FIN** - Finance
    - **HR** - Human Resources
    - **IT** - Information Technology
    - **SEC** - Security
    - **OPS** - Operations
    - **LEG** - Legal
    - **PRO** - Procurement
    - **MKT** - Marketing
    - **RND** - Research & Development
    - **QA** - Quality Assurance
    - **ENV** - Environmental
    - **SAF** - Health & Safety
    - **EXT** - External
    - **GOV** - Governance
    - **GEN** - General

    - **search**: Optional search term to filter scopes

    Returns a list of all matching scopes.

    Results are cached for 24 hours (static data).
    """
    settings = get_settings()
    cache_key = f"cache:scopes:list:{search or 'all'}"

    async def compute():
        scopes = PREDEFINED_SCOPES

        # Filter by search term if provided
        if search:
            search_lower = search.lower()
            scopes = [
                scope
                for scope in scopes
                if search_lower in scope.code.lower()
                or search_lower in scope.name.lower()
                or search_lower in scope.description.lower()
            ]

        return ScopeListResponse(
            items=scopes,
            total=len(scopes),
        )

    result = await cache.get_or_compute(
        key=cache_key,
        compute_func=compute,
        ttl=settings.cache_scopes_ttl,
    )
    return ScopeListResponse(**result) if isinstance(result, dict) else result


@router.get(
    "/{scope_code}",
    response_model=ScopeResponse,
    summary="Get scope by code",
    description="Retrieve a specific scope by its code.",
)
async def get_scope(
    scope_code: str,
    cache: Cache,
) -> ScopeResponse:
    """
    Get a specific scope by its code.

    - **scope_code**: The scope code (e.g., FIN, HR, IT)

    Returns the scope details if found.

    Results are cached for 24 hours (static data).

    Raises:
        HTTPException: 404 if scope not found
    """
    from fastapi import HTTPException, status

    settings = get_settings()
    scope_code_upper = scope_code.upper()
    cache_key = f"cache:scopes:{scope_code_upper}"

    async def compute():
        for scope in PREDEFINED_SCOPES:
            if scope.code == scope_code_upper:
                return scope
        return None

    result = await cache.get_or_compute(
        key=cache_key,
        compute_func=compute,
        ttl=settings.cache_scopes_ttl,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scope with code '{scope_code}' not found",
        )

    return ScopeResponse(**result) if isinstance(result, dict) else result
