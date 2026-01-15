"""Embedding service for AuditCaseOS.

Generates vector embeddings using Ollama and stores them in pgvector
for similarity search and RAG capabilities.
"""

import logging
import os
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Configuration
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
EMBEDDING_DIMENSION = 768  # nomic-embed-text produces 768-dim vectors
MAX_CHUNK_SIZE = 8000  # Characters per chunk (nomic-embed-text context ~8192 tokens)
CHUNK_OVERLAP = 200  # Overlap between chunks for context continuity


class EmbeddingService:
    """Service for generating and managing vector embeddings."""

    def __init__(
        self,
        ollama_host: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
    ):
        """
        Initialize the EmbeddingService.

        Args:
            ollama_host: Ollama API host URL
            model: Embedding model to use
            timeout: Request timeout in seconds
        """
        self.ollama_host = (
            ollama_host or os.getenv("OLLAMA_HOST", "http://ollama:11434")
        ).rstrip("/")
        self.model = model or EMBEDDING_MODEL
        self.timeout = timeout
        self.dimension = EMBEDDING_DIMENSION

        logger.info(
            f"EmbeddingService initialized: {self.ollama_host} (model: {self.model})"
        )

    def chunk_text(
        self,
        text: str,
        max_size: int = MAX_CHUNK_SIZE,
        overlap: int = CHUNK_OVERLAP,
    ) -> list[str]:
        """
        Split text into overlapping chunks for embedding.

        Args:
            text: Text to chunk
            max_size: Maximum characters per chunk
            overlap: Number of characters to overlap between chunks

        Returns:
            List of text chunks
        """
        if not text or len(text) <= max_size:
            return [text] if text else []

        chunks = []
        start = 0

        while start < len(text):
            # Find end of chunk
            end = start + max_size

            # If not at the end, try to break at sentence/paragraph boundary
            if end < len(text):
                # Look for paragraph break
                para_break = text.rfind("\n\n", start, end)
                if para_break > start + max_size // 2:
                    end = para_break + 2
                else:
                    # Look for sentence break
                    for sep in [". ", ".\n", "! ", "? "]:
                        sent_break = text.rfind(sep, start, end)
                        if sent_break > start + max_size // 2:
                            end = sent_break + len(sep)
                            break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start with overlap
            start = end - overlap if end < len(text) else len(text)

        return chunks

    async def embed_text(self, text: str) -> list[float] | None:
        """
        Generate embedding vector for text using Ollama.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats, or None on failure
        """
        if not text or not text.strip():
            return None

        url = f"{self.ollama_host}/api/embeddings"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json={
                        "model": self.model,
                        "prompt": text.strip(),
                    },
                )
                response.raise_for_status()

                data = response.json()
                embedding = data.get("embedding")

                if embedding and len(embedding) == self.dimension:
                    return embedding
                else:
                    logger.warning(
                        f"Unexpected embedding dimension: {len(embedding) if embedding else 0}"
                    )
                    return embedding  # Return anyway, let DB handle dimension mismatch

        except httpx.TimeoutException:
            logger.error("Ollama embedding request timed out")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama embedding HTTP error: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Ollama embedding request failed: {e}")
            return None

    async def embed_chunks(self, chunks: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple text chunks.

        Args:
            chunks: List of text chunks

        Returns:
            List of embedding vectors
        """
        embeddings = []
        for chunk in chunks:
            embedding = await self.embed_text(chunk)
            if embedding:
                embeddings.append(embedding)
        return embeddings

    async def store_embedding(
        self,
        db: AsyncSession,
        entity_type: str,
        entity_id: UUID,
        content: str,
        embedding: list[float],
    ) -> dict[str, Any] | None:
        """
        Store an embedding in the database.

        Args:
            db: Database session
            entity_type: Type of entity (case, evidence, finding, kb)
            entity_id: UUID of the entity
            content: Original text that was embedded
            embedding: Embedding vector

        Returns:
            Created embedding record or None on failure
        """
        try:
            # Format embedding as PostgreSQL array string
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

            query = text("""
                INSERT INTO embeddings (entity_type, entity_id, content, embedding)
                VALUES (:entity_type, :entity_id, :content, CAST(:embedding AS vector))
                ON CONFLICT (entity_type, entity_id) DO UPDATE SET
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding,
                    created_at = CURRENT_TIMESTAMP
                RETURNING *
            """)

            result = await db.execute(
                query,
                {
                    "entity_type": entity_type,
                    "entity_id": str(entity_id),
                    "content": content[:10000],  # Limit stored content
                    "embedding": embedding_str,
                },
            )
            await db.commit()

            row = result.fetchone()
            if row:
                return dict(row._mapping)
            return None

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to store embedding: {e}")
            return None

    async def get_embedding(
        self,
        db: AsyncSession,
        entity_type: str,
        entity_id: UUID,
    ) -> list[float] | None:
        """
        Retrieve an embedding from the database.

        Args:
            db: Database session
            entity_type: Type of entity
            entity_id: UUID of the entity

        Returns:
            Embedding vector or None if not found
        """
        try:
            query = text("""
                SELECT embedding::text FROM embeddings
                WHERE entity_type = :entity_type AND entity_id = :entity_id
            """)

            result = await db.execute(
                query,
                {"entity_type": entity_type, "entity_id": str(entity_id)},
            )
            row = result.fetchone()

            if row and row[0]:
                # Parse PostgreSQL vector format: [0.1,0.2,...]
                vec_str = row[0].strip("[]")
                return [float(x) for x in vec_str.split(",")]
            return None

        except Exception as e:
            logger.error(f"Failed to get embedding: {e}")
            return None

    async def embed_case(
        self,
        db: AsyncSession,
        case_id: UUID,
    ) -> dict[str, Any] | None:
        """
        Generate and store embedding for a case.

        Combines case title, summary, description, and findings into
        a single text for embedding.

        Args:
            db: Database session
            case_id: Case UUID

        Returns:
            Embedding record or None on failure
        """
        try:
            # Fetch case data
            query = text("""
                SELECT c.case_id, c.title, c.summary, c.description,
                       c.case_type, c.scope_code, c.severity
                FROM cases c
                WHERE c.id = :case_id
            """)
            result = await db.execute(query, {"case_id": str(case_id)})
            case = result.fetchone()

            if not case:
                logger.warning(f"Case not found for embedding: {case_id}")
                return None

            # Fetch findings
            findings_query = text("""
                SELECT title, description FROM findings
                WHERE case_id = :case_id
                ORDER BY severity DESC
            """)
            findings_result = await db.execute(
                findings_query, {"case_id": str(case_id)}
            )
            findings = findings_result.fetchall()

            # Build content for embedding
            parts = [
                f"Case: {case.case_id}",
                f"Type: {case.case_type}",
                f"Scope: {case.scope_code}",
                f"Severity: {case.severity}",
                f"Title: {case.title}",
            ]

            if case.summary:
                parts.append(f"Summary: {case.summary}")

            if case.description:
                parts.append(f"Description: {case.description}")

            if findings:
                findings_text = "\n".join(
                    f"- {f.title}: {f.description}" for f in findings
                )
                parts.append(f"Findings:\n{findings_text}")

            content = "\n\n".join(parts)

            # Generate embedding
            embedding = await self.embed_text(content)

            if not embedding:
                logger.error(f"Failed to generate embedding for case {case_id}")
                return None

            # Store embedding
            return await self.store_embedding(
                db=db,
                entity_type="case",
                entity_id=case_id,
                content=content,
                embedding=embedding,
            )

        except Exception as e:
            logger.error(f"Failed to embed case {case_id}: {e}")
            return None

    async def embed_evidence(
        self,
        db: AsyncSession,
        evidence_id: UUID,
    ) -> dict[str, Any] | None:
        """
        Generate and store embedding for evidence.

        Uses the evidence description and extracted OCR text.

        Args:
            db: Database session
            evidence_id: Evidence UUID

        Returns:
            Embedding record or None on failure
        """
        try:
            query = text("""
                SELECT e.id, e.file_name, e.description, e.extracted_text,
                       c.case_id
                FROM evidence e
                JOIN cases c ON e.case_id = c.id
                WHERE e.id = :evidence_id
            """)
            result = await db.execute(query, {"evidence_id": str(evidence_id)})
            evidence = result.fetchone()

            if not evidence:
                logger.warning(f"Evidence not found: {evidence_id}")
                return None

            # Build content
            parts = [
                f"Evidence from case: {evidence.case_id}",
                f"File: {evidence.file_name}",
            ]

            if evidence.description:
                parts.append(f"Description: {evidence.description}")

            if evidence.extracted_text:
                # Chunk long OCR text
                chunks = self.chunk_text(evidence.extracted_text)
                if chunks:
                    # Use first chunk for primary embedding
                    parts.append(f"Content:\n{chunks[0]}")

            content = "\n\n".join(parts)

            # Generate embedding
            embedding = await self.embed_text(content)

            if not embedding:
                logger.error(f"Failed to generate embedding for evidence {evidence_id}")
                return None

            return await self.store_embedding(
                db=db,
                entity_type="evidence",
                entity_id=evidence_id,
                content=content,
                embedding=embedding,
            )

        except Exception as e:
            logger.error(f"Failed to embed evidence {evidence_id}: {e}")
            return None

    async def batch_embed_case(
        self,
        db: AsyncSession,
        case_id: UUID,
    ) -> dict[str, Any]:
        """
        Generate embeddings for a case and all its evidence.

        Args:
            db: Database session
            case_id: Case UUID

        Returns:
            Summary of embedded items
        """
        results = {
            "case_embedded": False,
            "evidence_embedded": 0,
            "errors": [],
        }

        # Embed case
        case_embedding = await self.embed_case(db, case_id)
        if case_embedding:
            results["case_embedded"] = True
        else:
            results["errors"].append("Failed to embed case")

        # Get all evidence for case
        try:
            query = text("""
                SELECT e.id FROM evidence e
                JOIN cases c ON e.case_id = c.id
                WHERE c.id = :case_id
            """)
            result = await db.execute(query, {"case_id": str(case_id)})
            evidence_ids = [row[0] for row in result.fetchall()]

            for eid in evidence_ids:
                evidence_embedding = await self.embed_evidence(db, eid)
                if evidence_embedding:
                    results["evidence_embedded"] += 1
                else:
                    results["errors"].append(f"Failed to embed evidence {eid}")

        except Exception as e:
            results["errors"].append(f"Error fetching evidence: {e}")

        logger.info(
            f"Batch embed for case {case_id}: "
            f"case={results['case_embedded']}, evidence={results['evidence_embedded']}"
        )

        return results

    async def find_similar(
        self,
        db: AsyncSession,
        entity_type: str,
        entity_id: UUID,
        limit: int = 10,
        min_similarity: float = 0.7,
        same_type_only: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Find similar entities using vector similarity search.

        Args:
            db: Database session
            entity_type: Type of source entity
            entity_id: UUID of source entity
            limit: Maximum results
            min_similarity: Minimum similarity threshold (0-1)
            same_type_only: Only return same entity type

        Returns:
            List of similar entities with similarity scores
        """
        try:
            # Get source embedding
            source_embedding = await self.get_embedding(db, entity_type, entity_id)

            if not source_embedding:
                logger.warning(f"No embedding found for {entity_type}/{entity_id}")
                return []

            # Format embedding for query
            embedding_str = "[" + ",".join(str(x) for x in source_embedding) + "]"

            # Build query with cosine similarity
            type_filter = "AND e.entity_type = :entity_type" if same_type_only else ""

            query = text(f"""
                SELECT
                    e.entity_type,
                    e.entity_id,
                    e.content,
                    1 - (e.embedding <=> CAST(:embedding AS vector)) as similarity
                FROM embeddings e
                WHERE e.entity_id != :source_id
                {type_filter}
                AND 1 - (e.embedding <=> CAST(:embedding AS vector)) >= :min_similarity
                ORDER BY similarity DESC
                LIMIT :limit
            """)

            params = {
                "embedding": embedding_str,
                "source_id": str(entity_id),
                "min_similarity": min_similarity,
                "limit": limit,
            }

            if same_type_only:
                params["entity_type"] = entity_type

            result = await db.execute(query, params)
            rows = result.fetchall()

            return [
                {
                    "entity_type": row.entity_type,
                    "entity_id": row.entity_id,
                    "content_preview": row.content[:200] if row.content else "",
                    "similarity": float(row.similarity),
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Failed to find similar entities: {e}")
            return []

    async def find_similar_cases(
        self,
        db: AsyncSession,
        case_id: UUID,
        limit: int = 10,
        min_similarity: float = 0.7,
        include_closed: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Find cases similar to the given case.

        Args:
            db: Database session
            case_id: Source case UUID
            limit: Maximum results
            min_similarity: Minimum similarity threshold
            include_closed: Include closed/archived cases

        Returns:
            List of similar cases with full details
        """
        try:
            # Get source embedding
            source_embedding = await self.get_embedding(db, "case", case_id)

            if not source_embedding:
                logger.warning(f"No embedding found for case {case_id}")
                return []

            embedding_str = "[" + ",".join(str(x) for x in source_embedding) + "]"

            # Build status filter
            status_filter = "" if include_closed else "AND c.status NOT IN ('CLOSED', 'ARCHIVED')"

            query = text(f"""
                SELECT
                    c.id,
                    c.case_id,
                    c.title,
                    c.summary,
                    c.case_type,
                    c.scope_code,
                    c.severity,
                    c.status,
                    1 - (e.embedding <=> CAST(:embedding AS vector)) as similarity
                FROM embeddings e
                JOIN cases c ON e.entity_id = c.id
                WHERE e.entity_type = 'case'
                AND e.entity_id != :source_id
                AND 1 - (e.embedding <=> CAST(:embedding AS vector)) >= :min_similarity
                {status_filter}
                ORDER BY similarity DESC
                LIMIT :limit
            """)

            result = await db.execute(
                query,
                {
                    "embedding": embedding_str,
                    "source_id": str(case_id),
                    "min_similarity": min_similarity,
                    "limit": limit,
                },
            )
            rows = result.fetchall()

            return [
                {
                    "id": str(row.id),
                    "case_id": row.case_id,
                    "title": row.title,
                    "summary": row.summary,
                    "case_type": row.case_type,
                    "scope_code": row.scope_code,
                    "severity": row.severity,
                    "status": row.status,
                    "similarity": float(row.similarity),
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Failed to find similar cases: {e}")
            return []

    async def health_check(self) -> dict[str, Any]:
        """
        Check if embedding service is available.

        Returns:
            Health status dictionary
        """
        try:
            # Test embedding generation
            test_embedding = await self.embed_text("Health check test")

            return {
                "status": "healthy" if test_embedding else "degraded",
                "ollama_host": self.ollama_host,
                "model": self.model,
                "dimension": self.dimension,
                "embedding_works": test_embedding is not None,
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "ollama_host": self.ollama_host,
                "model": self.model,
                "error": str(e),
            }


# Singleton instance
embedding_service = EmbeddingService()
