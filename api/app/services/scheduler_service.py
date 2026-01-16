"""Scheduler service for time-based workflow rules.

This module provides background task scheduling using APScheduler
for executing time-based workflow rules.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for managing scheduled workflow executions."""

    def __init__(self):
        self.scheduler: AsyncIOScheduler | None = None
        self._initialized = False
        self._engine = None
        self._session_factory = None

    async def _get_db_session(self) -> AsyncSession:
        """Create a new database session for scheduled tasks."""
        if not self._engine:
            settings = get_settings()
            self._engine = create_async_engine(settings.database_url)
            self._session_factory = sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
        return self._session_factory()

    def start(self) -> None:
        """Start the scheduler."""
        if self._initialized:
            return

        self.scheduler = AsyncIOScheduler(
            timezone="UTC",
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 300,
            },
        )

        # Add job to check time-based rules every minute
        self.scheduler.add_job(
            self._check_time_based_rules,
            IntervalTrigger(minutes=1),
            id="check_time_based_rules",
            name="Check time-based workflow rules",
            replace_existing=True,
        )

        # Add job to clean up old notifications daily
        self.scheduler.add_job(
            self._cleanup_old_notifications,
            CronTrigger(hour=2, minute=0),  # Run at 2 AM UTC
            id="cleanup_notifications",
            name="Clean up old notifications",
            replace_existing=True,
        )

        self.scheduler.start()
        self._initialized = True
        logger.info("Scheduler service started")

    def stop(self) -> None:
        """Stop the scheduler."""
        if self.scheduler:
            self.scheduler.shutdown(wait=False)
            self._initialized = False
            logger.info("Scheduler service stopped")

    async def _check_time_based_rules(self) -> None:
        """Check and execute time-based workflow rules."""
        try:
            db = await self._get_db_session()
            try:
                # Get enabled time-based rules
                query = text("""
                    SELECT * FROM workflow_rules
                    WHERE is_enabled = true
                    AND trigger_type = 'TIME_BASED'
                """)
                result = await db.execute(query)
                rules = [dict(row._mapping) for row in result.fetchall()]

                for rule in rules:
                    await self._evaluate_time_based_rule(db, rule)

            finally:
                await db.close()

        except Exception as e:
            logger.error(f"Error checking time-based rules: {e}")

    async def _evaluate_time_based_rule(
        self,
        db: AsyncSession,
        rule: dict[str, Any],
    ) -> None:
        """
        Evaluate a single time-based rule.

        Time-based rules can have these trigger_config options:
        - schedule: cron expression (e.g., "0 9 * * 1" for 9 AM every Monday)
        - condition: status condition to check (e.g., "status_unchanged_days": 7)
        """
        try:
            trigger_config = rule.get("trigger_config", {})

            # Handle "status_unchanged" condition
            if "status_unchanged_days" in trigger_config:
                days = trigger_config["status_unchanged_days"]
                from_status = trigger_config.get("from_status")

                await self._execute_status_unchanged_rule(db, rule, days, from_status)

            # Handle "case_open_duration" condition
            elif "case_open_days" in trigger_config:
                days = trigger_config["case_open_days"]
                await self._execute_case_open_duration_rule(db, rule, days)

        except Exception as e:
            logger.error(f"Error evaluating time-based rule {rule.get('id')}: {e}")

    async def _execute_status_unchanged_rule(
        self,
        db: AsyncSession,
        rule: dict[str, Any],
        days: int,
        from_status: str | None,
    ) -> None:
        """Execute rule for cases with unchanged status for N days."""
        from app.services.workflow_executor import workflow_executor
        from app.services.workflow_service import workflow_service

        try:
            # Find cases that haven't been updated in N days
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            query_params: dict[str, Any] = {"cutoff_date": cutoff_date}
            status_filter = ""

            if from_status:
                status_filter = "AND status = CAST(:from_status AS case_status)"
                query_params["from_status"] = from_status

            # Filter by scope/case_type if specified in rule
            scope_filter = ""
            type_filter = ""

            if rule.get("scope_codes"):
                scope_filter = "AND scope_code = ANY(:scope_codes)"
                query_params["scope_codes"] = rule["scope_codes"]

            if rule.get("case_types"):
                type_filter = "AND case_type = ANY(:case_types)"
                query_params["case_types"] = rule["case_types"]

            query = text(f"""
                SELECT * FROM cases
                WHERE status NOT IN ('CLOSED', 'ARCHIVED')
                AND updated_at < :cutoff_date
                {status_filter}
                {scope_filter}
                {type_filter}
            """)

            result = await db.execute(query, query_params)
            cases = [dict(row._mapping) for row in result.fetchall()]

            # Get actions for rule
            actions_query = text("""
                SELECT * FROM workflow_actions
                WHERE rule_id = :rule_id
                ORDER BY sequence
            """)
            actions_result = await db.execute(actions_query, {"rule_id": str(rule["id"])})
            rule["actions"] = [dict(row._mapping) for row in actions_result.fetchall()]

            for case_data in cases:
                try:
                    trigger_data = {
                        "days_unchanged": days,
                        "from_status": from_status,
                        "time_based": True,
                    }

                    result = await workflow_executor.execute_rule(
                        db=db,
                        rule=rule,
                        case_data=case_data,
                        trigger_data=trigger_data,
                        triggered_by=f"scheduler:status_unchanged_{days}d",
                    )

                    await workflow_service.log_execution(
                        db=db,
                        rule=rule,
                        case_data=case_data,
                        trigger_type="TIME_BASED",
                        trigger_data=trigger_data,
                        actions_executed=result["actions_executed"],
                        success=result["success"],
                        error_message=result.get("error_message"),
                        triggered_by=f"scheduler:status_unchanged_{days}d",
                    )

                    logger.info(
                        f"Time-based rule '{rule['name']}' executed for case "
                        f"{case_data.get('case_id')} - success: {result['success']}"
                    )

                except Exception as case_error:
                    logger.error(
                        f"Failed to execute time-based rule for case "
                        f"{case_data.get('case_id')}: {case_error}"
                    )

        except Exception as e:
            logger.error(f"Error executing status_unchanged rule: {e}")

    async def _execute_case_open_duration_rule(
        self,
        db: AsyncSession,
        rule: dict[str, Any],
        days: int,
    ) -> None:
        """Execute rule for cases open for more than N days."""
        from app.services.workflow_executor import workflow_executor
        from app.services.workflow_service import workflow_service

        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            query_params: dict[str, Any] = {"cutoff_date": cutoff_date}

            # Filter by scope/case_type if specified
            scope_filter = ""
            type_filter = ""

            if rule.get("scope_codes"):
                scope_filter = "AND scope_code = ANY(:scope_codes)"
                query_params["scope_codes"] = rule["scope_codes"]

            if rule.get("case_types"):
                type_filter = "AND case_type = ANY(:case_types)"
                query_params["case_types"] = rule["case_types"]

            query = text(f"""
                SELECT * FROM cases
                WHERE status NOT IN ('CLOSED', 'ARCHIVED')
                AND created_at < :cutoff_date
                {scope_filter}
                {type_filter}
            """)

            result = await db.execute(query, query_params)
            cases = [dict(row._mapping) for row in result.fetchall()]

            # Get actions for rule
            actions_query = text("""
                SELECT * FROM workflow_actions
                WHERE rule_id = :rule_id
                ORDER BY sequence
            """)
            actions_result = await db.execute(actions_query, {"rule_id": str(rule["id"])})
            rule["actions"] = [dict(row._mapping) for row in actions_result.fetchall()]

            for case_data in cases:
                try:
                    trigger_data = {
                        "days_open": days,
                        "time_based": True,
                    }

                    result = await workflow_executor.execute_rule(
                        db=db,
                        rule=rule,
                        case_data=case_data,
                        trigger_data=trigger_data,
                        triggered_by=f"scheduler:case_open_{days}d",
                    )

                    await workflow_service.log_execution(
                        db=db,
                        rule=rule,
                        case_data=case_data,
                        trigger_type="TIME_BASED",
                        trigger_data=trigger_data,
                        actions_executed=result["actions_executed"],
                        success=result["success"],
                        error_message=result.get("error_message"),
                        triggered_by=f"scheduler:case_open_{days}d",
                    )

                except Exception as case_error:
                    logger.error(
                        f"Failed to execute case_open rule for case "
                        f"{case_data.get('case_id')}: {case_error}"
                    )

        except Exception as e:
            logger.error(f"Error executing case_open_duration rule: {e}")

    async def _cleanup_old_notifications(self) -> None:
        """Clean up notifications older than 90 days."""
        try:
            db = await self._get_db_session()
            try:
                from app.services.notification_service import notification_service
                deleted = await notification_service.delete_old_notifications(db, days=90)
                logger.info(f"Cleaned up {deleted} old notifications")
            finally:
                await db.close()

        except Exception as e:
            logger.error(f"Error cleaning up old notifications: {e}")


# Singleton instance
scheduler_service = SchedulerService()
