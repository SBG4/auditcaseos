"""Workflow executor service for executing workflow actions."""

import logging
import re
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .notification_service import notification_service

logger = logging.getLogger(__name__)


class WorkflowExecutor:
    """Executes workflow actions on cases."""

    async def execute_rule(
        self,
        db: AsyncSession,
        rule: dict[str, Any],
        case_data: dict[str, Any],
        trigger_data: dict[str, Any],
        triggered_by: str,
    ) -> dict[str, Any]:
        """
        Execute all actions for a rule.

        Args:
            db: Database session
            rule: Rule to execute
            case_data: Target case data
            trigger_data: Trigger-specific data
            triggered_by: What triggered the rule

        Returns:
            Execution result dict
        """
        actions = rule.get("actions", [])
        actions_executed = []
        all_success = True
        error_message = None

        context = {
            "rule": rule,
            "trigger_data": trigger_data,
            "triggered_by": triggered_by,
            "case_data": case_data,
        }

        for action in sorted(actions, key=lambda a: a.get("sequence", 0)):
            try:
                result = await self.execute_action(db, action, case_data, context)
                actions_executed.append(result)

                if not result.get("success"):
                    all_success = False
                    if result.get("error"):
                        error_message = result["error"]

            except Exception as e:
                logger.error(f"Failed to execute action {action.get('id')}: {e}")
                actions_executed.append({
                    "action_type": action.get("action_type"),
                    "success": False,
                    "error": str(e),
                })
                all_success = False
                error_message = str(e)

        return {
            "success": all_success,
            "actions_executed": actions_executed,
            "error_message": error_message,
        }

    async def execute_action(
        self,
        db: AsyncSession,
        action: dict[str, Any],
        case_data: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute a single action.

        Args:
            db: Database session
            action: Action to execute
            case_data: Target case data
            context: Execution context

        Returns:
            Action result dict
        """
        action_type = action.get("action_type")
        action_config = action.get("action_config", {})

        handlers = {
            "CHANGE_STATUS": self._execute_change_status,
            "ASSIGN_USER": self._execute_assign_user,
            "ADD_TAG": self._execute_add_tag,
            "SEND_NOTIFICATION": self._execute_send_notification,
            "CREATE_TIMELINE": self._execute_create_timeline,
        }

        handler = handlers.get(action_type)
        if not handler:
            return {
                "action_type": action_type,
                "success": False,
                "error": f"Unknown action type: {action_type}",
            }

        return await handler(db, action_config, case_data, context)

    async def _execute_change_status(
        self,
        db: AsyncSession,
        action_config: dict[str, Any],
        case_data: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute CHANGE_STATUS action.

        Args:
            db: Database session
            action_config: Config with new_status
            case_data: Target case
            context: Execution context

        Returns:
            Action result
        """
        try:
            new_status = action_config.get("new_status")
            if not new_status:
                return {
                    "action_type": "CHANGE_STATUS",
                    "success": False,
                    "error": "new_status not specified",
                }

            case_id = case_data.get("id")
            old_status = case_data.get("status")

            query = text("""
                UPDATE cases
                SET status = CAST(:new_status AS case_status), updated_at = CURRENT_TIMESTAMP
                WHERE id = :case_id
                RETURNING id, status
            """)

            result = await db.execute(query, {
                "case_id": str(case_id),
                "new_status": new_status,
            })
            await db.commit()
            row = result.fetchone()

            if row:
                logger.info(
                    f"Workflow changed case {case_data.get('case_id')} status: "
                    f"{old_status} -> {new_status}"
                )
                return {
                    "action_type": "CHANGE_STATUS",
                    "success": True,
                    "details": {
                        "old_status": old_status,
                        "new_status": new_status,
                    },
                }

            return {
                "action_type": "CHANGE_STATUS",
                "success": False,
                "error": "Case not found",
            }

        except Exception as e:
            await db.rollback()
            return {
                "action_type": "CHANGE_STATUS",
                "success": False,
                "error": str(e),
            }

    async def _execute_assign_user(
        self,
        db: AsyncSession,
        action_config: dict[str, Any],
        case_data: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute ASSIGN_USER action.

        Args:
            db: Database session
            action_config: Config with user_id or assign_to_owner
            case_data: Target case
            context: Execution context

        Returns:
            Action result
        """
        try:
            case_id = case_data.get("id")
            assign_to_owner = action_config.get("assign_to_owner", False)
            user_id = action_config.get("user_id")

            if assign_to_owner:
                user_id = case_data.get("owner_id")

            if not user_id:
                return {
                    "action_type": "ASSIGN_USER",
                    "success": False,
                    "error": "user_id not specified and assign_to_owner is false",
                }

            query = text("""
                UPDATE cases
                SET assigned_to = :user_id, updated_at = CURRENT_TIMESTAMP
                WHERE id = :case_id
                RETURNING id, assigned_to
            """)

            result = await db.execute(query, {
                "case_id": str(case_id),
                "user_id": str(user_id),
            })
            await db.commit()
            row = result.fetchone()

            if row:
                logger.info(
                    f"Workflow assigned case {case_data.get('case_id')} to user {user_id}"
                )
                return {
                    "action_type": "ASSIGN_USER",
                    "success": True,
                    "details": {"assigned_to": str(user_id)},
                }

            return {
                "action_type": "ASSIGN_USER",
                "success": False,
                "error": "Case not found",
            }

        except Exception as e:
            await db.rollback()
            return {
                "action_type": "ASSIGN_USER",
                "success": False,
                "error": str(e),
            }

    async def _execute_add_tag(
        self,
        db: AsyncSession,
        action_config: dict[str, Any],
        case_data: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute ADD_TAG action.

        Args:
            db: Database session
            action_config: Config with tag
            case_data: Target case
            context: Execution context

        Returns:
            Action result
        """
        try:
            tag = action_config.get("tag")
            if not tag:
                return {
                    "action_type": "ADD_TAG",
                    "success": False,
                    "error": "tag not specified",
                }

            case_id = case_data.get("id")

            # Add tag if not already present
            query = text("""
                UPDATE cases
                SET tags = CASE
                    WHEN tags IS NULL THEN ARRAY[:tag]
                    WHEN :tag = ANY(tags) THEN tags
                    ELSE array_append(tags, :tag)
                END,
                updated_at = CURRENT_TIMESTAMP
                WHERE id = :case_id
                RETURNING id, tags
            """)

            result = await db.execute(query, {
                "case_id": str(case_id),
                "tag": tag,
            })
            await db.commit()
            row = result.fetchone()

            if row:
                logger.info(
                    f"Workflow added tag '{tag}' to case {case_data.get('case_id')}"
                )
                return {
                    "action_type": "ADD_TAG",
                    "success": True,
                    "details": {"tag": tag},
                }

            return {
                "action_type": "ADD_TAG",
                "success": False,
                "error": "Case not found",
            }

        except Exception as e:
            await db.rollback()
            return {
                "action_type": "ADD_TAG",
                "success": False,
                "error": str(e),
            }

    async def _execute_send_notification(
        self,
        db: AsyncSession,
        action_config: dict[str, Any],
        case_data: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute SEND_NOTIFICATION action.

        Args:
            db: Database session
            action_config: Config with title, message, recipient_type, recipient_value
            case_data: Target case
            context: Execution context

        Returns:
            Action result
        """
        try:
            title_template = action_config.get("title", "Workflow Notification")
            message_template = action_config.get("message", "")
            recipient_type = action_config.get("recipient_type", "owner")
            recipient_value = action_config.get("recipient_value")
            priority = action_config.get("priority", "NORMAL")

            # Render templates
            template_context = {
                "case_id": case_data.get("case_id", ""),
                "case_title": case_data.get("title", ""),
                "status": case_data.get("status", ""),
                "severity": case_data.get("severity", ""),
                "scope_code": case_data.get("scope_code", ""),
                **context.get("trigger_data", {}),
            }

            title = self._render_template(title_template, template_context)
            message = self._render_template(message_template, template_context)

            # Determine recipients
            recipient_ids = await self._get_recipients(
                db, recipient_type, recipient_value, case_data
            )

            if not recipient_ids:
                return {
                    "action_type": "SEND_NOTIFICATION",
                    "success": False,
                    "error": f"No recipients found for type: {recipient_type}",
                }

            # Create notifications
            rule = context.get("rule", {})
            notifications_created = []

            for user_id in recipient_ids:
                notification = await notification_service.create_notification(
                    db=db,
                    user_id=user_id,
                    title=title,
                    message=message,
                    priority=priority,
                    entity_type="case",
                    entity_id=case_data.get("id"),
                    link_url=f"/cases/{case_data.get('case_id')}",
                    source="workflow",
                    source_rule_id=rule.get("id"),
                )
                notifications_created.append(str(notification.get("id")))

            logger.info(
                f"Workflow sent {len(notifications_created)} notifications for "
                f"case {case_data.get('case_id')}"
            )

            return {
                "action_type": "SEND_NOTIFICATION",
                "success": True,
                "details": {
                    "recipients": len(notifications_created),
                    "notification_ids": notifications_created,
                },
            }

        except Exception as e:
            return {
                "action_type": "SEND_NOTIFICATION",
                "success": False,
                "error": str(e),
            }

    async def _execute_create_timeline(
        self,
        db: AsyncSession,
        action_config: dict[str, Any],
        case_data: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute CREATE_TIMELINE action.

        Args:
            db: Database session
            action_config: Config with event_type, description_template
            case_data: Target case
            context: Execution context

        Returns:
            Action result
        """
        try:
            event_type = action_config.get("event_type", "workflow")
            description_template = action_config.get(
                "description_template", "Workflow action executed"
            )

            # Render template
            template_context = {
                "case_id": case_data.get("case_id", ""),
                "case_title": case_data.get("title", ""),
                "status": case_data.get("status", ""),
                "severity": case_data.get("severity", ""),
                "rule_name": context.get("rule", {}).get("name", "Unknown"),
                **context.get("trigger_data", {}),
            }

            description = self._render_template(description_template, template_context)

            # Get a system user ID for created_by (use owner if no system user)
            created_by = case_data.get("owner_id")

            query = text("""
                INSERT INTO timeline_events (
                    case_id, event_time, event_type, description, source, created_by
                ) VALUES (
                    :case_id, :event_time, :event_type, :description, :source, :created_by
                )
                RETURNING id
            """)

            result = await db.execute(query, {
                "case_id": str(case_data.get("id")),
                "event_time": datetime.utcnow(),
                "event_type": event_type,
                "description": description,
                "source": "workflow",
                "created_by": str(created_by),
            })
            await db.commit()
            row = result.fetchone()

            if row:
                logger.info(
                    f"Workflow created timeline event for case {case_data.get('case_id')}"
                )
                return {
                    "action_type": "CREATE_TIMELINE",
                    "success": True,
                    "details": {
                        "event_id": str(row.id),
                        "event_type": event_type,
                    },
                }

            return {
                "action_type": "CREATE_TIMELINE",
                "success": False,
                "error": "Failed to create timeline event",
            }

        except Exception as e:
            await db.rollback()
            return {
                "action_type": "CREATE_TIMELINE",
                "success": False,
                "error": str(e),
            }

    def _render_template(
        self,
        template: str,
        context: dict[str, Any],
    ) -> str:
        """
        Render a template string with context variables.

        Supports {variable_name} syntax.

        Args:
            template: Template string
            context: Variables to substitute

        Returns:
            Rendered string
        """
        result = template
        for key, value in context.items():
            result = result.replace(f"{{{key}}}", str(value) if value else "")
        return result

    async def _get_recipients(
        self,
        db: AsyncSession,
        recipient_type: str,
        recipient_value: str | None,
        case_data: dict[str, Any],
    ) -> list[str]:
        """
        Get recipient user IDs based on recipient type.

        Args:
            db: Database session
            recipient_type: Type of recipient (owner, assignee, role, user)
            recipient_value: Value for role or user type
            case_data: Case data

        Returns:
            List of user UUIDs as strings
        """
        if recipient_type == "owner":
            owner_id = case_data.get("owner_id")
            return [str(owner_id)] if owner_id else []

        elif recipient_type == "assignee":
            assignee_id = case_data.get("assigned_to")
            return [str(assignee_id)] if assignee_id else []

        elif recipient_type == "role":
            if not recipient_value:
                return []

            query = text("""
                SELECT id FROM users
                WHERE role = CAST(:role AS user_role) AND is_active = true
            """)
            result = await db.execute(query, {"role": recipient_value})
            return [str(row.id) for row in result.fetchall()]

        elif recipient_type == "user":
            if not recipient_value:
                return []
            return [recipient_value]

        return []


# Singleton instance
workflow_executor = WorkflowExecutor()
