"""Search service for AuditCaseOS.

Implements hybrid search combining keyword matching (ILIKE) with
semantic similarity (pgvector) for comprehensive search across
cases, evidence, findings, entities, and timeline events.
"""

import logging
import time
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)

# Hybrid search weights
KEYWORD_WEIGHT = 0.4
SEMANTIC_WEIGHT = 0.6


class SearchService:
    """Service for full-text and semantic search across all entities."""

    def __init__(self):
        """Initialize the search service."""
        self.embedding_service = embedding_service
        logger.info("SearchService initialized")

    async def search(
        self,
        db: AsyncSession,
        query: str,
        entity_types: list[str] | None = None,
        mode: str = "hybrid",
        scope_codes: list[str] | None = None,
        case_types: list[str] | None = None,
        statuses: list[str] | None = None,
        severities: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        min_similarity: float = 0.5,
        skip: int = 0,
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        Execute hybrid search across entities.

        Args:
            db: Database session
            query: Search query text
            entity_types: List of entity types to search (case, evidence, finding, entity, timeline)
            mode: Search mode (keyword, semantic, hybrid)
            scope_codes: Filter by scope codes
            case_types: Filter by case types
            statuses: Filter by case statuses
            severities: Filter by severities
            date_from: Filter by date range start
            date_to: Filter by date range end
            min_similarity: Minimum similarity for semantic search (0-1)
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            Dict with items, total, entity_type_counts, search_time_ms
        """
        start_time = time.time()
        results: list[dict[str, Any]] = []
        entity_type_counts: dict[str, int] = {}

        # Determine which entity types to search
        search_all = not entity_types or "all" in entity_types
        search_types = (
            entity_types
            if not search_all
            else ["case", "evidence", "finding", "entity", "timeline"]
        )

        # Execute search based on mode
        if mode in ("keyword", "hybrid"):
            keyword_results = await self._keyword_search(
                db=db,
                query=query,
                entity_types=search_types,
                scope_codes=scope_codes,
                case_types=case_types,
                statuses=statuses,
                severities=severities,
                date_from=date_from,
                date_to=date_to,
            )
            results.extend(keyword_results)

        if mode in ("semantic", "hybrid"):
            semantic_results = await self._semantic_search(
                db=db,
                query=query,
                entity_types=search_types,
                min_similarity=min_similarity,
                scope_codes=scope_codes,
            )
            # Merge semantic results with keyword results
            results = self._merge_results(results, semantic_results, mode)

        # Sort by combined score
        results.sort(key=lambda x: x["combined_score"], reverse=True)

        # Count by entity type
        for result in results:
            et = result["entity_type"]
            entity_type_counts[et] = entity_type_counts.get(et, 0) + 1

        # Apply pagination
        total = len(results)
        paginated_results = results[skip : skip + limit]

        search_time_ms = (time.time() - start_time) * 1000

        logger.info(
            f"Search completed: query='{query}', mode={mode}, "
            f"total={total}, time={search_time_ms:.1f}ms"
        )

        return {
            "items": paginated_results,
            "total": total,
            "entity_type_counts": entity_type_counts,
            "search_time_ms": round(search_time_ms, 2),
        }

    async def _keyword_search(
        self,
        db: AsyncSession,
        query: str,
        entity_types: list[str],
        scope_codes: list[str] | None = None,
        case_types: list[str] | None = None,
        statuses: list[str] | None = None,
        severities: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict[str, Any]]:
        """Execute keyword search using ILIKE across entities."""
        results: list[dict[str, Any]] = []
        pattern = f"%{query}%"

        # Search Cases
        if "case" in entity_types:
            case_results = await self._search_cases_keyword(
                db,
                pattern,
                scope_codes,
                case_types,
                statuses,
                severities,
                date_from,
                date_to,
            )
            results.extend(case_results)

        # Search Evidence
        if "evidence" in entity_types:
            evidence_results = await self._search_evidence_keyword(
                db, pattern, scope_codes
            )
            results.extend(evidence_results)

        # Search Findings
        if "finding" in entity_types:
            finding_results = await self._search_findings_keyword(
                db, pattern, scope_codes, severities
            )
            results.extend(finding_results)

        # Search Entities
        if "entity" in entity_types:
            entity_results = await self._search_entities_keyword(
                db, pattern, scope_codes
            )
            results.extend(entity_results)

        # Search Timeline
        if "timeline" in entity_types:
            timeline_results = await self._search_timeline_keyword(
                db, pattern, scope_codes
            )
            results.extend(timeline_results)

        return results

    async def _search_cases_keyword(
        self,
        db: AsyncSession,
        pattern: str,
        scope_codes: list[str] | None,
        case_types: list[str] | None,
        statuses: list[str] | None,
        severities: list[str] | None,
        date_from: str | None,
        date_to: str | None,
    ) -> list[dict[str, Any]]:
        """Search cases using ILIKE."""
        where_clauses = [
            "(c.title ILIKE :pattern OR c.summary ILIKE :pattern OR "
            "c.description ILIKE :pattern OR c.case_id ILIKE :pattern OR "
            "c.subject_user ILIKE :pattern)"
        ]
        params: dict[str, Any] = {"pattern": pattern}

        if scope_codes:
            where_clauses.append("c.scope_code = ANY(:scope_codes)")
            params["scope_codes"] = scope_codes
        if case_types:
            where_clauses.append("c.case_type::text = ANY(:case_types)")
            params["case_types"] = case_types
        if statuses:
            where_clauses.append("c.status::text = ANY(:statuses)")
            params["statuses"] = statuses
        if severities:
            where_clauses.append("c.severity::text = ANY(:severities)")
            params["severities"] = severities
        if date_from:
            where_clauses.append("c.created_at >= :date_from")
            params["date_from"] = date_from
        if date_to:
            where_clauses.append("c.created_at <= :date_to")
            params["date_to"] = date_to

        where_sql = " AND ".join(where_clauses)

        sql = text(f"""
            SELECT
                c.id, c.case_id, c.title, c.summary, c.status, c.severity,
                c.scope_code, c.case_type, c.created_at
            FROM cases c
            WHERE {where_sql}
            ORDER BY c.created_at DESC
            LIMIT 100
        """)

        result = await db.execute(sql, params)
        rows = result.fetchall()

        return [
            {
                "id": str(row.id),
                "entity_type": "case",
                "title": row.title,
                "snippet": (row.summary or "")[:200],
                "keyword_score": 1.0,
                "semantic_score": 0.0,
                "combined_score": KEYWORD_WEIGHT,
                "case_id": row.case_id,
                "case_uuid": str(row.id),
                "metadata": {
                    "status": str(row.status),
                    "severity": str(row.severity),
                    "scope_code": row.scope_code,
                    "case_type": str(row.case_type),
                },
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]

    async def _search_evidence_keyword(
        self,
        db: AsyncSession,
        pattern: str,
        scope_codes: list[str] | None,
    ) -> list[dict[str, Any]]:
        """Search evidence using ILIKE."""
        where_clauses = [
            "(e.file_name ILIKE :pattern OR e.description ILIKE :pattern OR "
            "e.extracted_text ILIKE :pattern)"
        ]
        params: dict[str, Any] = {"pattern": pattern}

        if scope_codes:
            where_clauses.append("c.scope_code = ANY(:scope_codes)")
            params["scope_codes"] = scope_codes

        where_sql = " AND ".join(where_clauses)

        sql = text(f"""
            SELECT
                e.id, e.file_name, e.description, e.extracted_text,
                e.uploaded_at, c.case_id, c.id as case_uuid
            FROM evidence e
            JOIN cases c ON e.case_id = c.id
            WHERE {where_sql}
            ORDER BY e.uploaded_at DESC
            LIMIT 100
        """)

        result = await db.execute(sql, params)
        rows = result.fetchall()

        return [
            {
                "id": str(row.id),
                "entity_type": "evidence",
                "title": row.file_name,
                "snippet": (row.description or row.extracted_text or "")[:200],
                "keyword_score": 1.0,
                "semantic_score": 0.0,
                "combined_score": KEYWORD_WEIGHT,
                "case_id": row.case_id,
                "case_uuid": str(row.case_uuid),
                "metadata": {},
                "created_at": row.uploaded_at.isoformat(),
            }
            for row in rows
        ]

    async def _search_findings_keyword(
        self,
        db: AsyncSession,
        pattern: str,
        scope_codes: list[str] | None,
        severities: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Search findings using ILIKE."""
        where_clauses = [
            "(f.title ILIKE :pattern OR f.description ILIKE :pattern)"
        ]
        params: dict[str, Any] = {"pattern": pattern}

        if scope_codes:
            where_clauses.append("c.scope_code = ANY(:scope_codes)")
            params["scope_codes"] = scope_codes
        if severities:
            where_clauses.append("f.severity::text = ANY(:severities)")
            params["severities"] = severities

        where_sql = " AND ".join(where_clauses)

        sql = text(f"""
            SELECT
                f.id, f.title, f.description, f.severity, f.created_at,
                c.case_id, c.id as case_uuid
            FROM findings f
            JOIN cases c ON f.case_id = c.id
            WHERE {where_sql}
            ORDER BY f.created_at DESC
            LIMIT 100
        """)

        result = await db.execute(sql, params)
        rows = result.fetchall()

        return [
            {
                "id": str(row.id),
                "entity_type": "finding",
                "title": row.title,
                "snippet": (row.description or "")[:200],
                "keyword_score": 1.0,
                "semantic_score": 0.0,
                "combined_score": KEYWORD_WEIGHT,
                "case_id": row.case_id,
                "case_uuid": str(row.case_uuid),
                "metadata": {"severity": str(row.severity)},
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]

    async def _search_entities_keyword(
        self,
        db: AsyncSession,
        pattern: str,
        scope_codes: list[str] | None,
    ) -> list[dict[str, Any]]:
        """Search case entities using ILIKE."""
        where_clauses = ["ce.value ILIKE :pattern"]
        params: dict[str, Any] = {"pattern": pattern}

        if scope_codes:
            where_clauses.append("c.scope_code = ANY(:scope_codes)")
            params["scope_codes"] = scope_codes

        where_sql = " AND ".join(where_clauses)

        sql = text(f"""
            SELECT
                ce.id, ce.entity_type, ce.value, ce.occurrence_count,
                ce.created_at, c.case_id, c.id as case_uuid
            FROM case_entities ce
            JOIN cases c ON ce.case_id = c.id
            WHERE {where_sql}
            ORDER BY ce.occurrence_count DESC
            LIMIT 100
        """)

        result = await db.execute(sql, params)
        rows = result.fetchall()

        return [
            {
                "id": str(row.id),
                "entity_type": "entity",
                "title": f"{row.entity_type}: {row.value}",
                "snippet": f"Found {row.occurrence_count} time(s)",
                "keyword_score": 1.0,
                "semantic_score": 0.0,
                "combined_score": KEYWORD_WEIGHT,
                "case_id": row.case_id,
                "case_uuid": str(row.case_uuid),
                "metadata": {
                    "extracted_entity_type": row.entity_type,
                    "value": row.value,
                    "occurrence_count": row.occurrence_count,
                },
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]

    async def _search_timeline_keyword(
        self,
        db: AsyncSession,
        pattern: str,
        scope_codes: list[str] | None,
    ) -> list[dict[str, Any]]:
        """Search timeline events using ILIKE."""
        where_clauses = [
            "(t.event_type ILIKE :pattern OR t.description ILIKE :pattern)"
        ]
        params: dict[str, Any] = {"pattern": pattern}

        if scope_codes:
            where_clauses.append("c.scope_code = ANY(:scope_codes)")
            params["scope_codes"] = scope_codes

        where_sql = " AND ".join(where_clauses)

        sql = text(f"""
            SELECT
                t.id, t.event_type, t.description, t.event_time, t.created_at,
                c.case_id, c.id as case_uuid
            FROM timeline_events t
            JOIN cases c ON t.case_id = c.id
            WHERE {where_sql}
            ORDER BY t.event_time DESC
            LIMIT 100
        """)

        result = await db.execute(sql, params)
        rows = result.fetchall()

        return [
            {
                "id": str(row.id),
                "entity_type": "timeline",
                "title": row.event_type,
                "snippet": (row.description or "")[:200],
                "keyword_score": 1.0,
                "semantic_score": 0.0,
                "combined_score": KEYWORD_WEIGHT,
                "case_id": row.case_id,
                "case_uuid": str(row.case_uuid),
                "metadata": {"event_time": row.event_time.isoformat()},
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]

    async def _semantic_search(
        self,
        db: AsyncSession,
        query: str,
        entity_types: list[str],
        min_similarity: float = 0.5,
        scope_codes: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute semantic search using pgvector embeddings."""
        # Generate embedding for query
        query_embedding = await self.embedding_service.embed_text(query)

        if not query_embedding:
            logger.warning("Failed to generate query embedding for semantic search")
            return []

        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        # Map entity types to embedding entity_type values
        # Note: Only cases and evidence have embeddings by default
        embedding_types: list[str] = []
        if "case" in entity_types:
            embedding_types.append("case")
        if "evidence" in entity_types:
            embedding_types.append("evidence")

        if not embedding_types:
            return []

        # Query embeddings table with similarity
        sql = text("""
            SELECT
                e.entity_type,
                e.entity_id,
                e.content,
                1 - (e.embedding <=> CAST(:embedding AS vector)) as similarity
            FROM embeddings e
            WHERE e.entity_type = ANY(:entity_types)
            AND 1 - (e.embedding <=> CAST(:embedding AS vector)) >= :min_similarity
            ORDER BY similarity DESC
            LIMIT 100
        """)

        result = await db.execute(
            sql,
            {
                "embedding": embedding_str,
                "entity_types": embedding_types,
                "min_similarity": min_similarity,
            },
        )
        rows = result.fetchall()

        # Enrich results with entity details
        results: list[dict[str, Any]] = []
        for row in rows:
            enriched = await self._enrich_semantic_result(
                db,
                row.entity_type,
                str(row.entity_id),
                row.content,
                float(row.similarity),
                scope_codes,
            )
            if enriched:
                results.append(enriched)

        return results

    async def _enrich_semantic_result(
        self,
        db: AsyncSession,
        entity_type: str,
        entity_id: str,
        content: str,
        similarity: float,
        scope_codes: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Enrich semantic result with entity details."""
        if entity_type == "case":
            where_clause = "WHERE id = :entity_id"
            params: dict[str, Any] = {"entity_id": entity_id}

            if scope_codes:
                where_clause += " AND scope_code = ANY(:scope_codes)"
                params["scope_codes"] = scope_codes

            sql = text(f"""
                SELECT id, case_id, title, summary, status, severity, scope_code,
                       case_type, created_at
                FROM cases {where_clause}
            """)
            result = await db.execute(sql, params)
            row = result.fetchone()

            if row:
                return {
                    "id": str(row.id),
                    "entity_type": "case",
                    "title": row.title,
                    "snippet": content[:200],
                    "keyword_score": 0.0,
                    "semantic_score": similarity,
                    "combined_score": similarity * SEMANTIC_WEIGHT,
                    "case_id": row.case_id,
                    "case_uuid": str(row.id),
                    "metadata": {
                        "status": str(row.status),
                        "severity": str(row.severity),
                        "scope_code": row.scope_code,
                        "case_type": str(row.case_type),
                    },
                    "created_at": row.created_at.isoformat(),
                }

        elif entity_type == "evidence":
            where_clause = "WHERE e.id = :entity_id"
            params = {"entity_id": entity_id}

            if scope_codes:
                where_clause += " AND c.scope_code = ANY(:scope_codes)"
                params["scope_codes"] = scope_codes

            sql = text(f"""
                SELECT e.id, e.file_name, e.description, e.uploaded_at,
                       c.case_id, c.id as case_uuid
                FROM evidence e
                JOIN cases c ON e.case_id = c.id
                {where_clause}
            """)
            result = await db.execute(sql, params)
            row = result.fetchone()

            if row:
                return {
                    "id": str(row.id),
                    "entity_type": "evidence",
                    "title": row.file_name,
                    "snippet": content[:200],
                    "keyword_score": 0.0,
                    "semantic_score": similarity,
                    "combined_score": similarity * SEMANTIC_WEIGHT,
                    "case_id": row.case_id,
                    "case_uuid": str(row.case_uuid),
                    "metadata": {},
                    "created_at": row.uploaded_at.isoformat(),
                }

        return None

    def _merge_results(
        self,
        keyword_results: list[dict[str, Any]],
        semantic_results: list[dict[str, Any]],
        mode: str,
    ) -> list[dict[str, Any]]:
        """Merge and deduplicate keyword and semantic results."""
        # Index by (entity_type, id)
        merged: dict[tuple[str, str], dict[str, Any]] = {}

        for result in keyword_results:
            key = (result["entity_type"], result["id"])
            merged[key] = result

        for result in semantic_results:
            key = (result["entity_type"], result["id"])
            if key in merged:
                # Combine scores
                existing = merged[key]
                existing["semantic_score"] = result["semantic_score"]
                existing["combined_score"] = (
                    existing["keyword_score"] * KEYWORD_WEIGHT
                    + result["semantic_score"] * SEMANTIC_WEIGHT
                )
            else:
                merged[key] = result

        return list(merged.values())

    async def suggest(
        self,
        db: AsyncSession,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get search suggestions based on query prefix.

        Args:
            db: Database session
            query: Query prefix
            limit: Maximum suggestions

        Returns:
            List of suggestion dicts with type and value
        """
        suggestions: list[dict[str, Any]] = []
        pattern = f"{query}%"  # Prefix match

        # Case IDs
        case_id_sql = text("""
            SELECT DISTINCT case_id FROM cases
            WHERE case_id ILIKE :pattern
            LIMIT :limit
        """)
        result = await db.execute(case_id_sql, {"pattern": pattern, "limit": limit})
        suggestions.extend(
            [{"type": "case_id", "value": row[0]} for row in result.fetchall()]
        )

        # Case titles (substring match)
        title_sql = text("""
            SELECT DISTINCT title FROM cases
            WHERE title ILIKE :pattern
            LIMIT :limit
        """)
        result = await db.execute(
            title_sql, {"pattern": f"%{query}%", "limit": limit}
        )
        suggestions.extend(
            [{"type": "title", "value": row[0]} for row in result.fetchall()]
        )

        # Entity values
        entity_sql = text("""
            SELECT DISTINCT value, entity_type FROM case_entities
            WHERE value ILIKE :pattern
            LIMIT :limit
        """)
        result = await db.execute(entity_sql, {"pattern": pattern, "limit": limit})
        suggestions.extend(
            [
                {"type": "entity", "value": row[0], "entity_type": row[1]}
                for row in result.fetchall()
            ]
        )

        # Deduplicate and limit
        seen: set[str] = set()
        unique_suggestions: list[dict[str, Any]] = []
        for s in suggestions:
            if s["value"] not in seen:
                seen.add(s["value"])
                unique_suggestions.append(s)
                if len(unique_suggestions) >= limit:
                    break

        return unique_suggestions


# Singleton instance
search_service = SearchService()
