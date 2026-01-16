"""Workflow automation service for managing rules and triggering actions."""

import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class WorkflowService:
    """Service for managing workflow rules and executing actions."""

    # ============================================
    # RULE CRUD OPERATIONS
    # ============================================

    async def create_rule(
        self,
        db: AsyncSession,
        rule_data: dict[str, Any],
        created_by: UUID | str,
    ) -> dict[str, Any]:
        """
        Create a new workflow rule.

        Args:
            db: Database session
            rule_data: Rule data with name, trigger_type, trigger_config, etc.
            created_by: User ID who created the rule

        Returns:
            Created rule dict
        """
        try:
            query = text("""
                INSERT INTO workflow_rules (
                    name, description, trigger_type, trigger_config,
                    is_enabled, priority, scope_codes, case_types, created_by
                ) VALUES (
                    :name, :description, CAST(:trigger_type AS workflow_trigger_type),
                    CAST(:trigger_config AS jsonb), :is_enabled, :priority,
                    :scope_codes, :case_types, :created_by
                )
                RETURNING *
            """)

            params = {
                "name": rule_data["name"],
                "description": rule_data.get("description"),
                "trigger_type": rule_data["trigger_type"],
                "trigger_config": json.dumps(rule_data.get("trigger_config", {})),
                "is_enabled": rule_data.get("is_enabled", True),
                "priority": rule_data.get("priority", 100),
                "scope_codes": rule_data.get("scope_codes"),
                "case_types": rule_data.get("case_types"),
                "created_by": str(created_by),
            }

            result = await db.execute(query, params)
            await db.commit()
            row = result.fetchone()

            if row:
                rule = dict(row._mapping)
                rule["actions"] = []

                # Create actions if provided
                actions = rule_data.get("actions", [])
                for action_data in actions:
                    action = await self.add_action(db, rule["id"], action_data)
                    rule["actions"].append(action)

                logger.info(f"Created workflow rule: {rule['name']} (ID: {rule['id']})")
                return rule

            raise Exception("Failed to create workflow rule")

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to create workflow rule: {e}")
            raise

    async def get_rule(
        self,
        db: AsyncSession,
        rule_id: UUID | str,
    ) -> dict[str, Any] | None:
        """
        Get a workflow rule by ID with its actions.

        Args:
            db: Database session
            rule_id: Rule UUID

        Returns:
            Rule dict with actions or None
        """
        try:
            query = text("""
                SELECT * FROM workflow_rules WHERE id = :rule_id
            """)

            result = await db.execute(query, {"rule_id": str(rule_id)})
            row = result.fetchone()

            if row:
                rule = dict(row._mapping)
                rule["actions"] = await self.get_rule_actions(db, rule_id)
                return rule

            return None

        except Exception as e:
            logger.error(f"Failed to get workflow rule {rule_id}: {e}")
            raise

    async def list_rules(
        self,
        db: AsyncSession,
        filters: dict[str, Any] | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        List workflow rules with optional filtering.

        Args:
            db: Database session
            filters: Optional filters (is_enabled, trigger_type)
            skip: Pagination offset
            limit: Maximum rules to return

        Returns:
            Tuple of (list of rules, total count)
        """
        try:
            filters = filters or {}
            where_clauses = []
            params: dict[str, Any] = {"skip": skip, "limit": limit}

            if "is_enabled" in filters:
                where_clauses.append("is_enabled = :is_enabled")
                params["is_enabled"] = filters["is_enabled"]

            if "trigger_type" in filters:
                where_clauses.append("trigger_type = CAST(:trigger_type AS workflow_trigger_type)")
                params["trigger_type"] = filters["trigger_type"]

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            # Count query
            count_query = text(f"""
                SELECT COUNT(*) as count FROM workflow_rules WHERE {where_sql}
            """)
            count_result = await db.execute(count_query, params)
            total = count_result.scalar() or 0

            # Main query
            query = text(f"""
                SELECT * FROM workflow_rules
                WHERE {where_sql}
                ORDER BY priority ASC, created_at DESC
                OFFSET :skip LIMIT :limit
            """)

            result = await db.execute(query, params)
            rules = []

            for row in result.fetchall():
                rule = dict(row._mapping)
                rule["actions"] = await self.get_rule_actions(db, rule["id"])
                rules.append(rule)

            return rules, total

        except Exception as e:
            logger.error(f"Failed to list workflow rules: {e}")
            raise

    async def update_rule(
        self,
        db: AsyncSession,
        rule_id: UUID | str,
        updates: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Update a workflow rule.

        Args:
            db: Database session
            rule_id: Rule UUID
            updates: Fields to update

        Returns:
            Updated rule or None if not found
        """
        try:
            # Build dynamic UPDATE statement
            set_clauses = []
            params: dict[str, Any] = {"rule_id": str(rule_id)}

            if "name" in updates:
                set_clauses.append("name = :name")
                params["name"] = updates["name"]

            if "description" in updates:
                set_clauses.append("description = :description")
                params["description"] = updates["description"]

            if "trigger_type" in updates:
                set_clauses.append("trigger_type = CAST(:trigger_type AS workflow_trigger_type)")
                params["trigger_type"] = updates["trigger_type"]

            if "trigger_config" in updates:
                set_clauses.append("trigger_config = CAST(:trigger_config AS jsonb)")
                params["trigger_config"] = json.dumps(updates["trigger_config"])

            if "is_enabled" in updates:
                set_clauses.append("is_enabled = :is_enabled")
                params["is_enabled"] = updates["is_enabled"]

            if "priority" in updates:
                set_clauses.append("priority = :priority")
                params["priority"] = updates["priority"]

            if "scope_codes" in updates:
                set_clauses.append("scope_codes = :scope_codes")
                params["scope_codes"] = updates["scope_codes"]

            if "case_types" in updates:
                set_clauses.append("case_types = :case_types")
                params["case_types"] = updates["case_types"]

            if not set_clauses:
                return await self.get_rule(db, rule_id)

            set_sql = ", ".join(set_clauses)
            query = text(f"""
                UPDATE workflow_rules
                SET {set_sql}, updated_at = CURRENT_TIMESTAMP
                WHERE id = :rule_id
                RETURNING *
            """)

            result = await db.execute(query, params)
            await db.commit()
            row = result.fetchone()

            if row:
                rule = dict(row._mapping)
                rule["actions"] = await self.get_rule_actions(db, rule_id)
                return rule

            return None

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to update workflow rule {rule_id}: {e}")
            raise

    async def delete_rule(
        self,
        db: AsyncSession,
        rule_id: UUID | str,
    ) -> bool:
        """
        Delete a workflow rule.

        Args:
            db: Database session
            rule_id: Rule UUID

        Returns:
            True if deleted, False if not found
        """
        try:
            query = text("""
                DELETE FROM workflow_rules WHERE id = :rule_id RETURNING id
            """)

            result = await db.execute(query, {"rule_id": str(rule_id)})
            await db.commit()

            return result.fetchone() is not None

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to delete workflow rule {rule_id}: {e}")
            raise

    async def toggle_rule(
        self,
        db: AsyncSession,
        rule_id: UUID | str,
        enabled: bool,
    ) -> dict[str, Any] | None:
        """
        Enable or disable a workflow rule.

        Args:
            db: Database session
            rule_id: Rule UUID
            enabled: Whether to enable or disable

        Returns:
            Updated rule or None if not found
        """
        return await self.update_rule(db, rule_id, {"is_enabled": enabled})

    # ============================================
    # ACTION CRUD OPERATIONS
    # ============================================

    async def add_action(
        self,
        db: AsyncSession,
        rule_id: UUID | str,
        action_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Add an action to a workflow rule.

        Args:
            db: Database session
            rule_id: Rule UUID
            action_data: Action data with action_type, action_config, sequence

        Returns:
            Created action dict
        """
        try:
            query = text("""
                INSERT INTO workflow_actions (
                    rule_id, action_type, action_config, sequence
                ) VALUES (
                    :rule_id, CAST(:action_type AS workflow_action_type),
                    CAST(:action_config AS jsonb), :sequence
                )
                RETURNING *
            """)

            params = {
                "rule_id": str(rule_id),
                "action_type": action_data["action_type"],
                "action_config": json.dumps(action_data.get("action_config", {})),
                "sequence": action_data.get("sequence", 0),
            }

            result = await db.execute(query, params)
            await db.commit()
            row = result.fetchone()

            if row:
                return dict(row._mapping)

            raise Exception("Failed to create workflow action")

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to add action to rule {rule_id}: {e}")
            raise

    async def get_rule_actions(
        self,
        db: AsyncSession,
        rule_id: UUID | str,
    ) -> list[dict[str, Any]]:
        """
        Get all actions for a rule.

        Args:
            db: Database session
            rule_id: Rule UUID

        Returns:
            List of action dicts
        """
        try:
            query = text("""
                SELECT * FROM workflow_actions
                WHERE rule_id = :rule_id
                ORDER BY sequence ASC
            """)

            result = await db.execute(query, {"rule_id": str(rule_id)})
            return [dict(row._mapping) for row in result.fetchall()]

        except Exception as e:
            logger.error(f"Failed to get actions for rule {rule_id}: {e}")
            raise

    async def update_action(
        self,
        db: AsyncSession,
        action_id: UUID | str,
        updates: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Update a workflow action.

        Args:
            db: Database session
            action_id: Action UUID
            updates: Fields to update

        Returns:
            Updated action or None if not found
        """
        try:
            set_clauses = []
            params: dict[str, Any] = {"action_id": str(action_id)}

            if "action_type" in updates:
                set_clauses.append("action_type = CAST(:action_type AS workflow_action_type)")
                params["action_type"] = updates["action_type"]

            if "action_config" in updates:
                set_clauses.append("action_config = CAST(:action_config AS jsonb)")
                params["action_config"] = json.dumps(updates["action_config"])

            if "sequence" in updates:
                set_clauses.append("sequence = :sequence")
                params["sequence"] = updates["sequence"]

            if not set_clauses:
                return None

            set_sql = ", ".join(set_clauses)
            query = text(f"""
                UPDATE workflow_actions
                SET {set_sql}
                WHERE id = :action_id
                RETURNING *
            """)

            result = await db.execute(query, params)
            await db.commit()
            row = result.fetchone()

            return dict(row._mapping) if row else None

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to update action {action_id}: {e}")
            raise

    async def delete_action(
        self,
        db: AsyncSession,
        action_id: UUID | str,
    ) -> bool:
        """
        Delete a workflow action.

        Args:
            db: Database session
            action_id: Action UUID

        Returns:
            True if deleted, False if not found
        """
        try:
            query = text("""
                DELETE FROM workflow_actions WHERE id = :action_id RETURNING id
            """)

            result = await db.execute(query, {"action_id": str(action_id)})
            await db.commit()

            return result.fetchone() is not None

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to delete action {action_id}: {e}")
            raise

    # ============================================
    # RULE MATCHING
    # ============================================

    async def get_matching_rules(
        self,
        db: AsyncSession,
        trigger_type: str,
        trigger_data: dict[str, Any],
        case_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Find rules that match the given trigger and case.

        Args:
            db: Database session
            trigger_type: Type of trigger (STATUS_CHANGE, EVENT, etc.)
            trigger_data: Trigger-specific data
            case_data: Case data to match against

        Returns:
            List of matching rules
        """
        try:
            # Get all enabled rules of the trigger type
            rules, _ = await self.list_rules(
                db,
                filters={"is_enabled": True, "trigger_type": trigger_type},
                skip=0,
                limit=1000,
            )

            matching = []
            for rule in rules:
                if self._rule_matches(rule, trigger_data, case_data):
                    matching.append(rule)

            return matching

        except Exception as e:
            logger.error(f"Failed to get matching rules: {e}")
            raise

    def _rule_matches(
        self,
        rule: dict[str, Any],
        trigger_data: dict[str, Any],
        case_data: dict[str, Any],
    ) -> bool:
        """
        Check if a rule matches the trigger and case data.

        Args:
            rule: Rule to check
            trigger_data: Trigger-specific data
            case_data: Case data

        Returns:
            True if rule matches
        """
        # Check scope filter
        scope_codes = rule.get("scope_codes")
        if scope_codes and case_data.get("scope_code") not in scope_codes:
            return False

        # Check case type filter
        case_types = rule.get("case_types")
        if case_types and case_data.get("case_type") not in case_types:
            return False

        # Check trigger-specific conditions
        trigger_type = rule.get("trigger_type")
        trigger_config = rule.get("trigger_config", {})

        if trigger_type == "STATUS_CHANGE":
            from_status = trigger_config.get("from_status")
            to_status = trigger_config.get("to_status")

            if from_status and trigger_data.get("from_status") != from_status:
                return False
            if to_status and trigger_data.get("to_status") != to_status:
                return False

        elif trigger_type == "EVENT":
            event_type = trigger_config.get("event_type")
            if event_type and trigger_data.get("event_type") != event_type:
                return False

        elif trigger_type == "CONDITION":
            conditions = trigger_config.get("conditions", [])
            for condition in conditions:
                if not self._check_condition(condition, case_data):
                    return False

        # TIME_BASED rules are handled by scheduler, not event matching

        return True

    def _check_condition(
        self,
        condition: dict[str, Any],
        case_data: dict[str, Any],
    ) -> bool:
        """
        Check if a single condition matches.

        Args:
            condition: Condition with field, operator, value
            case_data: Case data to check

        Returns:
            True if condition matches
        """
        field = condition.get("field")
        operator = condition.get("operator")
        value = condition.get("value")

        case_value = case_data.get(field)

        if operator == "eq":
            return case_value == value
        elif operator == "neq":
            return case_value != value
        elif operator == "gt":
            return case_value > value
        elif operator == "gte":
            return case_value >= value
        elif operator == "lt":
            return case_value < value
        elif operator == "lte":
            return case_value <= value
        elif operator == "in":
            return case_value in value
        elif operator == "not_in":
            return case_value not in value
        elif operator == "contains":
            return value in str(case_value) if case_value else False

        return False

    # ============================================
    # WORKFLOW HISTORY
    # ============================================

    async def log_execution(
        self,
        db: AsyncSession,
        rule: dict[str, Any],
        case_data: dict[str, Any],
        trigger_type: str,
        trigger_data: dict[str, Any],
        actions_executed: list[dict[str, Any]],
        success: bool,
        error_message: str | None,
        triggered_by: str,
    ) -> dict[str, Any]:
        """
        Log a workflow execution to history.

        Args:
            db: Database session
            rule: Rule that was executed
            case_data: Case that triggered the rule
            trigger_type: Type of trigger
            trigger_data: Trigger data
            actions_executed: Results of executed actions
            success: Whether execution succeeded
            error_message: Error message if failed
            triggered_by: What triggered the rule

        Returns:
            Created history entry
        """
        try:
            query = text("""
                INSERT INTO workflow_history (
                    rule_id, rule_name, trigger_type, trigger_data,
                    case_id, case_id_str, actions_executed,
                    success, error_message, completed_at, triggered_by
                ) VALUES (
                    :rule_id, :rule_name, CAST(:trigger_type AS workflow_trigger_type),
                    CAST(:trigger_data AS jsonb), :case_id, :case_id_str,
                    CAST(:actions_executed AS jsonb), :success, :error_message,
                    :completed_at, :triggered_by
                )
                RETURNING *
            """)

            params = {
                "rule_id": str(rule["id"]),
                "rule_name": rule["name"],
                "trigger_type": trigger_type,
                "trigger_data": json.dumps(trigger_data),
                "case_id": str(case_data.get("id")) if case_data.get("id") else None,
                "case_id_str": case_data.get("case_id"),
                "actions_executed": json.dumps(actions_executed),
                "success": success,
                "error_message": error_message,
                "completed_at": datetime.utcnow(),
                "triggered_by": triggered_by,
            }

            result = await db.execute(query, params)
            await db.commit()
            row = result.fetchone()

            return dict(row._mapping) if row else {}

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to log workflow execution: {e}")
            raise

    async def get_rule_history(
        self,
        db: AsyncSession,
        rule_id: UUID | str,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Get execution history for a rule.

        Args:
            db: Database session
            rule_id: Rule UUID
            skip: Pagination offset
            limit: Maximum entries to return

        Returns:
            Tuple of (list of history entries, total count)
        """
        try:
            # Count query
            count_query = text("""
                SELECT COUNT(*) as count FROM workflow_history WHERE rule_id = :rule_id
            """)
            count_result = await db.execute(count_query, {"rule_id": str(rule_id)})
            total = count_result.scalar() or 0

            # Main query
            query = text("""
                SELECT * FROM workflow_history
                WHERE rule_id = :rule_id
                ORDER BY started_at DESC
                OFFSET :skip LIMIT :limit
            """)

            result = await db.execute(query, {
                "rule_id": str(rule_id),
                "skip": skip,
                "limit": limit,
            })

            history = [dict(row._mapping) for row in result.fetchall()]
            return history, total

        except Exception as e:
            logger.error(f"Failed to get history for rule {rule_id}: {e}")
            raise

    async def get_all_history(
        self,
        db: AsyncSession,
        filters: dict[str, Any] | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Get all workflow execution history.

        Args:
            db: Database session
            filters: Optional filters (rule_id, case_id, success)
            skip: Pagination offset
            limit: Maximum entries to return

        Returns:
            Tuple of (list of history entries, total count)
        """
        try:
            filters = filters or {}
            where_clauses = []
            params: dict[str, Any] = {"skip": skip, "limit": limit}

            if "rule_id" in filters:
                where_clauses.append("rule_id = :rule_id")
                params["rule_id"] = str(filters["rule_id"])

            if "case_id" in filters:
                where_clauses.append("case_id = :case_id")
                params["case_id"] = str(filters["case_id"])

            if "success" in filters:
                where_clauses.append("success = :success")
                params["success"] = filters["success"]

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            # Count query
            count_query = text(f"""
                SELECT COUNT(*) as count FROM workflow_history WHERE {where_sql}
            """)
            count_result = await db.execute(count_query, params)
            total = count_result.scalar() or 0

            # Main query
            query = text(f"""
                SELECT * FROM workflow_history
                WHERE {where_sql}
                ORDER BY started_at DESC
                OFFSET :skip LIMIT :limit
            """)

            result = await db.execute(query, params)
            history = [dict(row._mapping) for row in result.fetchall()]

            return history, total

        except Exception as e:
            logger.error(f"Failed to get workflow history: {e}")
            raise


# Singleton instance
workflow_service = WorkflowService()
