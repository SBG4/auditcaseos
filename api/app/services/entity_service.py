"""Entity extraction service for AuditCaseOS.

Extracts entities (employee IDs, IPs, emails, hostnames) from text
using regex patterns for forensic analysis.
"""

import logging
import re
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# Entity type constants
ENTITY_TYPE_EMPLOYEE_ID = "employee_id"
ENTITY_TYPE_IP_ADDRESS = "ip_address"
ENTITY_TYPE_EMAIL = "email"
ENTITY_TYPE_HOSTNAME = "hostname"
ENTITY_TYPE_MAC_ADDRESS = "mac_address"
ENTITY_TYPE_FILE_PATH = "file_path"
ENTITY_TYPE_USB_DEVICE = "usb_device"


# Regex patterns for entity extraction
ENTITY_PATTERNS = {
    ENTITY_TYPE_EMPLOYEE_ID: [
        r"\bEMP[-_]?\d{4,8}\b",  # EMP-123456, EMP_1234, EMP12345678
        r"\bE\d{6,8}\b",  # E123456
        r"\b[A-Z]{2,4}[-_]\d{4,6}\b",  # HR-1234, IT-12345
    ],
    ENTITY_TYPE_IP_ADDRESS: [
        # IPv4
        r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b",
        # IPv6 (simplified)
        r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b",
        r"\b(?:[0-9a-fA-F]{1,4}:){1,7}:\b",
        r"\b::(?:[0-9a-fA-F]{1,4}:){0,5}[0-9a-fA-F]{1,4}\b",
    ],
    ENTITY_TYPE_EMAIL: [
        r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
    ],
    ENTITY_TYPE_HOSTNAME: [
        # Windows workstation names
        r"\b(?:WS|PC|DESKTOP|LAPTOP|SRV|SERVER)[-_][A-Z0-9]{2,}[-_][A-Z0-9]{2,}\b",
        # General hostnames (subdomain.domain.tld)
        r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b",
    ],
    ENTITY_TYPE_MAC_ADDRESS: [
        # MAC address formats
        r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b",
        r"\b(?:[0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4}\b",
    ],
    ENTITY_TYPE_FILE_PATH: [
        # Windows paths
        r"\b[A-Za-z]:\\(?:[^\\/:*?\"<>|\r\n]+\\)*[^\\/:*?\"<>|\r\n]*",
        # Unix paths
        r"\b/(?:[^/\0]+/)*[^/\0]+",
    ],
    ENTITY_TYPE_USB_DEVICE: [
        # USB device identifiers
        r"\bUSB[-_]?[A-Z0-9]{3,10}\b",
        r"\bVID_[0-9A-Fa-f]{4}&PID_[0-9A-Fa-f]{4}\b",
    ],
}


class EntityService:
    """Service for extracting and managing entities from case evidence."""

    def extract_entities(
        self,
        text_content: str,
        entity_types: list[str] | None = None,
    ) -> dict[str, list[str]]:
        """
        Extract entities from text content using regex patterns.

        Args:
            text_content: Text to extract entities from
            entity_types: Optional list of entity types to extract.
                         If None, extracts all types.

        Returns:
            Dictionary mapping entity types to lists of unique extracted values
        """
        if not text_content:
            return {}

        # Use all types if none specified
        types_to_extract = entity_types or list(ENTITY_PATTERNS.keys())

        results: dict[str, list[str]] = {}

        for entity_type in types_to_extract:
            patterns = ENTITY_PATTERNS.get(entity_type, [])
            matches: set[str] = set()

            for pattern in patterns:
                try:
                    found = re.findall(pattern, text_content, re.IGNORECASE)
                    matches.update(found)
                except re.error as e:
                    logger.warning(f"Invalid regex pattern for {entity_type}: {e}")
                    continue

            if matches:
                # Sort for consistent output
                results[entity_type] = sorted(matches)

        return results

    def extract_all_entities(
        self,
        text_content: str,
    ) -> list[dict[str, str]]:
        """
        Extract all entities and return as a flat list.

        Args:
            text_content: Text to extract entities from

        Returns:
            List of dicts with entity_type and value keys
        """
        extracted = self.extract_entities(text_content)
        entities = []

        for entity_type, values in extracted.items():
            for value in values:
                entities.append({
                    "entity_type": entity_type,
                    "value": value,
                })

        return entities

    async def store_entities(
        self,
        db: AsyncSession,
        case_id: UUID,
        evidence_id: UUID | None,
        entities: list[dict[str, str]],
        source: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Store extracted entities in the database.

        Args:
            db: Database session
            case_id: Case UUID
            evidence_id: Evidence UUID (optional)
            entities: List of entities with entity_type and value
            source: Source description (e.g., "OCR extraction")

        Returns:
            List of created entity records
        """
        if not entities:
            return []

        created = []

        for entity in entities:
            try:
                # Use INSERT ON CONFLICT to handle duplicates atomically
                # Handle evidence_id separately to avoid NULL type issues with asyncpg
                if evidence_id:
                    insert_query = text("""
                        INSERT INTO case_entities (
                            case_id, evidence_ids, entity_type, value, source, occurrence_count
                        ) VALUES (
                            :case_id,
                            ARRAY[CAST(:evidence_id AS UUID)],
                            :entity_type,
                            :value,
                            :source,
                            1
                        )
                        ON CONFLICT (case_id, entity_type, value) DO UPDATE SET
                            evidence_ids = CASE
                                WHEN NOT (CAST(:evidence_id AS UUID) = ANY(COALESCE(case_entities.evidence_ids, ARRAY[]::UUID[])))
                                THEN array_append(COALESCE(case_entities.evidence_ids, ARRAY[]::UUID[]), CAST(:evidence_id AS UUID))
                                ELSE case_entities.evidence_ids
                            END,
                            occurrence_count = case_entities.occurrence_count + 1,
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING *, (xmax = 0) as is_new
                    """)
                    params = {
                        "case_id": str(case_id),
                        "evidence_id": str(evidence_id),
                        "entity_type": entity["entity_type"],
                        "value": entity["value"],
                        "source": source,
                    }
                else:
                    insert_query = text("""
                        INSERT INTO case_entities (
                            case_id, evidence_ids, entity_type, value, source, occurrence_count
                        ) VALUES (
                            :case_id,
                            ARRAY[]::UUID[],
                            :entity_type,
                            :value,
                            :source,
                            1
                        )
                        ON CONFLICT (case_id, entity_type, value) DO UPDATE SET
                            occurrence_count = case_entities.occurrence_count + 1,
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING *, (xmax = 0) as is_new
                    """)
                    params = {
                        "case_id": str(case_id),
                        "entity_type": entity["entity_type"],
                        "value": entity["value"],
                        "source": source,
                    }

                result = await db.execute(insert_query, params)

                row = result.fetchone()
                if row:
                    row_dict = dict(row._mapping)
                    # Only count as new if is_new flag is True
                    if row_dict.pop("is_new", False):
                        created.append(row_dict)

            except Exception as e:
                logger.error(f"Failed to store entity {entity}: {e}")
                # Rollback to clear failed transaction state
                await db.rollback()
                continue

        await db.commit()
        logger.info(f"Stored {len(created)} new entities for case {case_id}")

        return created

    async def get_case_entities(
        self,
        db: AsyncSession,
        case_id: UUID,
        entity_type: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get entities for a case with optional filtering.

        Args:
            db: Database session
            case_id: Case UUID
            entity_type: Optional filter by entity type
            skip: Offset for pagination
            limit: Max results

        Returns:
            List of entity records
        """
        try:
            params: dict[str, Any] = {
                "case_id": str(case_id),
                "skip": skip,
                "limit": limit,
            }

            where_clause = "case_id = :case_id"
            if entity_type:
                where_clause += " AND entity_type = :entity_type"
                params["entity_type"] = entity_type

            query = text(f"""
                SELECT * FROM case_entities
                WHERE {where_clause}
                ORDER BY entity_type, occurrence_count DESC, value
                OFFSET :skip LIMIT :limit
            """)

            result = await db.execute(query, params)
            rows = result.fetchall()

            return [dict(row._mapping) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get entities for case {case_id}: {e}")
            raise

    async def count_case_entities(
        self,
        db: AsyncSession,
        case_id: UUID,
        entity_type: str | None = None,
    ) -> int:
        """
        Count entities for a case.

        Args:
            db: Database session
            case_id: Case UUID
            entity_type: Optional filter by entity type

        Returns:
            Total count
        """
        try:
            params: dict[str, Any] = {"case_id": str(case_id)}

            where_clause = "case_id = :case_id"
            if entity_type:
                where_clause += " AND entity_type = :entity_type"
                params["entity_type"] = entity_type

            query = text(f"SELECT COUNT(*) FROM case_entities WHERE {where_clause}")
            result = await db.execute(query, params)
            row = result.fetchone()

            return row[0] if row else 0

        except Exception as e:
            logger.error(f"Failed to count entities for case {case_id}: {e}")
            raise

    async def search_entities(
        self,
        db: AsyncSession,
        value_pattern: str,
        entity_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Search for entities across all cases by value pattern.

        Args:
            db: Database session
            value_pattern: Pattern to search for (uses ILIKE)
            entity_type: Optional filter by entity type
            limit: Max results

        Returns:
            List of matching entities with case info
        """
        try:
            params: dict[str, Any] = {
                "pattern": f"%{value_pattern}%",
                "limit": limit,
            }

            where_clause = "e.value ILIKE :pattern"
            if entity_type:
                where_clause += " AND e.entity_type = :entity_type"
                params["entity_type"] = entity_type

            query = text(f"""
                SELECT e.*, c.case_id as case_id_str, c.title as case_title
                FROM case_entities e
                JOIN cases c ON e.case_id = c.id
                WHERE {where_clause}
                ORDER BY e.occurrence_count DESC, e.created_at DESC
                LIMIT :limit
            """)

            result = await db.execute(query, params)
            rows = result.fetchall()

            return [dict(row._mapping) for row in rows]

        except Exception as e:
            logger.error(f"Failed to search entities: {e}")
            raise

    async def get_entity_summary(
        self,
        db: AsyncSession,
        case_id: UUID,
    ) -> dict[str, int]:
        """
        Get a summary of entity counts by type for a case.

        Args:
            db: Database session
            case_id: Case UUID

        Returns:
            Dictionary mapping entity types to counts
        """
        try:
            query = text("""
                SELECT entity_type, COUNT(*) as count
                FROM case_entities
                WHERE case_id = :case_id
                GROUP BY entity_type
                ORDER BY count DESC
            """)

            result = await db.execute(query, {"case_id": str(case_id)})
            rows = result.fetchall()

            return {row.entity_type: row.count for row in rows}

        except Exception as e:
            logger.error(f"Failed to get entity summary for case {case_id}: {e}")
            raise

    async def extract_and_store_from_evidence(
        self,
        db: AsyncSession,
        case_id: UUID,
        evidence_id: UUID,
        text_content: str,
        source: str = "evidence_extraction",
    ) -> dict[str, Any]:
        """
        Extract entities from evidence text and store them.

        Convenience method that combines extraction and storage.

        Args:
            db: Database session
            case_id: Case UUID
            evidence_id: Evidence UUID
            text_content: Text to extract from
            source: Source description

        Returns:
            Summary of extraction results
        """
        # Extract entities
        entities = self.extract_all_entities(text_content)

        if not entities:
            return {
                "extracted_count": 0,
                "stored_count": 0,
                "entities_by_type": {},
            }

        # Count by type before storing
        by_type: dict[str, int] = {}
        for entity in entities:
            entity_type = entity["entity_type"]
            by_type[entity_type] = by_type.get(entity_type, 0) + 1

        # Store entities
        stored = await self.store_entities(
            db=db,
            case_id=case_id,
            evidence_id=evidence_id,
            entities=entities,
            source=source,
        )

        return {
            "extracted_count": len(entities),
            "stored_count": len(stored),
            "entities_by_type": by_type,
        }


# Singleton instance
entity_service = EntityService()
