"""AI router for AuditCaseOS API.

This module provides AI-powered endpoints including case summarization
using Ollama, similarity search using RAG, and embedding management.
"""

import logging
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.auth import get_current_user_required
from app.schemas.common import BaseSchema, Severity
from app.services.case_service import case_service
from app.services.embedding_service import embedding_service
from app.services.ollama_service import ollama_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


# =============================================================================
# Schemas
# =============================================================================


class CaseSummaryRequest(BaseSchema):
    """Request schema for case summarization."""

    include_findings: bool = Field(default=True, description="Include findings in summary")
    include_timeline: bool = Field(default=True, description="Include timeline in summary")
    include_evidence: bool = Field(default=False, description="Include evidence metadata in summary")
    max_length: int = Field(default=500, ge=100, le=2000, description="Maximum summary length in words")
    language: str = Field(default="en", description="Summary language code")


class CaseSummaryResponse(BaseSchema):
    """Response schema for case summarization."""

    case_id: str = Field(..., description="Case ID that was summarized")
    summary: str = Field(..., description="AI-generated summary")
    key_points: list[str] = Field(default_factory=list, description="Key points extracted")
    risk_assessment: str | None = Field(None, description="AI risk assessment")
    recommended_actions: list[str] = Field(default_factory=list, description="Recommended next steps")
    model_used: str = Field(..., description="Ollama model used for generation")
    generated_at: datetime = Field(..., description="Timestamp of generation")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="AI confidence score")


class SimilarCaseResult(BaseSchema):
    """Schema for a similar case result."""

    case_id: str = Field(..., description="Similar case ID")
    title: str = Field(..., description="Case title")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    matching_aspects: list[str] = Field(default_factory=list, description="Aspects that match")
    case_type: str = Field(..., description="Type of case")
    scope: str = Field(..., description="Case scope")
    severity: Severity = Field(..., description="Case severity")
    status: str = Field(..., description="Case status")


class SimilarCasesRequest(BaseSchema):
    """Request schema for finding similar cases."""

    limit: int = Field(default=5, ge=1, le=20, description="Maximum number of similar cases")
    min_similarity: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum similarity threshold")
    include_closed: bool = Field(default=True, description="Include closed cases in results")
    same_scope_only: bool = Field(default=False, description="Only return cases from same scope")


class SimilarCasesResponse(BaseSchema):
    """Response schema for similar cases search."""

    case_id: str = Field(..., description="Source case ID")
    similar_cases: list[SimilarCaseResult] = Field(default_factory=list, description="Similar cases found")
    total_found: int = Field(..., description="Total similar cases found")
    search_method: str = Field(..., description="Method used for similarity search")
    generated_at: datetime = Field(..., description="Timestamp of search")


class AIHealthResponse(BaseSchema):
    """Response schema for AI service health check."""

    ollama_available: bool = Field(..., description="Whether Ollama is available")
    ollama_models: list[str] = Field(default_factory=list, description="Available Ollama models")
    rag_available: bool = Field(..., description="Whether RAG service is available")
    embedding_model: str | None = Field(None, description="Embedding model for RAG")


class EmbedCaseRequest(BaseSchema):
    """Request schema for embedding a case."""

    include_evidence: bool = Field(default=True, description="Also embed all case evidence")


class EmbedCaseResponse(BaseSchema):
    """Response schema for case embedding."""

    case_id: str = Field(..., description="Case ID that was embedded")
    case_embedded: bool = Field(..., description="Whether case was successfully embedded")
    evidence_embedded: int = Field(default=0, description="Number of evidence items embedded")
    errors: list[str] = Field(default_factory=list, description="Any errors encountered")


class EmbeddingHealthResponse(BaseSchema):
    """Response schema for embedding service health."""

    status: str = Field(..., description="Service status")
    ollama_host: str = Field(..., description="Ollama host URL")
    model: str = Field(..., description="Embedding model")
    dimension: int = Field(..., description="Embedding dimension")
    embedding_works: bool = Field(default=False, description="Whether embedding generation works")


# =============================================================================
# Dependencies
# =============================================================================


def get_current_user_id() -> UUID:
    """
    Dependency to get current user ID.

    This is a placeholder for authentication.

    Returns:
        UUID: Current user's UUID
    """
    # TODO: Implement actual authentication
    return UUID("00000000-0000-0000-0000-000000000001")


# Type aliases for dependency injection
DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(get_current_user_required)]
CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]


# =============================================================================
# Ollama Integration
# =============================================================================


class OllamaClient:
    """
    Client for interacting with Ollama API.

    This is a placeholder implementation that should be replaced
    with actual Ollama integration.
    """

    def __init__(self, base_url: str = "http://localhost:11434"):
        """Initialize Ollama client."""
        self.base_url = base_url
        self.default_model = "llama2"

    async def is_available(self) -> bool:
        """Check if Ollama service is available."""
        # TODO: Implement actual health check
        # import httpx
        # try:
        #     async with httpx.AsyncClient() as client:
        #         response = await client.get(f"{self.base_url}/api/tags")
        #         return response.status_code == 200
        # except Exception:
        #     return False
        return False

    async def list_models(self) -> list[str]:
        """List available models."""
        # TODO: Implement actual model listing
        return []

    async def generate(self, prompt: str, model: str | None = None) -> str:
        """Generate text using Ollama."""
        # TODO: Implement actual generation
        # import httpx
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(
        #         f"{self.base_url}/api/generate",
        #         json={
        #             "model": model or self.default_model,
        #             "prompt": prompt,
        #             "stream": False,
        #         },
        #     )
        #     return response.json()["response"]
        raise NotImplementedError("Ollama integration not configured")


# Global Ollama client instance
ollama_client = OllamaClient()


# =============================================================================
# RAG Integration
# =============================================================================


class RAGService:
    """
    Service for Retrieval-Augmented Generation.

    This is a placeholder implementation for vector similarity search
    to find similar cases based on embeddings.
    """

    def __init__(self):
        """Initialize RAG service."""
        self.embedding_model = "all-MiniLM-L6-v2"
        self.vector_store = None  # Placeholder for vector database

    async def is_available(self) -> bool:
        """Check if RAG service is available."""
        # TODO: Implement actual availability check
        return False

    async def get_case_embedding(self, case_id: str) -> list[float] | None:
        """Get embedding vector for a case."""
        # TODO: Implement actual embedding retrieval
        return None

    async def find_similar(
        self,
        case_id: str,
        limit: int = 5,
        min_similarity: float = 0.7,
    ) -> list[dict]:
        """Find similar cases using vector similarity."""
        # TODO: Implement actual similarity search
        # 1. Get embedding for source case
        # 2. Search vector store for similar embeddings
        # 3. Return matching case IDs with similarity scores
        return []


# Global RAG service instance
rag_service = RAGService()


# =============================================================================
# Helper Functions
# =============================================================================


async def build_case_context(case_id: str, include_findings: bool, include_timeline: bool) -> str:
    """
    Build context string from case data for AI summarization.

    Args:
        case_id: Case ID to build context for
        include_findings: Whether to include findings
        include_timeline: Whether to include timeline events

    Returns:
        str: Formatted context string
    """
    # TODO: Implement actual context building from database
    # This would fetch case data, findings, timeline, etc.
    return f"Case {case_id} context placeholder"


def build_summary_prompt(context: str, max_length: int, language: str) -> str:
    """
    Build prompt for case summarization.

    Args:
        context: Case context string
        max_length: Maximum summary length
        language: Target language

    Returns:
        str: Formatted prompt for Ollama
    """
    return f"""You are an audit case analyst. Summarize the following audit case information.
Provide a concise summary (max {max_length} words) in {language}.
Include key findings, risk assessment, and recommended actions.

Case Information:
{context}

Please provide:
1. A brief summary of the case
2. Key points (bullet points)
3. Risk assessment (low/medium/high/critical)
4. Recommended next steps

Summary:"""


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/summarize/{case_id}",
    response_model=CaseSummaryResponse,
    summary="Generate AI summary of case",
    description="Use Ollama to generate an AI-powered summary of an audit case.",
)
async def summarize_case(
    db: DbSession,
    current_user: CurrentUser,
    case_id: str = Path(..., description="Case ID (SCOPE-TYPE-SEQ format)"),
    request: CaseSummaryRequest | None = None,
) -> CaseSummaryResponse:
    """
    Generate an AI-powered summary of an audit case using Ollama.

    This endpoint uses a local Ollama instance to analyze case data
    and generate a comprehensive summary including:

    - **Summary**: Concise overview of the case
    - **Key Points**: Important facts and observations
    - **Risk Assessment**: AI-evaluated risk level
    - **Recommended Actions**: Suggested next steps

    Request Options:
    - **include_findings**: Include case findings in analysis (default: true)
    - **include_timeline**: Include timeline events in analysis (default: true)
    - **include_evidence**: Include evidence metadata in analysis (default: false)

    Requires Ollama to be running with llama3.2 model.

    Returns:
        CaseSummaryResponse: AI-generated case summary

    Raises:
        HTTPException: 404 if case not found
        HTTPException: 503 if Ollama service unavailable
    """
    if request is None:
        request = CaseSummaryRequest()

    # Check if Ollama is available
    if not await ollama_service.health_check():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ollama service is not available. Please ensure Ollama is running with llama3.2 model.",
        )

    try:
        # Get case data from database
        case_data = await case_service.get_case(db, case_id)
        if not case_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case '{case_id}' not found",
            )

        # Get findings if requested
        if request.include_findings:
            findings = await case_service.get_case_findings(db, case_data["id"])
            case_data["findings"] = findings

        # Get timeline if requested
        if request.include_timeline:
            timeline = await case_service.get_case_timeline(db, case_data["id"])
            case_data["timeline_events"] = timeline

        # Generate structured summary using Ollama
        result = await ollama_service.summarize_case_structured(
            case_data=case_data,
            include_findings=request.include_findings,
            include_timeline=request.include_timeline,
        )

        return CaseSummaryResponse(
            case_id=case_data["case_id"],
            summary=result.get("summary", "Unable to generate summary"),
            key_points=result.get("key_points", []),
            risk_assessment=result.get("risk_assessment"),
            recommended_actions=result.get("recommended_actions", []),
            model_used=result.get("model_used", ollama_service.model),
            generated_at=datetime.utcnow(),
            confidence_score=result.get("confidence_score", 0.5),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating summary for case {case_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating summary: {e!s}",
        )


@router.post(
    "/similar/{case_id}",
    response_model=SimilarCasesResponse,
    summary="Find similar cases",
    description="Use pgvector embeddings to find cases similar to the specified case.",
)
async def find_similar_cases(
    db: DbSession,
    current_user: CurrentUser,
    case_id: str = Path(..., description="Case ID (SCOPE-TYPE-SEQ format)"),
    request: SimilarCasesRequest | None = None,
) -> SimilarCasesResponse:
    """
    Find cases similar to the specified case using vector embeddings.

    This endpoint uses pgvector cosine similarity to find audit cases
    that are similar to the specified case. This is useful for:

    - Finding precedents for similar issues
    - Identifying patterns across cases
    - Learning from past resolutions

    The similarity search is based on embeddings that capture:
    - Case title, summary, description
    - Findings and their details
    - Case metadata (type, scope, severity)

    Request Options:
    - **limit**: Maximum number of similar cases to return (default: 5)
    - **min_similarity**: Minimum similarity threshold 0-1 (default: 0.7)
    - **include_closed**: Include closed cases in results (default: true)
    - **same_scope_only**: Only return cases from same scope (default: false)

    Note: The case must have embeddings generated first via POST /ai/embed/case/{case_id}

    Returns:
        SimilarCasesResponse: List of similar cases with similarity scores

    Raises:
        HTTPException: 404 if case not found
        HTTPException: 500 if search fails
    """
    if request is None:
        request = SimilarCasesRequest()

    try:
        # Verify case exists and get data
        case_data = await case_service.get_case(db, case_id)
        if not case_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case '{case_id}' not found",
            )

        case_uuid = case_data["id"]
        source_scope = case_data.get("scope_code")

        # Find similar cases using embedding service
        similar = await embedding_service.find_similar_cases(
            db=db,
            case_id=case_uuid,
            limit=request.limit,
            min_similarity=request.min_similarity,
            include_closed=request.include_closed,
        )

        # Apply same_scope_only filter if requested
        if request.same_scope_only and source_scope:
            similar = [s for s in similar if s.get("scope_code") == source_scope]

        # Convert to response format
        similar_cases = [
            SimilarCaseResult(
                case_id=item["case_id"],
                title=item["title"],
                similarity_score=item["similarity"],
                matching_aspects=[],
                case_type=item["case_type"],
                scope=item["scope_code"],
                severity=item["severity"],
                status=item["status"],
            )
            for item in similar
        ]

        return SimilarCasesResponse(
            case_id=case_data["case_id"],
            similar_cases=similar_cases,
            total_found=len(similar_cases),
            search_method="pgvector_cosine",
            generated_at=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding similar cases for {case_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error finding similar cases: {e!s}",
        )


@router.get(
    "/health",
    response_model=AIHealthResponse,
    summary="Check AI services health",
    description="Check the availability of AI services (Ollama and RAG/Embeddings).",
)
async def check_ai_health() -> AIHealthResponse:
    """
    Check the health and availability of AI services.

    Returns the status of:
    - **Ollama**: Local LLM service for text generation
    - **RAG**: Vector similarity search service (via embeddings)

    This endpoint is useful for:
    - Monitoring AI service availability
    - Debugging configuration issues
    - Checking available models

    Returns:
        AIHealthResponse: Status of AI services
    """
    ollama_available = await ollama_service.health_check()
    ollama_models = await ollama_service.list_models() if ollama_available else []

    # Check embedding service for RAG
    embedding_health = await embedding_service.health_check()
    rag_available = embedding_health.get("embedding_works", False)

    return AIHealthResponse(
        ollama_available=ollama_available,
        ollama_models=ollama_models,
        rag_available=rag_available,
        embedding_model=embedding_health.get("model") if rag_available else None,
    )


# =============================================================================
# Embedding Endpoints
# =============================================================================


@router.post(
    "/embed/case/{case_id}",
    response_model=EmbedCaseResponse,
    summary="Generate embeddings for a case",
    description="Generate and store vector embeddings for a case and its evidence.",
)
async def embed_case(
    db: DbSession,
    current_user: CurrentUser,
    case_id: str = Path(..., description="Case ID (SCOPE-TYPE-SEQ or UUID)"),
    request: EmbedCaseRequest | None = None,
) -> EmbedCaseResponse:
    """
    Generate vector embeddings for a case.

    This creates embeddings that enable similarity search to find related cases.
    Embeddings are generated using Ollama's nomic-embed-text model.

    Options:
    - **include_evidence**: Also generate embeddings for all evidence files (default: true)

    The embedding captures:
    - Case title, summary, description
    - Findings and their details
    - Evidence extracted text (if OCR available)
    """
    if request is None:
        request = EmbedCaseRequest()

    try:
        # Get case to verify it exists and get UUID
        case_data = await case_service.get_case(db, case_id)
        if not case_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case '{case_id}' not found",
            )

        case_uuid = case_data["id"]

        if request.include_evidence:
            # Batch embed case and all evidence
            result = await embedding_service.batch_embed_case(db, case_uuid)
        else:
            # Embed only the case
            embed_result = await embedding_service.embed_case(db, case_uuid)
            result = {
                "case_embedded": embed_result is not None,
                "evidence_embedded": 0,
                "errors": [] if embed_result else ["Failed to generate case embedding"],
            }

        return EmbedCaseResponse(
            case_id=case_data["case_id"],
            case_embedded=result["case_embedded"],
            evidence_embedded=result.get("evidence_embedded", 0),
            errors=result.get("errors", []),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to embed case {case_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate embeddings: {e!s}",
        )


@router.get(
    "/similar-cases/{case_id}",
    response_model=SimilarCasesResponse,
    summary="Find similar cases using embeddings",
    description="Find cases similar to the given case using vector similarity search.",
)
async def find_similar_cases_real(
    db: DbSession,
    current_user: CurrentUser,
    case_id: str = Path(..., description="Case ID"),
    limit: int = Query(5, ge=1, le=20, description="Maximum results"),
    min_similarity: float = Query(0.5, ge=0.0, le=1.0, description="Minimum similarity"),
    include_closed: bool = Query(True, description="Include closed cases"),
    same_scope_only: bool = Query(False, description="Only return cases from same scope"),
) -> SimilarCasesResponse:
    """
    Find cases similar to the given case using vector similarity.

    This uses pgvector cosine similarity to find cases with similar
    content based on their embeddings. The case must have been embedded
    first using POST /ai/embed/case/{case_id}.

    Query Parameters:
    - **limit**: Maximum number of results (default: 5)
    - **min_similarity**: Minimum similarity score 0-1 (default: 0.5)
    - **include_closed**: Include closed/archived cases (default: true)
    - **same_scope_only**: Only return cases from same scope/department (default: false)
    """
    try:
        # Get case UUID
        case_data = await case_service.get_case(db, case_id)
        if not case_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case '{case_id}' not found",
            )

        case_uuid = case_data["id"]
        source_scope = case_data.get("scope_code")

        # Find similar cases
        similar = await embedding_service.find_similar_cases(
            db=db,
            case_id=case_uuid,
            limit=limit,
            min_similarity=min_similarity,
            include_closed=include_closed,
        )

        # Apply same_scope_only filter if requested
        if same_scope_only and source_scope:
            similar = [s for s in similar if s.get("scope_code") == source_scope]

        # Convert to response format
        similar_cases = [
            SimilarCaseResult(
                case_id=item["case_id"],
                title=item["title"],
                similarity_score=item["similarity"],
                matching_aspects=[],
                case_type=item["case_type"],
                scope=item["scope_code"],
                severity=item["severity"],
                status=item["status"],
            )
            for item in similar
        ]

        return SimilarCasesResponse(
            case_id=case_data["case_id"],
            similar_cases=similar_cases,
            total_found=len(similar_cases),
            search_method="pgvector_cosine",
            generated_at=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to find similar cases: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search similar cases: {e!s}",
        )


@router.get(
    "/embeddings/health",
    response_model=EmbeddingHealthResponse,
    summary="Check embedding service health",
    description="Check if the embedding service is available and working.",
)
async def check_embedding_health() -> EmbeddingHealthResponse:
    """
    Check the health of the embedding service.

    Tests that:
    - Ollama is accessible
    - The embedding model is available
    - Embedding generation works
    """
    health = await embedding_service.health_check()

    return EmbeddingHealthResponse(
        status=health.get("status", "unknown"),
        ollama_host=health.get("ollama_host", ""),
        model=health.get("model", ""),
        dimension=health.get("dimension", 0),
        embedding_works=health.get("embedding_works", False),
    )
