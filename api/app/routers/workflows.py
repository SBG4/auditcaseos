"""Workflow automation router for AuditCaseOS API.

This module provides endpoints for managing workflow rules and actions.
Most endpoints require admin access.
"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.auth import get_admin_user, get_current_user_required
from app.schemas.common import MessageResponse
from app.schemas.workflow import (
    WorkflowActionCreate,
    WorkflowActionResponse,
    WorkflowActionUpdate,
    WorkflowHistoryListResponse,
    WorkflowHistoryResponse,
    WorkflowRuleCreate,
    WorkflowRuleListResponse,
    WorkflowRuleResponse,
    WorkflowRuleToggle,
    WorkflowRuleUpdate,
)
from app.services.audit_service import audit_service
from app.services.workflow_executor import workflow_executor
from app.services.workflow_service import workflow_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflows", tags=["workflows"])

# Type aliases
DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(get_current_user_required)]
AdminUser = Annotated[dict, Depends(get_admin_user)]


# =============================================================================
# WORKFLOW RULES ENDPOINTS
# =============================================================================


@router.get(
    "/rules",
    response_model=WorkflowRuleListResponse,
    summary="List workflow rules",
)
async def list_rules(
    db: DbSession,
    current_user: CurrentUser,
    is_enabled: bool | None = Query(None, description="Filter by enabled status"),
    trigger_type: str | None = Query(None, description="Filter by trigger type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
) -> WorkflowRuleListResponse:
    """
    List all workflow rules with optional filtering.

    Accessible to all authenticated users for visibility.
    """
    skip = (page - 1) * page_size
    filters = {}

    if is_enabled is not None:
        filters["is_enabled"] = is_enabled
    if trigger_type:
        filters["trigger_type"] = trigger_type

    rules, total = await workflow_service.list_rules(
        db=db,
        filters=filters,
        skip=skip,
        limit=page_size,
    )

    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return WorkflowRuleListResponse(
        items=rules,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "/rules",
    response_model=WorkflowRuleResponse,
    status_code=http_status.HTTP_201_CREATED,
    summary="Create workflow rule",
)
async def create_rule(
    rule_data: WorkflowRuleCreate,
    db: DbSession,
    admin_user: AdminUser,
) -> WorkflowRuleResponse:
    """
    Create a new workflow rule.

    Admin access required.
    """
    rule_dict = rule_data.model_dump()

    rule = await workflow_service.create_rule(
        db=db,
        rule_data=rule_dict,
        created_by=admin_user["id"],
    )

    # Audit log
    await audit_service.log_create(
        db=db,
        entity_type="workflow_rule",
        entity_id=rule["id"],
        user_id=admin_user["id"],
        new_values={"name": rule["name"], "trigger_type": rule["trigger_type"]},
    )

    logger.info(f"Created workflow rule: {rule['name']} by {admin_user['username']}")

    return WorkflowRuleResponse(**rule)


@router.get(
    "/rules/{rule_id}",
    response_model=WorkflowRuleResponse,
    summary="Get workflow rule",
)
async def get_rule(
    rule_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> WorkflowRuleResponse:
    """
    Get a workflow rule by ID.
    """
    rule = await workflow_service.get_rule(db=db, rule_id=rule_id)

    if not rule:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Workflow rule not found",
        )

    return WorkflowRuleResponse(**rule)


@router.patch(
    "/rules/{rule_id}",
    response_model=WorkflowRuleResponse,
    summary="Update workflow rule",
)
async def update_rule(
    rule_id: UUID,
    rule_update: WorkflowRuleUpdate,
    db: DbSession,
    admin_user: AdminUser,
) -> WorkflowRuleResponse:
    """
    Update a workflow rule.

    Admin access required.
    """
    # Get existing rule for audit
    existing = await workflow_service.get_rule(db=db, rule_id=rule_id)
    if not existing:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Workflow rule not found",
        )

    updates = rule_update.model_dump(exclude_unset=True)
    if not updates:
        return WorkflowRuleResponse(**existing)

    rule = await workflow_service.update_rule(
        db=db,
        rule_id=rule_id,
        updates=updates,
    )

    # Audit log
    await audit_service.log_update(
        db=db,
        entity_type="workflow_rule",
        entity_id=rule_id,
        user_id=admin_user["id"],
        old_values={"name": existing["name"]},
        new_values=updates,
    )

    return WorkflowRuleResponse(**rule)


@router.delete(
    "/rules/{rule_id}",
    response_model=MessageResponse,
    summary="Delete workflow rule",
)
async def delete_rule(
    rule_id: UUID,
    db: DbSession,
    admin_user: AdminUser,
) -> MessageResponse:
    """
    Delete a workflow rule.

    Admin access required.
    """
    # Get existing rule for audit
    existing = await workflow_service.get_rule(db=db, rule_id=rule_id)
    if not existing:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Workflow rule not found",
        )

    await workflow_service.delete_rule(db=db, rule_id=rule_id)

    # Audit log
    await audit_service.log_action(
        db=db,
        action="DELETE",
        entity_type="workflow_rule",
        entity_id=rule_id,
        user_id=admin_user["id"],
        old_values={"name": existing["name"]},
    )

    return MessageResponse(message=f"Workflow rule '{existing['name']}' deleted")


@router.post(
    "/rules/{rule_id}/toggle",
    response_model=WorkflowRuleResponse,
    summary="Toggle workflow rule enabled status",
)
async def toggle_rule(
    rule_id: UUID,
    toggle: WorkflowRuleToggle,
    db: DbSession,
    admin_user: AdminUser,
) -> WorkflowRuleResponse:
    """
    Enable or disable a workflow rule.

    Admin access required.
    """
    rule = await workflow_service.toggle_rule(
        db=db,
        rule_id=rule_id,
        enabled=toggle.enabled,
    )

    if not rule:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Workflow rule not found",
        )

    # Audit log
    action = "ENABLE" if toggle.enabled else "DISABLE"
    await audit_service.log_action(
        db=db,
        action=action,
        entity_type="workflow_rule",
        entity_id=rule_id,
        user_id=admin_user["id"],
        new_values={"is_enabled": toggle.enabled},
    )

    return WorkflowRuleResponse(**rule)


# =============================================================================
# WORKFLOW ACTIONS ENDPOINTS
# =============================================================================


@router.get(
    "/rules/{rule_id}/actions",
    response_model=list[WorkflowActionResponse],
    summary="Get actions for a rule",
)
async def get_rule_actions(
    rule_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> list[WorkflowActionResponse]:
    """
    Get all actions for a workflow rule.
    """
    # Verify rule exists
    rule = await workflow_service.get_rule(db=db, rule_id=rule_id)
    if not rule:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Workflow rule not found",
        )

    actions = await workflow_service.get_rule_actions(db=db, rule_id=rule_id)
    return [WorkflowActionResponse(**action) for action in actions]


@router.post(
    "/rules/{rule_id}/actions",
    response_model=WorkflowActionResponse,
    status_code=http_status.HTTP_201_CREATED,
    summary="Add action to rule",
)
async def add_action(
    rule_id: UUID,
    action_data: WorkflowActionCreate,
    db: DbSession,
    admin_user: AdminUser,
) -> WorkflowActionResponse:
    """
    Add an action to a workflow rule.

    Admin access required.
    """
    # Verify rule exists
    rule = await workflow_service.get_rule(db=db, rule_id=rule_id)
    if not rule:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Workflow rule not found",
        )

    action = await workflow_service.add_action(
        db=db,
        rule_id=rule_id,
        action_data=action_data.model_dump(),
    )

    # Audit log
    await audit_service.log_create(
        db=db,
        entity_type="workflow_action",
        entity_id=action["id"],
        user_id=admin_user["id"],
        new_values={"rule_id": str(rule_id), "action_type": action["action_type"]},
    )

    return WorkflowActionResponse(**action)


@router.patch(
    "/actions/{action_id}",
    response_model=WorkflowActionResponse,
    summary="Update workflow action",
)
async def update_action(
    action_id: UUID,
    action_update: WorkflowActionUpdate,
    db: DbSession,
    admin_user: AdminUser,
) -> WorkflowActionResponse:
    """
    Update a workflow action.

    Admin access required.
    """
    updates = action_update.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="No updates provided",
        )

    action = await workflow_service.update_action(
        db=db,
        action_id=action_id,
        updates=updates,
    )

    if not action:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Workflow action not found",
        )

    # Audit log
    await audit_service.log_update(
        db=db,
        entity_type="workflow_action",
        entity_id=action_id,
        user_id=admin_user["id"],
        old_values={},
        new_values=updates,
    )

    return WorkflowActionResponse(**action)


@router.delete(
    "/actions/{action_id}",
    response_model=MessageResponse,
    summary="Delete workflow action",
)
async def delete_action(
    action_id: UUID,
    db: DbSession,
    admin_user: AdminUser,
) -> MessageResponse:
    """
    Delete a workflow action.

    Admin access required.
    """
    deleted = await workflow_service.delete_action(db=db, action_id=action_id)

    if not deleted:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Workflow action not found",
        )

    # Audit log
    await audit_service.log_action(
        db=db,
        action="DELETE",
        entity_type="workflow_action",
        entity_id=action_id,
        user_id=admin_user["id"],
    )

    return MessageResponse(message="Workflow action deleted")


# =============================================================================
# WORKFLOW HISTORY ENDPOINTS
# =============================================================================


@router.get(
    "/rules/{rule_id}/history",
    response_model=WorkflowHistoryListResponse,
    summary="Get execution history for a rule",
)
async def get_rule_history(
    rule_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> WorkflowHistoryListResponse:
    """
    Get execution history for a specific workflow rule.
    """
    # Verify rule exists
    rule = await workflow_service.get_rule(db=db, rule_id=rule_id)
    if not rule:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Workflow rule not found",
        )

    skip = (page - 1) * page_size
    history, total = await workflow_service.get_rule_history(
        db=db,
        rule_id=rule_id,
        skip=skip,
        limit=page_size,
    )

    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return WorkflowHistoryListResponse(
        items=history,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/history",
    response_model=WorkflowHistoryListResponse,
    summary="Get all workflow execution history",
)
async def get_all_history(
    db: DbSession,
    current_user: CurrentUser,
    rule_id: UUID | None = Query(None, description="Filter by rule ID"),
    case_id: UUID | None = Query(None, description="Filter by case ID"),
    success: bool | None = Query(None, description="Filter by success status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> WorkflowHistoryListResponse:
    """
    Get all workflow execution history with optional filtering.
    """
    skip = (page - 1) * page_size
    filters = {}

    if rule_id:
        filters["rule_id"] = rule_id
    if case_id:
        filters["case_id"] = case_id
    if success is not None:
        filters["success"] = success

    history, total = await workflow_service.get_all_history(
        db=db,
        filters=filters,
        skip=skip,
        limit=page_size,
    )

    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return WorkflowHistoryListResponse(
        items=history,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# =============================================================================
# MANUAL TRIGGER ENDPOINT
# =============================================================================


@router.post(
    "/rules/{rule_id}/trigger/{case_id}",
    response_model=WorkflowHistoryResponse,
    summary="Manually trigger rule for a case",
)
async def trigger_rule(
    rule_id: UUID,
    case_id: str,
    db: DbSession,
    admin_user: AdminUser,
) -> WorkflowHistoryResponse:
    """
    Manually trigger a workflow rule for a specific case.

    Admin access required.
    """
    from app.services.case_service import case_service

    # Get rule
    rule = await workflow_service.get_rule(db=db, rule_id=rule_id)
    if not rule:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Workflow rule not found",
        )

    # Get case
    case_data = await case_service.get_case(db=db, case_id=case_id)
    if not case_data:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )

    # Execute rule
    trigger_data = {"manual": True, "triggered_by_user": str(admin_user["id"])}
    result = await workflow_executor.execute_rule(
        db=db,
        rule=rule,
        case_data=case_data,
        trigger_data=trigger_data,
        triggered_by=f"manual:{admin_user['username']}",
    )

    # Log execution
    history = await workflow_service.log_execution(
        db=db,
        rule=rule,
        case_data=case_data,
        trigger_type=str(rule["trigger_type"]),
        trigger_data=trigger_data,
        actions_executed=result["actions_executed"],
        success=result["success"],
        error_message=result.get("error_message"),
        triggered_by=f"manual:{admin_user['username']}",
    )

    logger.info(
        f"Manually triggered rule '{rule['name']}' for case {case_id} "
        f"by {admin_user['username']} - success: {result['success']}"
    )

    return WorkflowHistoryResponse(**history)
