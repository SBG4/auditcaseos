"""Case service for managing audit cases."""

import json
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def _parse_json_field(value: Any, default: Any) -> Any:
    """
    Parse JSON string to Python object (handles SQLite vs PostgreSQL).

    PostgreSQL returns JSONB/ARRAY as Python objects.
    SQLite stores them as TEXT strings that need parsing.

    Args:
        value: The value to parse
        default: Default value if parsing fails or value is None

    Returns:
        Parsed value or default
    """
    if value is None:
        return default
    if isinstance(value, (list, dict)):
        return value  # Already parsed (PostgreSQL)
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
    return default


class CaseService:
    """Service for managing audit cases."""

    async def generate_case_id(
        self,
        db: AsyncSession,
        scope_code: str,
        case_type: str,
    ) -> str:
        """
        Generate a unique case ID by querying and incrementing the case_sequences table.

        Args:
            db: Database session
            scope_code: Scope code (e.g., 'FIN', 'HR', 'IT')
            case_type: Case type (e.g., 'USB', 'EMAIL', 'WEB', 'POLICY')

        Returns:
            Formatted case ID in SCOPE-TYPE-XXXX format (e.g., 'FIN-USB-0001')

        Raises:
            Exception: If database operation fails
        """
        try:
            # Use the PostgreSQL function defined in init.sql
            query = text("SELECT generate_case_id(:scope_code, :case_type)")

            result = await db.execute(
                query,
                {"scope_code": scope_code, "case_type": case_type},
            )
            row = result.fetchone()
            case_id = row[0] if row else f"{scope_code}-{case_type}-0001"

            logger.info(f"Generated case ID: {case_id}")
            return case_id

        except Exception as e:
            logger.error(f"Failed to generate case ID: {e}")
            raise

    async def create_case(
        self,
        db: AsyncSession,
        case_data: dict[str, Any],
        owner_id: UUID,
    ) -> dict[str, Any]:
        """
        Create a new audit case.

        Args:
            db: Database session
            case_data: Case data including scope_code, case_type, title, etc.
            owner_id: UUID of the case owner

        Returns:
            Created case record

        Raises:
            Exception: If case creation fails
        """
        try:
            # Generate case ID
            scope_code = case_data.get("scope_code")
            case_type = case_data.get("case_type")
            case_id = await self.generate_case_id(db, scope_code, case_type)

            # Build insert query - avoid inline type casts with asyncpg
            # PostgreSQL will handle implicit casts for enums
            query = text("""
                INSERT INTO cases (
                    case_id, scope_code, case_type, status, severity,
                    title, summary, description,
                    subject_user, subject_computer, subject_devices, related_users,
                    owner_id, assigned_to, incident_date, tags, metadata
                ) VALUES (
                    :case_id, :scope_code, CAST(:case_type AS case_type),
                    CAST(COALESCE(:status, 'OPEN') AS case_status),
                    CAST(COALESCE(:severity, 'MEDIUM') AS severity_level),
                    :title, :summary, :description,
                    :subject_user, :subject_computer, :subject_devices, :related_users,
                    :owner_id, :assigned_to, :incident_date, :tags,
                    CAST(COALESCE(:metadata, '{}') AS jsonb)
                )
                RETURNING *
            """)

            params = {
                "case_id": case_id,
                "scope_code": scope_code,
                "case_type": case_type,
                "status": case_data.get("status"),
                "severity": case_data.get("severity"),
                "title": case_data.get("title"),
                "summary": case_data.get("summary"),
                "description": case_data.get("description"),
                "subject_user": case_data.get("subject_user"),
                "subject_computer": case_data.get("subject_computer"),
                "subject_devices": case_data.get("subject_devices"),
                "related_users": case_data.get("related_users"),
                "owner_id": str(owner_id),
                "assigned_to": str(case_data["assigned_to"]) if case_data.get("assigned_to") else None,
                "incident_date": case_data.get("incident_date"),
                "tags": case_data.get("tags"),
                "metadata": case_data.get("metadata"),
            }

            result = await db.execute(query, params)
            await db.commit()

            row = result.fetchone()
            case = dict(row._mapping) if row else None

            logger.info(f"Created case: {case_id}")
            return case

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to create case: {e}")
            raise

    async def get_case(
        self,
        db: AsyncSession,
        case_id: str | UUID,
    ) -> dict[str, Any] | None:
        """
        Get a case by its case_id or UUID.

        Args:
            db: Database session
            case_id: Case ID string (e.g., 'FIN-USB-0001') or UUID

        Returns:
            Case record or None if not found
        """
        try:
            # Check if it's a UUID or case_id string
            if isinstance(case_id, UUID):
                query = text("SELECT * FROM cases WHERE id = :id")
                params = {"id": str(case_id)}
            else:
                # Try to parse as UUID first, otherwise treat as case_id string
                try:
                    uuid_val = UUID(str(case_id))
                    query = text("SELECT * FROM cases WHERE id = :id")
                    params = {"id": str(uuid_val)}
                except ValueError:
                    query = text("SELECT * FROM cases WHERE case_id = :case_id")
                    params = {"case_id": case_id}

            result = await db.execute(query, params)
            row = result.fetchone()

            if row:
                return dict(row._mapping)
            return None

        except Exception as e:
            logger.error(f"Failed to get case {case_id}: {e}")
            raise

    async def count_cases(
        self,
        db: AsyncSession,
        filters: dict[str, Any] | None = None,
    ) -> int:
        """
        Count cases with optional filtering.

        Args:
            db: Database session
            filters: Optional filters (same as list_cases)

        Returns:
            Total count of matching cases
        """
        try:
            filters = filters or {}
            where_clauses = []
            params: dict[str, Any] = {}

            # Build filter conditions (same as list_cases)
            if "scope_code" in filters:
                where_clauses.append("scope_code = :scope_code")
                params["scope_code"] = filters["scope_code"]

            if "case_type" in filters:
                where_clauses.append("case_type = CAST(:case_type AS case_type)")
                params["case_type"] = filters["case_type"]

            if "status" in filters:
                where_clauses.append("status = CAST(:status AS case_status)")
                params["status"] = filters["status"]

            if "severity" in filters:
                where_clauses.append("severity = CAST(:severity AS severity_level)")
                params["severity"] = filters["severity"]

            if "owner_id" in filters:
                where_clauses.append("owner_id = :owner_id")
                params["owner_id"] = str(filters["owner_id"])

            if "assigned_to" in filters:
                where_clauses.append("assigned_to = :assigned_to")
                params["assigned_to"] = str(filters["assigned_to"])

            if "subject_user" in filters:
                where_clauses.append("subject_user ILIKE :subject_user")
                params["subject_user"] = f"%{filters['subject_user']}%"

            if "search" in filters:
                where_clauses.append(
                    "(title ILIKE :search OR summary ILIKE :search OR description ILIKE :search OR case_id ILIKE :search)"
                )
                params["search"] = f"%{filters['search']}%"

            # Build query
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            query = text(f"SELECT COUNT(*) FROM cases WHERE {where_sql}")

            result = await db.execute(query, params)
            row = result.fetchone()

            return row[0] if row else 0

        except Exception as e:
            logger.error(f"Failed to count cases: {e}")
            raise

    async def list_cases(
        self,
        db: AsyncSession,
        filters: dict[str, Any] | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        List cases with optional filtering and pagination.

        Args:
            db: Database session
            filters: Optional filters (scope_code, case_type, status, severity, owner_id)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of case records
        """
        try:
            filters = filters or {}
            where_clauses = []
            params: dict[str, Any] = {"skip": skip, "limit": limit}

            # Build filter conditions
            if "scope_code" in filters:
                where_clauses.append("scope_code = :scope_code")
                params["scope_code"] = filters["scope_code"]

            if "case_type" in filters:
                where_clauses.append("case_type = CAST(:case_type AS case_type)")
                params["case_type"] = filters["case_type"]

            if "status" in filters:
                where_clauses.append("status = CAST(:status AS case_status)")
                params["status"] = filters["status"]

            if "severity" in filters:
                where_clauses.append("severity = CAST(:severity AS severity_level)")
                params["severity"] = filters["severity"]

            if "owner_id" in filters:
                where_clauses.append("owner_id = :owner_id")
                params["owner_id"] = str(filters["owner_id"])

            if "assigned_to" in filters:
                where_clauses.append("assigned_to = :assigned_to")
                params["assigned_to"] = str(filters["assigned_to"])

            if "subject_user" in filters:
                where_clauses.append("subject_user ILIKE :subject_user")
                params["subject_user"] = f"%{filters['subject_user']}%"

            if "search" in filters:
                where_clauses.append(
                    "(title ILIKE :search OR summary ILIKE :search OR description ILIKE :search OR case_id ILIKE :search)"
                )
                params["search"] = f"%{filters['search']}%"

            # Build query
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            query = text(f"""
                SELECT * FROM cases
                WHERE {where_sql}
                ORDER BY created_at DESC
                OFFSET :skip LIMIT :limit
            """)

            result = await db.execute(query, params)
            rows = result.fetchall()

            return [dict(row._mapping) for row in rows]

        except Exception as e:
            logger.error(f"Failed to list cases: {e}")
            raise

    async def update_case(
        self,
        db: AsyncSession,
        case_id: str | UUID,
        updates: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Update a case.

        Args:
            db: Database session
            case_id: Case ID string or UUID
            updates: Dictionary of fields to update

        Returns:
            Updated case record or None if not found
        """
        try:
            if not updates:
                return await self.get_case(db, case_id)

            # Build update clauses
            set_clauses = []
            params: dict[str, Any] = {}

            # Mapping of fields to their SQL cast types
            type_casts = {
                "case_type": "case_type",
                "status": "case_status",
                "severity": "severity_level",
                "metadata": "jsonb",
            }

            for key, value in updates.items():
                if key in ("id", "case_id", "created_at"):
                    continue  # Skip immutable fields

                if key in type_casts:
                    # Use CAST() syntax for asyncpg compatibility
                    set_clauses.append(f"{key} = CAST(:{key} AS {type_casts[key]})")
                else:
                    set_clauses.append(f"{key} = :{key}")

                if key in ("owner_id", "assigned_to") and value is not None:
                    params[key] = str(value)
                else:
                    params[key] = value

            if not set_clauses:
                return await self.get_case(db, case_id)

            set_sql = ", ".join(set_clauses)

            # Determine if case_id is UUID or string
            if isinstance(case_id, UUID):
                where_clause = "id = :identifier"
                params["identifier"] = str(case_id)
            else:
                try:
                    uuid_val = UUID(str(case_id))
                    where_clause = "id = :identifier"
                    params["identifier"] = str(uuid_val)
                except ValueError:
                    where_clause = "case_id = :identifier"
                    params["identifier"] = case_id

            query = text(f"""
                UPDATE cases
                SET {set_sql}, updated_at = CURRENT_TIMESTAMP
                WHERE {where_clause}
                RETURNING *
            """)

            result = await db.execute(query, params)
            await db.commit()

            row = result.fetchone()
            if row:
                logger.info(f"Updated case: {case_id}")
                return dict(row._mapping)
            return None

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to update case {case_id}: {e}")
            raise

    async def delete_case(
        self,
        db: AsyncSession,
        case_id: str | UUID,
    ) -> bool:
        """
        Delete a case.

        Args:
            db: Database session
            case_id: Case ID string or UUID

        Returns:
            True if deleted, False if not found
        """
        try:
            # Determine if case_id is UUID or string
            if isinstance(case_id, UUID):
                query = text("DELETE FROM cases WHERE id = :identifier RETURNING id")
                params = {"identifier": str(case_id)}
            else:
                try:
                    uuid_val = UUID(str(case_id))
                    query = text("DELETE FROM cases WHERE id = :identifier RETURNING id")
                    params = {"identifier": str(uuid_val)}
                except ValueError:
                    query = text("DELETE FROM cases WHERE case_id = :identifier RETURNING id")
                    params = {"identifier": case_id}

            result = await db.execute(query, params)
            await db.commit()

            row = result.fetchone()
            deleted = row is not None

            if deleted:
                logger.info(f"Deleted case: {case_id}")
            else:
                logger.warning(f"Case not found for deletion: {case_id}")

            return deleted

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to delete case {case_id}: {e}")
            raise


    async def get_user_brief(
        self,
        db: AsyncSession,
        user_id: UUID | str,
    ) -> dict[str, Any] | None:
        """
        Get brief user info for embedding in responses.

        Args:
            db: Database session
            user_id: User UUID

        Returns:
            User dict with id, full_name, email or None
        """
        try:
            query = text("SELECT id, full_name, email FROM users WHERE id = :user_id")
            result = await db.execute(query, {"user_id": str(user_id)})
            row = result.fetchone()
            if row:
                return dict(row._mapping)
            return None
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None

    async def get_case_counts(
        self,
        db: AsyncSession,
        case_uuid: UUID | str,
    ) -> dict[str, int]:
        """
        Get evidence and findings counts for a case.

        Args:
            db: Database session
            case_uuid: Case UUID (internal ID)

        Returns:
            Dict with evidence_count and findings_count
        """
        try:
            query = text("""
                SELECT
                    (SELECT COUNT(*) FROM evidence WHERE case_id = :case_uuid) as evidence_count,
                    (SELECT COUNT(*) FROM findings WHERE case_id = :case_uuid) as findings_count
            """)
            result = await db.execute(query, {"case_uuid": str(case_uuid)})
            row = result.fetchone()
            if row:
                return {
                    "evidence_count": row.evidence_count or 0,
                    "findings_count": row.findings_count or 0,
                }
            return {"evidence_count": 0, "findings_count": 0}
        except Exception as e:
            logger.error(f"Failed to get case counts: {e}")
            return {"evidence_count": 0, "findings_count": 0}

    async def build_case_response(
        self,
        db: AsyncSession,
        case_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Build a complete case response with user info and counts.

        Args:
            db: Database session
            case_data: Raw case data from database

        Returns:
            Complete case response dict
        """
        # Parse JSON fields (handles SQLite vs PostgreSQL differences)
        # SQLite stores arrays as TEXT, PostgreSQL returns them as lists
        case_data["tags"] = _parse_json_field(case_data.get("tags"), [])
        case_data["subject_devices"] = _parse_json_field(case_data.get("subject_devices"), [])
        case_data["related_users"] = _parse_json_field(case_data.get("related_users"), [])

        # Get owner info
        owner = await self.get_user_brief(db, case_data["owner_id"])

        # Get assignee info if assigned
        assigned_to = None
        if case_data.get("assigned_to"):
            assigned_to = await self.get_user_brief(db, case_data["assigned_to"])

        # Get counts
        counts = await self.get_case_counts(db, case_data["id"])

        return {
            **case_data,
            "owner": owner,
            "assigned_to": assigned_to,
            **counts,
        }


    async def get_case_findings(
        self,
        db: AsyncSession,
        case_uuid: UUID | str,
    ) -> list[dict[str, Any]]:
        """
        Get all findings for a case.

        Args:
            db: Database session
            case_uuid: Case UUID (internal ID)

        Returns:
            List of findings
        """
        try:
            query = text("""
                SELECT id, title, description, severity, evidence_ids,
                       created_by, created_at, updated_at
                FROM findings
                WHERE case_id = :case_uuid
                ORDER BY
                    CASE severity
                        WHEN 'CRITICAL' THEN 1
                        WHEN 'HIGH' THEN 2
                        WHEN 'MEDIUM' THEN 3
                        WHEN 'LOW' THEN 4
                        ELSE 5
                    END,
                    created_at DESC
            """)
            result = await db.execute(query, {"case_uuid": str(case_uuid)})
            rows = result.fetchall()
            return [dict(row._mapping) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get findings for case {case_uuid}: {e}")
            return []

    async def get_case_timeline(
        self,
        db: AsyncSession,
        case_uuid: UUID | str,
    ) -> list[dict[str, Any]]:
        """
        Get all timeline events for a case.

        Args:
            db: Database session
            case_uuid: Case UUID (internal ID)

        Returns:
            List of timeline events ordered by event_time
        """
        try:
            query = text("""
                SELECT id, event_time, event_type, description,
                       source, evidence_id, created_by, created_at
                FROM timeline_events
                WHERE case_id = :case_uuid
                ORDER BY event_time ASC
            """)
            result = await db.execute(query, {"case_uuid": str(case_uuid)})
            rows = result.fetchall()
            return [dict(row._mapping) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get timeline for case {case_uuid}: {e}")
            return []

    async def get_case_evidence(
        self,
        db: AsyncSession,
        case_uuid: UUID | str,
    ) -> list[dict[str, Any]]:
        """
        Get all evidence for a case.

        Args:
            db: Database session
            case_uuid: Case UUID (internal ID)

        Returns:
            List of evidence items
        """
        try:
            query = text("""
                SELECT id, file_name, file_path, file_size, mime_type,
                       file_hash, description, uploaded_by, uploaded_at,
                       extracted_text, metadata
                FROM evidence
                WHERE case_id = :case_uuid
                ORDER BY uploaded_at DESC
            """)
            result = await db.execute(query, {"case_uuid": str(case_uuid)})
            rows = result.fetchall()
            return [dict(row._mapping) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get evidence for case {case_uuid}: {e}")
            return []


# Singleton instance
case_service = CaseService()
