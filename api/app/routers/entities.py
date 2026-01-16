"""Entities router for AuditCaseOS API.

This module provides endpoints for managing and searching extracted entities
from case evidence (employee IDs, IP addresses, emails, hostnames, etc.).
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.auth import get_current_user_required
from app.schemas.entity import (
    EntityExtractionRequest,
    EntityExtractionResponse,
    EntityListResponse,
    EntitySearchResponse,
    EntityStoreRequest,
    EntityStoreResponse,
    EntitySummary,
    EntityType,
)
from app.services.case_service import case_service
from app.services.entity_service import entity_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/entities", tags=["entities"])


# Type aliases for dependency injection
DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(get_current_user_required)]


# =============================================================================
# Extraction Endpoints (No Auth Required for Testing)
# =============================================================================


@router.post(
    "/extract",
    response_model=EntityExtractionResponse,
    summary="Extract entities from text",
    description="Extract entities (IPs, emails, employee IDs, etc.) from provided text without storing.",
)
async def extract_entities(
    request: EntityExtractionRequest,
) -> EntityExtractionResponse:
    """
    Extract entities from text using regex patterns.

    This endpoint is useful for testing and previewing what entities
    would be extracted from a piece of text before storing them.

    Supported entity types:
    - employee_id: Employee identifiers (EMP-123456, E123456, etc.)
    - ip_address: IPv4 and IPv6 addresses
    - email: Email addresses
    - hostname: Computer/server names and domains
    - mac_address: MAC addresses
    - file_path: Windows and Unix file paths
    - usb_device: USB device identifiers
    """
    try:
        # Convert enum types to strings if provided
        entity_types = None
        if request.entity_types:
            entity_types = [et.value for et in request.entity_types]

        # Extract entities
        extracted = entity_service.extract_entities(
            text_content=request.text,
            entity_types=entity_types,
        )

        # Count total
        total = sum(len(values) for values in extracted.values())

        return EntityExtractionResponse(
            extracted_count=total,
            entities_by_type=extracted,
        )

    except Exception as e:
        logger.error(f"Failed to extract entities: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract entities: {e!s}",
        )


# =============================================================================
# Case Entity Endpoints
# =============================================================================


@router.post(
    "/store",
    response_model=EntityStoreResponse,
    summary="Extract and store entities",
    description="Extract entities from text and store them for a case.",
)
async def store_entities(
    request: EntityStoreRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> EntityStoreResponse:
    """
    Extract entities from text and store them associated with a case.

    This endpoint extracts entities using regex patterns and stores
    unique entities in the database linked to the specified case.
    Duplicate entities (same case + type + value) are not stored again,
    but their occurrence count is incremented.
    """
    try:
        # Verify case exists
        case_data = await case_service.get_case(db, request.case_id)
        if not case_data:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Case with ID '{request.case_id}' not found",
            )

        case_uuid = case_data["id"]

        # Extract and store entities
        result = await entity_service.extract_and_store_from_evidence(
            db=db,
            case_id=case_uuid,
            evidence_id=request.evidence_id,
            text_content=request.text,
            source=request.source or "manual_extraction",
        )

        return EntityStoreResponse(
            extracted_count=result["extracted_count"],
            stored_count=result["stored_count"],
            entities_by_type=result["entities_by_type"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to store entities: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store entities: {e!s}",
        )


@router.get(
    "/case/{case_id}",
    response_model=EntityListResponse,
    summary="Get entities for a case",
    description="Retrieve all extracted entities for a specific case.",
)
async def get_case_entities(
    db: DbSession,
    current_user: CurrentUser,
    case_id: str = Path(..., description="Case ID (SCOPE-TYPE-SEQ format or UUID)"),
    entity_type: EntityType | None = Query(None, description="Filter by entity type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
) -> EntityListResponse:
    """
    Get all extracted entities for a case with optional filtering.

    Returns a paginated list of entities including:
    - Entity type and value
    - Evidence items where it was found
    - Occurrence count
    """
    try:
        # Verify case exists
        case_data = await case_service.get_case(db, case_id)
        if not case_data:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Case with ID '{case_id}' not found",
            )

        case_uuid = case_data["id"]
        skip = (page - 1) * page_size

        # Get filter value
        type_filter = entity_type.value if entity_type else None

        # Get total and entities
        total = await entity_service.count_case_entities(
            db=db,
            case_id=case_uuid,
            entity_type=type_filter,
        )

        entities = await entity_service.get_case_entities(
            db=db,
            case_id=case_uuid,
            entity_type=type_filter,
            skip=skip,
            limit=page_size,
        )

        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

        return EntityListResponse(
            items=entities,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get entities for case {case_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve entities",
        )


@router.get(
    "/case/{case_id}/summary",
    response_model=list[EntitySummary],
    summary="Get entity summary for a case",
    description="Get counts of entities by type for a case.",
)
async def get_entity_summary(
    db: DbSession,
    current_user: CurrentUser,
    case_id: str = Path(..., description="Case ID"),
) -> list[EntitySummary]:
    """
    Get a summary of entity counts by type for a case.

    Useful for dashboards and quick overviews of what entities
    have been extracted from case evidence.
    """
    try:
        # Verify case exists
        case_data = await case_service.get_case(db, case_id)
        if not case_data:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Case with ID '{case_id}' not found",
            )

        case_uuid = case_data["id"]

        # Get summary
        summary = await entity_service.get_entity_summary(db, case_uuid)

        return [
            EntitySummary(entity_type=EntityType(et), count=count)
            for et, count in summary.items()
            if et in EntityType._value2member_map_
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get entity summary for case {case_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve entity summary",
        )


# =============================================================================
# Search Endpoints
# =============================================================================


@router.get(
    "/search",
    response_model=list[EntitySearchResponse],
    summary="Search entities across cases",
    description="Search for entities by value pattern across all cases.",
)
async def search_entities(
    db: DbSession,
    current_user: CurrentUser,
    q: str = Query(..., min_length=2, max_length=200, description="Search query"),
    entity_type: EntityType | None = Query(None, description="Filter by entity type"),
    limit: int = Query(50, ge=1, le=100, description="Max results"),
) -> list[EntitySearchResponse]:
    """
    Search for entities across all cases.

    This is useful for finding related cases that contain the same
    IP address, email, employee ID, or other entity.

    The search uses pattern matching (ILIKE) so partial matches work.
    """
    try:
        type_filter = entity_type.value if entity_type else None

        results = await entity_service.search_entities(
            db=db,
            value_pattern=q,
            entity_type=type_filter,
            limit=limit,
        )

        return results

    except Exception as e:
        logger.error(f"Failed to search entities: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search entities",
        )
