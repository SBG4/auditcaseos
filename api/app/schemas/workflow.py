"""Workflow automation schemas for AuditCaseOS API."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import Field

from .common import BaseSchema, PaginatedResponse, TimestampMixin


# ============================================
# ENUMS
# ============================================

class TriggerType(str, Enum):
    """Type of workflow trigger."""
    STATUS_CHANGE = "STATUS_CHANGE"      # When case status transitions
    TIME_BASED = "TIME_BASED"            # After X days in a status
    EVENT = "EVENT"                      # When event occurs (evidence added, etc.)
    CONDITION = "CONDITION"              # When conditions match


class ActionType(str, Enum):
    """Type of workflow action."""
    CHANGE_STATUS = "CHANGE_STATUS"      # Update case status
    ASSIGN_USER = "ASSIGN_USER"          # Assign case to a user
    ADD_TAG = "ADD_TAG"                  # Add a tag to the case
    SEND_NOTIFICATION = "SEND_NOTIFICATION"  # Send in-app notification
    CREATE_TIMELINE = "CREATE_TIMELINE"  # Add timeline event


class NotificationPriority(str, Enum):
    """Notification priority level."""
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class EventType(str, Enum):
    """Types of events that can trigger workflows."""
    CASE_CREATED = "case_created"
    CASE_UPDATED = "case_updated"
    STATUS_CHANGED = "status_changed"
    EVIDENCE_ADDED = "evidence_added"
    EVIDENCE_DELETED = "evidence_deleted"
    FINDING_ADDED = "finding_added"
    FINDING_UPDATED = "finding_updated"
    TIMELINE_ADDED = "timeline_added"


class RecipientType(str, Enum):
    """Type of notification recipient."""
    OWNER = "owner"           # Case owner
    ASSIGNEE = "assignee"     # Assigned user
    ROLE = "role"             # All users with a role
    USER = "user"             # Specific user


# ============================================
# WORKFLOW ACTION SCHEMAS
# ============================================

class WorkflowActionBase(BaseSchema):
    """Base schema for workflow action."""

    action_type: ActionType = Field(
        ...,
        description="Type of action to execute",
    )
    action_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Action configuration (varies by action_type)",
    )
    sequence: int = Field(
        default=0,
        ge=0,
        description="Execution order within rule (lower = first)",
    )


class WorkflowActionCreate(WorkflowActionBase):
    """Schema for creating a workflow action."""
    pass


class WorkflowActionUpdate(BaseSchema):
    """Schema for updating a workflow action."""

    action_type: ActionType | None = Field(
        default=None,
        description="Type of action to execute",
    )
    action_config: dict[str, Any] | None = Field(
        default=None,
        description="Action configuration",
    )
    sequence: int | None = Field(
        default=None,
        ge=0,
        description="Execution order within rule",
    )


class WorkflowActionResponse(WorkflowActionBase):
    """Schema for workflow action response."""

    id: UUID = Field(..., description="Action unique identifier")
    rule_id: UUID = Field(..., description="Parent rule ID")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = {"from_attributes": True}


# ============================================
# WORKFLOW RULE SCHEMAS
# ============================================

class WorkflowRuleBase(BaseSchema):
    """Base schema for workflow rule."""

    name: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Rule name",
        examples=["Auto-escalate critical cases"],
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
        description="Rule description",
    )
    trigger_type: TriggerType = Field(
        ...,
        description="Type of trigger",
    )
    trigger_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Trigger configuration (varies by trigger_type)",
    )
    is_enabled: bool = Field(
        default=True,
        description="Whether the rule is active",
    )
    priority: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Rule priority (lower = higher priority)",
    )
    scope_codes: list[str] | None = Field(
        default=None,
        description="Limit to specific scopes (null = all)",
    )
    case_types: list[str] | None = Field(
        default=None,
        description="Limit to specific case types (null = all)",
    )


class WorkflowRuleCreate(WorkflowRuleBase):
    """Schema for creating a workflow rule."""

    actions: list[WorkflowActionCreate] | None = Field(
        default=None,
        description="Actions to add to the rule",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Auto-escalate stale critical cases",
                "description": "Notify manager when critical cases are open for more than 3 days",
                "trigger_type": "TIME_BASED",
                "trigger_config": {"status": "OPEN", "days": 3},
                "is_enabled": True,
                "priority": 50,
                "scope_codes": None,
                "case_types": None,
                "actions": [
                    {
                        "action_type": "SEND_NOTIFICATION",
                        "action_config": {
                            "title": "Critical case requires attention",
                            "message": "Case {case_id} has been open for {days} days",
                            "recipient_type": "role",
                            "recipient_value": "admin",
                            "priority": "HIGH",
                        },
                        "sequence": 0,
                    },
                    {
                        "action_type": "ADD_TAG",
                        "action_config": {"tag": "escalated"},
                        "sequence": 1,
                    },
                ],
            }
        }
    }


class WorkflowRuleUpdate(BaseSchema):
    """Schema for updating a workflow rule."""

    name: str | None = Field(
        default=None,
        min_length=3,
        max_length=255,
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
    )
    trigger_type: TriggerType | None = Field(default=None)
    trigger_config: dict[str, Any] | None = Field(default=None)
    is_enabled: bool | None = Field(default=None)
    priority: int | None = Field(default=None, ge=1, le=1000)
    scope_codes: list[str] | None = Field(default=None)
    case_types: list[str] | None = Field(default=None)


class WorkflowRuleResponse(WorkflowRuleBase, TimestampMixin):
    """Schema for workflow rule response."""

    id: UUID = Field(..., description="Rule unique identifier")
    created_by: UUID = Field(..., description="User who created the rule")
    actions: list[WorkflowActionResponse] = Field(
        default_factory=list,
        description="Actions attached to this rule",
    )

    model_config = {"from_attributes": True}


class WorkflowRuleListResponse(PaginatedResponse):
    """Paginated list of workflow rules."""

    items: list[WorkflowRuleResponse] = Field(
        ...,
        description="List of workflow rules",
    )


class WorkflowRuleToggle(BaseSchema):
    """Schema for toggling rule enabled status."""

    enabled: bool = Field(..., description="Whether to enable or disable the rule")


# ============================================
# NOTIFICATION SCHEMAS
# ============================================

class NotificationBase(BaseSchema):
    """Base schema for notification."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Notification title",
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Notification message",
    )
    priority: NotificationPriority = Field(
        default=NotificationPriority.NORMAL,
        description="Notification priority",
    )


class NotificationCreate(NotificationBase):
    """Schema for creating a notification."""

    user_id: UUID = Field(..., description="Recipient user ID")
    entity_type: str | None = Field(
        default=None,
        max_length=50,
        description="Related entity type (case, evidence, etc.)",
    )
    entity_id: UUID | None = Field(
        default=None,
        description="Related entity ID",
    )
    link_url: str | None = Field(
        default=None,
        max_length=500,
        description="URL to navigate when clicked",
    )
    source: str = Field(
        default="system",
        max_length=100,
        description="Notification source",
    )
    source_rule_id: UUID | None = Field(
        default=None,
        description="Workflow rule that generated this",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Additional metadata",
    )


class NotificationResponse(NotificationBase):
    """Schema for notification response."""

    id: UUID = Field(..., description="Notification ID")
    user_id: UUID = Field(..., description="Recipient user ID")
    entity_type: str | None = Field(default=None)
    entity_id: UUID | None = Field(default=None)
    link_url: str | None = Field(default=None)
    is_read: bool = Field(default=False)
    read_at: datetime | None = Field(default=None)
    source: str = Field(default="system")
    source_rule_id: UUID | None = Field(default=None)
    metadata: dict[str, Any] | None = Field(default=None)
    created_at: datetime = Field(...)

    model_config = {"from_attributes": True}


class NotificationListResponse(PaginatedResponse):
    """Paginated list of notifications."""

    items: list[NotificationResponse] = Field(
        ...,
        description="List of notifications",
    )


class NotificationCountResponse(BaseSchema):
    """Unread notification count response."""

    count: int = Field(..., ge=0, description="Number of unread notifications")


class NotificationMarkReadResponse(BaseSchema):
    """Response for mark all as read."""

    marked_count: int = Field(..., ge=0, description="Number of notifications marked as read")


# ============================================
# WORKFLOW HISTORY SCHEMAS
# ============================================

class ActionExecutionResult(BaseSchema):
    """Result of executing a single action."""

    action_type: ActionType
    success: bool
    details: dict[str, Any] | None = None
    error: str | None = None


class WorkflowHistoryResponse(BaseSchema):
    """Schema for workflow execution history."""

    id: UUID = Field(..., description="History entry ID")
    rule_id: UUID | None = Field(default=None, description="Rule that was executed")
    rule_name: str = Field(..., description="Name of the rule (preserved)")
    trigger_type: TriggerType = Field(..., description="Type of trigger")
    trigger_data: dict[str, Any] | None = Field(default=None)
    case_id: UUID | None = Field(default=None, description="Target case UUID")
    case_id_str: str | None = Field(default=None, description="Target case ID string")
    actions_executed: list[ActionExecutionResult] = Field(
        default_factory=list,
        description="Results of each action executed",
    )
    success: bool = Field(..., description="Whether all actions succeeded")
    error_message: str | None = Field(default=None)
    started_at: datetime = Field(...)
    completed_at: datetime | None = Field(default=None)
    triggered_by: str | None = Field(default=None, description="What triggered the rule")

    model_config = {"from_attributes": True}


class WorkflowHistoryListResponse(PaginatedResponse):
    """Paginated list of workflow history entries."""

    items: list[WorkflowHistoryResponse] = Field(
        ...,
        description="List of history entries",
    )


# ============================================
# TRIGGER CONFIG SCHEMAS (for validation)
# ============================================

class StatusChangeTriggerConfig(BaseSchema):
    """Configuration for STATUS_CHANGE trigger."""

    from_status: str | None = Field(
        default=None,
        description="Previous status (null = any)",
    )
    to_status: str = Field(
        ...,
        description="New status that triggers the rule",
    )


class TimeBasedTriggerConfig(BaseSchema):
    """Configuration for TIME_BASED trigger."""

    status: str = Field(
        ...,
        description="Status to check duration for",
    )
    days: int = Field(
        ...,
        gt=0,
        description="Number of days threshold",
    )


class EventTriggerConfig(BaseSchema):
    """Configuration for EVENT trigger."""

    event_type: EventType = Field(
        ...,
        description="Type of event to trigger on",
    )


class ConditionOperator(str, Enum):
    """Operators for condition matching."""
    EQ = "eq"           # Equal
    NEQ = "neq"         # Not equal
    GT = "gt"           # Greater than
    GTE = "gte"         # Greater than or equal
    LT = "lt"           # Less than
    LTE = "lte"         # Less than or equal
    IN = "in"           # In list
    NOT_IN = "not_in"   # Not in list
    CONTAINS = "contains"  # String contains


class ConditionItem(BaseSchema):
    """Single condition for CONDITION trigger."""

    field: str = Field(..., description="Field to check (status, severity, scope_code, etc.)")
    operator: ConditionOperator = Field(..., description="Comparison operator")
    value: Any = Field(..., description="Value to compare against")


class ConditionTriggerConfig(BaseSchema):
    """Configuration for CONDITION trigger."""

    conditions: list[ConditionItem] = Field(
        ...,
        min_length=1,
        description="List of conditions (all must match)",
    )


# ============================================
# ACTION CONFIG SCHEMAS (for documentation)
# ============================================

class ChangeStatusActionConfig(BaseSchema):
    """Configuration for CHANGE_STATUS action."""

    new_status: str = Field(..., description="Status to change to")


class AssignUserActionConfig(BaseSchema):
    """Configuration for ASSIGN_USER action."""

    user_id: UUID | None = Field(default=None, description="User ID to assign to")
    assign_to_owner: bool = Field(default=False, description="Assign to case owner")


class AddTagActionConfig(BaseSchema):
    """Configuration for ADD_TAG action."""

    tag: str = Field(..., min_length=1, max_length=50, description="Tag to add")


class SendNotificationActionConfig(BaseSchema):
    """Configuration for SEND_NOTIFICATION action."""

    title: str = Field(..., description="Notification title (supports templates)")
    message: str = Field(..., description="Notification message (supports templates)")
    recipient_type: RecipientType = Field(..., description="How to determine recipients")
    recipient_value: str | None = Field(
        default=None,
        description="Role name or user ID (depending on recipient_type)",
    )
    priority: NotificationPriority = Field(
        default=NotificationPriority.NORMAL,
        description="Notification priority",
    )


class CreateTimelineActionConfig(BaseSchema):
    """Configuration for CREATE_TIMELINE action."""

    event_type: str = Field(
        default="workflow",
        description="Timeline event type",
    )
    description_template: str = Field(
        ...,
        description="Description template (supports variables like {case_id}, {days})",
    )
