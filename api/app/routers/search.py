"""Search router for AuditCaseOS API.

Provides endpoints for full-text and semantic search across
cases, evidence, findings, entities, and timeline events.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.auth import get_current_user_required
from app.schemas.common import CaseStatus, Severity
from app.schemas.search import (
    SearchEntityType,
    SearchMode,
    SearchResponse,
    SearchResultItem,
    SearchSuggestion,
    SearchSuggestResponse,
)
from app.services.search_service import search_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(get_current_user_required)]


@router.get(
    "",
    response_model=SearchResponse,
    summary="Search across all entities",
    description="Full-text and semantic search across cases, evidence, findings, entities, and timeline.",
)
async def search(
    db: DbSession,
    current_user: CurrentUser,
    q: str = Query(
        ..., min_length=2, max_length=500, description="Search query text"
    ),
    entity_types: list[SearchEntityType] = Query(
        default=[SearchEntityType.ALL],
        description="Entity types to search (case, evidence, finding, entity, timeline, all)",
    ),
    mode: SearchMode = Query(
        default=SearchMode.HYBRID,
        description="Search mode: keyword (ILIKE), semantic (vector), or hybrid (combined)",
    ),
    scope_codes: list[str] | None = Query(
        default=None, description="Filter by scope codes (e.g., FIN, IT, HR)"
    ),
    case_types: list[str] | None = Query(
        default=None, description="Filter by case types (USB, EMAIL, WEB, POLICY)"
    ),
    statuses: list[CaseStatus] | None = Query(
        default=None, description="Filter by case statuses"
    ),
    severities: list[Severity] | None = Query(
        default=None, description="Filter by severity levels"
    ),
    min_similarity: float = Query(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score for semantic search (0-1)",
    ),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Results per page"),
) -> SearchResponse:
    """
    Search across all entities in AuditCaseOS.

    This endpoint supports three search modes:

    - **keyword**: Fast ILIKE pattern matching across text fields
    - **semantic**: Vector similarity using AI embeddings (pgvector)
    - **hybrid**: Combined keyword and semantic search (recommended)

    Searchable content by entity type:

    - **Cases**: title, summary, description, case_id, subject_user
    - **Evidence**: filename, description, extracted_text (OCR)
    - **Findings**: title, description
    - **Entities**: extracted values (IPs, emails, employee IDs, hostnames)
    - **Timeline**: event type, description

    Hybrid mode combines results from both keyword and semantic search,
    deduplicating matches and applying weighted scoring (40% keyword, 60% semantic).

    Returns:
        SearchResponse with paginated results, counts by entity type, and search time
    """
    skip = (page - 1) * page_size

    # Convert enums to strings for service
    entity_type_strs = [et.value for et in entity_types]
    status_strs = [s.value for s in statuses] if statuses else None
    severity_strs = [s.value for s in severities] if severities else None

    results = await search_service.search(
        db=db,
        query=q,
        entity_types=entity_type_strs,
        mode=mode.value,
        scope_codes=scope_codes,
        case_types=case_types,
        statuses=status_strs,
        severities=severity_strs,
        min_similarity=min_similarity,
        skip=skip,
        limit=page_size,
    )

    # Build response items
    items = [SearchResultItem(**item) for item in results["items"]]
    total = results["total"]
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return SearchResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        query=q,
        mode=mode,
        entity_type_counts=results["entity_type_counts"],
        search_time_ms=results["search_time_ms"],
    )


@router.get(
    "/suggest",
    response_model=SearchSuggestResponse,
    summary="Get search suggestions",
    description="Autocomplete suggestions based on query prefix.",
)
async def search_suggest(
    db: DbSession,
    current_user: CurrentUser,
    q: str = Query(
        ..., min_length=1, max_length=100, description="Query prefix for suggestions"
    ),
    limit: int = Query(default=10, ge=1, le=50, description="Maximum suggestions"),
) -> SearchSuggestResponse:
    """
    Get search autocomplete suggestions.

    Returns suggestions based on query prefix from:

    - **Case IDs**: Matching case ID patterns (e.g., FIN-USB-0001)
    - **Case titles**: Matching case titles
    - **Entity values**: Extracted entities (IPs, emails, employee IDs)

    Suggestions are deduplicated and sorted by relevance.
    """
    suggestions = await search_service.suggest(db=db, query=q, limit=limit)

    return SearchSuggestResponse(
        suggestions=[SearchSuggestion(**s) for s in suggestions]
    )
