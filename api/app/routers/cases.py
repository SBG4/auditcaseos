"""Cases router for AuditCaseOS API.

This module provides endpoints for managing audit cases, including
CRUD operations, timeline events, and findings.

Cache invalidation is performed on case create/update/delete to ensure
analytics data stays fresh.
"""

import logging
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi import status as http_status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_cache
from app.routers.auth import get_current_user_required
from app.schemas.case import (
    CaseCreate,
    CaseListResponse,
    CaseResponse,
    CaseUpdate,
)
from app.schemas.common import (
    CaseStatus,
    CaseType,
    MessageResponse,
    Severity,
)
from app.services.audit_service import audit_service
from app.services.cache_service import CacheService
from app.services.case_service import case_service
from app.services.websocket_service import connection_manager
from app.services.workflow_executor import workflow_executor
from app.services.workflow_service import workflow_service

logger = logging.getLogger(__name__)


# =============================================================================
# Workflow Trigger Helper
# =============================================================================


async def trigger_workflows(
    db: AsyncSession,
    trigger_type: str,
    case_data: dict[str, Any],
    trigger_data: dict[str, Any],
    triggered_by: str,
) -> None:
    """
    Trigger matching workflow rules for a case event.

    This function is non-blocking - workflow failures don't affect the main operation.
    """
    try:
        # Get matching rules
        rules = await workflow_service.get_matching_rules(
            db=db,
            trigger_type=trigger_type,
            case_data=case_data,
            trigger_data=trigger_data,
        )

        for rule in rules:
            try:
                # Execute rule actions
                result = await workflow_executor.execute_rule(
                    db=db,
                    rule=rule,
                    case_data=case_data,
                    trigger_data=trigger_data,
                    triggered_by=triggered_by,
                )

                # Log execution
                await workflow_service.log_execution(
                    db=db,
                    rule=rule,
                    case_data=case_data,
                    trigger_type=trigger_type,
                    trigger_data=trigger_data,
                    actions_executed=result["actions_executed"],
                    success=result["success"],
                    error_message=result.get("error_message"),
                    triggered_by=triggered_by,
                )

                logger.info(
                    f"Workflow '{rule['name']}' executed for case {case_data.get('case_id')} "
                    f"- success: {result['success']}"
                )

            except Exception as rule_error:
                logger.error(f"Failed to execute workflow rule {rule.get('id')}: {rule_error}")

    except Exception as e:
        logger.error(f"Failed to trigger workflows: {e}")

router = APIRouter(prefix="/cases", tags=["cases"])


# =============================================================================
# Dependencies
# =============================================================================


# Type aliases for dependency injection
DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(get_current_user_required)]
Cache = Annotated[CacheService, Depends(get_cache)]


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "",
    response_model=CaseListResponse,
    summary="List all cases",
    description="Retrieve a paginated list of audit cases with optional filtering.",
)
async def list_cases(
    db: DbSession,
    current_user: CurrentUser,
    status: CaseStatus | None = Query(None, description="Filter by case status"),
    case_type: CaseType | None = Query(None, alias="type", description="Filter by case type"),
    scope: str | None = Query(None, description="Filter by scope code"),
    severity: Severity | None = Query(None, description="Filter by severity"),
    search: str | None = Query(None, min_length=2, description="Search in title, summary, description, case_id"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> CaseListResponse:
    """
    List all audit cases with filtering and pagination.

    - **status**: Filter by case status (OPEN, IN_PROGRESS, PENDING_REVIEW, CLOSED, ARCHIVED)
    - **type**: Filter by case type (USB, EMAIL, WEB, POLICY)
    - **scope**: Filter by scope code (FIN, HR, IT, SEC, etc.)
    - **severity**: Filter by severity (LOW, MEDIUM, HIGH, CRITICAL)
    - **search**: Search term to match against title, summary, description, and case_id
    - **page**: Page number (starts at 1)
    - **page_size**: Number of items per page (max 100)

    Returns a paginated list of cases matching the filters.
    """
    try:
        # Build filters dict
        filters: dict[str, Any] = {}
        if status:
            filters["status"] = status.value
        if case_type:
            filters["case_type"] = case_type.value
        if scope:
            filters["scope_code"] = scope
        if severity:
            filters["severity"] = severity.value
        if search:
            filters["search"] = search

        # Calculate offset
        skip = (page - 1) * page_size

        # Get total count and cases
        total = await case_service.count_cases(db, filters)
        cases = await case_service.list_cases(db, filters, skip, page_size)

        # Build response items with user info and counts
        items = []
        for case_data in cases:
            case_response = await case_service.build_case_response(db, case_data)
            items.append(case_response)

        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

        return CaseListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    except Exception as e:
        logger.error(f"Failed to list cases: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cases",
        )


@router.post(
    "",
    response_model=CaseResponse,
    status_code=http_status.HTTP_201_CREATED,
    summary="Create a new case",
    description="Create a new audit case with auto-generated case ID.",
)
async def create_case(
    case_data: CaseCreate,
    db: DbSession,
    request: Request,
    current_user: CurrentUser,
    cache: Cache,
) -> CaseResponse:
    """
    Create a new audit case.

    The case ID is automatically generated in the format SCOPE-TYPE-SEQ,
    where SEQ is a sequential number for the scope/type combination.

    Example: FIN-USB-0001 for the first USB case in Finance scope.
    """
    try:
        # Get owner ID from authenticated user
        owner_id = current_user["id"]

        # Verify scope exists
        scope_query = text("SELECT code FROM scopes WHERE code = :code")
        scope_result = await db.execute(scope_query, {"code": case_data.scope_code})
        if not scope_result.fetchone():
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid scope code: {case_data.scope_code}",
            )

        # Build case data dict
        case_dict = {
            "scope_code": case_data.scope_code,
            "case_type": case_data.case_type.value,
            "title": case_data.title,
            "summary": case_data.summary,
            "description": case_data.description,
            "severity": case_data.severity.value if case_data.severity else "MEDIUM",
            "subject_user": case_data.subject_user,
            "subject_computer": case_data.subject_computer,
            "subject_devices": case_data.subject_devices,
            "related_users": case_data.related_users,
            "incident_date": case_data.incident_date,
            "tags": case_data.tags,
        }

        # Create case
        created_case = await case_service.create_case(db, case_dict, owner_id)

        if not created_case:
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create case",
            )

        # Log audit event
        client_ip = request.client.host if request.client else None
        await audit_service.log_create(
            db=db,
            entity_type="case",
            entity_id=created_case["id"],
            user_id=owner_id,
            new_values={"case_id": created_case["case_id"], "title": created_case["title"]},
            user_ip=client_ip,
        )

        # Create Nextcloud folder structure for the case (non-blocking)
        try:
            from app.services.nextcloud_service import nextcloud_service
            await nextcloud_service.create_case_folder(created_case["case_id"])
            logger.info(f"Created Nextcloud folder for case {created_case['case_id']}")
        except Exception as e:
            # Don't fail case creation if Nextcloud is unavailable
            logger.warning(f"Failed to create Nextcloud folder for case {created_case['case_id']}: {e}")

        # Build full response
        response = await case_service.build_case_response(db, created_case)

        # Broadcast new case creation (for dashboard updates)
        try:
            await connection_manager.send_case_update(
                case_id=created_case["case_id"],
                update_type="case_created",
                data={
                    "case_id": created_case["case_id"],
                    "title": created_case["title"],
                    "status": created_case.get("status"),
                    "severity": created_case.get("severity"),
                },
                triggered_by=str(owner_id),
            )
        except Exception as ws_error:
            logger.debug(f"WebSocket broadcast skipped: {ws_error}")

        # Trigger workflows for case creation
        try:
            await trigger_workflows(
                db=db,
                trigger_type="EVENT",
                case_data=created_case,
                trigger_data={"event": "case_created"},
                triggered_by="event:case_created",
            )
        except Exception as wf_error:
            logger.debug(f"Workflow trigger skipped: {wf_error}")

        # Invalidate analytics cache (case counts changed)
        try:
            await cache.delete_pattern("cache:analytics:*")
        except Exception as cache_error:
            logger.debug(f"Cache invalidation skipped: {cache_error}")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create case: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create case: {e!s}",
        )


@router.get(
    "/{case_id}",
    response_model=CaseResponse,
    summary="Get case by ID",
    description="Retrieve a specific case by its case ID.",
)
async def get_case(
    db: DbSession,
    request: Request,
    current_user: CurrentUser,
    case_id: str = Path(..., description="Case ID in format SCOPE-TYPE-SEQ (e.g., FIN-USB-0001) or UUID"),
) -> CaseResponse:
    """
    Get a specific audit case by its case ID.

    The case_id can be either:
    - Human-readable format: SCOPE-TYPE-SEQ (e.g., FIN-USB-0001)
    - Internal UUID

    Returns the case details if found.
    """
    try:
        case_data = await case_service.get_case(db, case_id)

        if not case_data:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Case with ID '{case_id}' not found",
            )

        # Log view event
        owner_id = current_user["id"]
        client_ip = request.client.host if request.client else None
        try:
            await audit_service.log_view(
                db=db,
                entity_type="case",
                entity_id=case_data["id"],
                user_id=owner_id,
                user_ip=client_ip,
            )
        except Exception as audit_error:
            logger.warning(f"Failed to log view event: {audit_error}")

        # Build full response
        response = await case_service.build_case_response(db, case_data)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get case {case_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve case",
        )


@router.patch(
    "/{case_id}",
    response_model=CaseResponse,
    summary="Update case",
    description="Update an existing case's details.",
)
async def update_case(
    case_update: CaseUpdate,
    db: DbSession,
    request: Request,
    current_user: CurrentUser,
    cache: Cache,
    case_id: str = Path(..., description="Case ID in format SCOPE-TYPE-SEQ or UUID"),
) -> CaseResponse:
    """
    Update an existing audit case.

    Only provided fields will be updated. All fields are optional.
    """
    try:
        # Get existing case first
        existing_case = await case_service.get_case(db, case_id)
        if not existing_case:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Case with ID '{case_id}' not found",
            )

        # Build update dict from provided fields
        update_dict: dict[str, Any] = {}
        update_data = case_update.model_dump(exclude_unset=True)

        # Map field names
        field_mapping = {
            "assigned_to_id": "assigned_to",
        }

        for key, value in update_data.items():
            if value is not None:
                mapped_key = field_mapping.get(key, key)
                # Convert enums to values
                if hasattr(value, "value"):
                    update_dict[mapped_key] = value.value
                else:
                    update_dict[mapped_key] = value

        if not update_dict:
            # No updates provided, return existing case
            response = await case_service.build_case_response(db, existing_case)
            return response

        # Update case
        updated_case = await case_service.update_case(db, case_id, update_dict)

        if not updated_case:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Case with ID '{case_id}' not found",
            )

        # Log audit event
        client_ip = request.client.host if request.client else None
        await audit_service.log_update(
            db=db,
            entity_type="case",
            entity_id=updated_case["id"],
            user_id=current_user["id"],
            old_values={"status": str(existing_case.get("status")), "severity": str(existing_case.get("severity"))},
            new_values=update_dict,
            user_ip=client_ip,
        )

        # Build full response
        response = await case_service.build_case_response(db, updated_case)

        # Broadcast case update to viewers
        try:
            await connection_manager.send_case_update(
                case_id=updated_case["case_id"],
                update_type="case_updated",
                data={
                    "case_id": updated_case["case_id"],
                    "updated_fields": list(update_dict.keys()),
                    "title": updated_case.get("title"),
                    "status": updated_case.get("status"),
                    "severity": updated_case.get("severity"),
                },
                triggered_by=str(current_user["id"]),
            )
        except Exception as ws_error:
            logger.debug(f"WebSocket broadcast skipped: {ws_error}")

        # Trigger workflows for case update
        try:
            # Check if status changed - trigger STATUS_CHANGE rules
            old_status = str(existing_case.get("status"))
            new_status = updated_case.get("status")
            if "status" in update_dict and old_status != new_status:
                await trigger_workflows(
                    db=db,
                    trigger_type="STATUS_CHANGE",
                    case_data=updated_case,
                    trigger_data={
                        "old_status": old_status,
                        "new_status": new_status,
                    },
                    triggered_by=f"status_change:{old_status}->{new_status}",
                )

            # Also trigger EVENT rules for case_updated
            await trigger_workflows(
                db=db,
                trigger_type="EVENT",
                case_data=updated_case,
                trigger_data={
                    "event": "case_updated",
                    "updated_fields": list(update_dict.keys()),
                },
                triggered_by="event:case_updated",
            )
        except Exception as wf_error:
            logger.debug(f"Workflow trigger skipped: {wf_error}")

        # Invalidate analytics cache (case data changed)
        try:
            await cache.delete_pattern("cache:analytics:*")
        except Exception as cache_error:
            logger.debug(f"Cache invalidation skipped: {cache_error}")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update case {case_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update case: {e!s}",
        )


@router.delete(
    "/{case_id}",
    response_model=MessageResponse,
    summary="Delete case (soft delete)",
    description="Soft delete a case by setting its status to ARCHIVED.",
)
async def delete_case(
    db: DbSession,
    request: Request,
    current_user: CurrentUser,
    cache: Cache,
    case_id: str = Path(..., description="Case ID in format SCOPE-TYPE-SEQ or UUID"),
) -> MessageResponse:
    """
    Soft delete an audit case.

    This sets the case status to ARCHIVED rather than permanently deleting it.
    Archived cases can still be retrieved but won't appear in default listings.
    """
    try:
        # Get existing case first
        existing_case = await case_service.get_case(db, case_id)
        if not existing_case:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Case with ID '{case_id}' not found",
            )

        # Soft delete by updating status to ARCHIVED
        updated_case = await case_service.update_case(
            db, case_id, {"status": "ARCHIVED", "closed_at": datetime.utcnow()}
        )

        if not updated_case:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Case with ID '{case_id}' not found",
            )

        # Log audit event
        client_ip = request.client.host if request.client else None
        await audit_service.log_delete(
            db=db,
            entity_type="case",
            entity_id=existing_case["id"],
            user_id=current_user["id"],
            old_values={"case_id": existing_case["case_id"], "status": str(existing_case.get("status"))},
            user_ip=client_ip,
        )

        # Invalidate analytics cache (case archived)
        try:
            await cache.delete_pattern("cache:analytics:*")
        except Exception as cache_error:
            logger.debug(f"Cache invalidation skipped: {cache_error}")

        return MessageResponse(
            message=f"Case '{existing_case['case_id']}' has been archived",
            details={"case_id": existing_case["case_id"], "status": "ARCHIVED"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete case {case_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to archive case",
        )


# =============================================================================
# Timeline Events Endpoints
# =============================================================================


@router.get(
    "/{case_id}/timeline",
    summary="Get case timeline",
    description="Retrieve all timeline events for a case.",
)
async def get_case_timeline(
    db: DbSession,
    case_id: str = Path(..., description="Case ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> dict:
    """Get all timeline events for a specific case."""
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

        # Get timeline events
        query = text("""
            SELECT t.*, u.full_name as created_by_name
            FROM timeline_events t
            LEFT JOIN users u ON t.created_by = u.id
            WHERE t.case_id = :case_uuid
            ORDER BY t.event_time DESC
            OFFSET :skip LIMIT :limit
        """)
        result = await db.execute(query, {"case_uuid": str(case_uuid), "skip": skip, "limit": page_size})
        rows = result.fetchall()

        # Get total count
        count_query = text("SELECT COUNT(*) FROM timeline_events WHERE case_id = :case_uuid")
        count_result = await db.execute(count_query, {"case_uuid": str(case_uuid)})
        total = count_result.scalar() or 0

        items = [dict(row._mapping) for row in rows]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get timeline for case {case_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve timeline",
        )


@router.post(
    "/{case_id}/timeline",
    status_code=http_status.HTTP_201_CREATED,
    summary="Add timeline event",
    description="Add a new event to the case timeline.",
)
async def add_timeline_event(
    db: DbSession,
    request: Request,
    current_user: CurrentUser,
    case_id: str = Path(..., description="Case ID"),
    event_type: str = Query(..., max_length=100),
    description: str = Query(..., max_length=2000),
    event_time: datetime | None = None,
    source: str | None = Query(None, max_length=255),
) -> dict:
    """Add a new event to a case's timeline."""
    try:
        # Verify case exists
        case_data = await case_service.get_case(db, case_id)
        if not case_data:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Case with ID '{case_id}' not found",
            )

        case_uuid = case_data["id"]
        user_id = current_user["id"]
        event_time = event_time or datetime.utcnow()

        # Insert timeline event
        query = text("""
            INSERT INTO timeline_events (case_id, event_time, event_type, description, source, created_by)
            VALUES (:case_id, :event_time, :event_type, :description, :source, :created_by)
            RETURNING *
        """)
        result = await db.execute(query, {
            "case_id": str(case_uuid),
            "event_time": event_time,
            "event_type": event_type,
            "description": description,
            "source": source,
            "created_by": str(user_id),
        })
        await db.commit()

        row = result.fetchone()
        event_data = dict(row._mapping) if row else {}

        # Broadcast timeline event to case viewers
        try:
            await connection_manager.send_case_update(
                case_id=case_data["case_id"],
                update_type="timeline_added",
                data={
                    "event_id": str(event_data.get("id")),
                    "event_type": event_type,
                    "description": description[:100],  # Truncate for notification
                    "event_time": str(event_time),
                },
                triggered_by=str(user_id),
            )
        except Exception as ws_error:
            logger.debug(f"WebSocket broadcast skipped: {ws_error}")

        return event_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add timeline event: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add timeline event",
        )


# =============================================================================
# Findings Endpoints
# =============================================================================


@router.get(
    "/{case_id}/findings",
    summary="Get case findings",
    description="Retrieve all findings for a case.",
)
async def get_case_findings(
    db: DbSession,
    case_id: str = Path(..., description="Case ID"),
) -> dict:
    """Get all findings for a specific case."""
    try:
        # Verify case exists
        case_data = await case_service.get_case(db, case_id)
        if not case_data:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Case with ID '{case_id}' not found",
            )

        case_uuid = case_data["id"]

        # Get findings
        query = text("""
            SELECT f.*, u.full_name as created_by_name
            FROM findings f
            LEFT JOIN users u ON f.created_by = u.id
            WHERE f.case_id = :case_uuid
            ORDER BY
                CASE f.severity
                    WHEN 'CRITICAL' THEN 1
                    WHEN 'HIGH' THEN 2
                    WHEN 'MEDIUM' THEN 3
                    WHEN 'LOW' THEN 4
                END,
                f.created_at DESC
        """)
        result = await db.execute(query, {"case_uuid": str(case_uuid)})
        rows = result.fetchall()

        items = [dict(row._mapping) for row in rows]

        return {
            "items": items,
            "total": len(items),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get findings for case {case_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve findings",
        )


@router.post(
    "/{case_id}/findings",
    status_code=http_status.HTTP_201_CREATED,
    summary="Add finding",
    description="Add a new finding to the case.",
)
async def add_finding(
    db: DbSession,
    request: Request,
    current_user: CurrentUser,
    case_id: str = Path(..., description="Case ID"),
    title: str = Query(..., min_length=1, max_length=500),
    description: str = Query(..., min_length=1, max_length=5000),
    severity: Severity = Query(Severity.MEDIUM),
    evidence_ids: list[UUID] | None = Query(None),
) -> dict:
    """Add a new finding to a case."""
    try:
        # Verify case exists
        case_data = await case_service.get_case(db, case_id)
        if not case_data:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Case with ID '{case_id}' not found",
            )

        case_uuid = case_data["id"]
        user_id = current_user["id"]

        # Insert finding
        evidence_ids_str = [str(eid) for eid in evidence_ids] if evidence_ids else None
        query = text("""
            INSERT INTO findings (case_id, title, description, severity, evidence_ids, created_by)
            VALUES (:case_id, :title, :description, CAST(:severity AS severity_level), :evidence_ids, :created_by)
            RETURNING *
        """)
        result = await db.execute(query, {
            "case_id": str(case_uuid),
            "title": title,
            "description": description,
            "severity": severity.value,
            "evidence_ids": evidence_ids_str,
            "created_by": str(user_id),
        })
        await db.commit()

        row = result.fetchone()
        finding_data = dict(row._mapping) if row else {}

        # Log audit event
        client_ip = request.client.host if request.client else None
        await audit_service.log_create(
            db=db,
            entity_type="finding",
            entity_id=finding_data.get("id"),
            user_id=user_id,
            new_values={"title": title, "severity": severity.value, "case_id": case_data["case_id"]},
            user_ip=client_ip,
        )

        # Broadcast finding to case viewers
        try:
            await connection_manager.send_case_update(
                case_id=case_data["case_id"],
                update_type="finding_added",
                data={
                    "finding_id": str(finding_data.get("id")),
                    "title": title,
                    "severity": severity.value,
                },
                triggered_by=str(user_id),
            )
        except Exception as ws_error:
            logger.debug(f"WebSocket broadcast skipped: {ws_error}")

        # Trigger workflows for finding added
        try:
            await trigger_workflows(
                db=db,
                trigger_type="EVENT",
                case_data=case_data,
                trigger_data={
                    "event": "finding_added",
                    "finding_id": str(finding_data.get("id")),
                    "finding_title": title,
                    "finding_severity": severity.value,
                },
                triggered_by="event:finding_added",
            )
        except Exception as wf_error:
            logger.debug(f"Workflow trigger skipped: {wf_error}")

        return finding_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add finding: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add finding: {e!s}",
        )
