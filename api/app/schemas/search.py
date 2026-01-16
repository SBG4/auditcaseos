"""Search schemas for AuditCaseOS API.

Defines request and response schemas for the advanced search feature
which combines full-text (ILIKE) and semantic (pgvector) search.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import Field

from .common import BaseSchema, PaginatedResponse, Severity, CaseStatus


class SearchEntityType(str, Enum):
    """Entity types that can be searched."""

    CASE = "case"
    EVIDENCE = "evidence"
    FINDING = "finding"
    ENTITY = "entity"
    TIMELINE = "timeline"
    ALL = "all"


class SearchMode(str, Enum):
    """Search mode."""

    KEYWORD = "keyword"  # ILIKE pattern matching
    SEMANTIC = "semantic"  # Vector similarity
    HYBRID = "hybrid"  # Combined (default)


class SearchResultItem(BaseSchema):
    """Individual search result."""

    id: UUID = Field(..., description="Entity UUID")
    entity_type: SearchEntityType = Field(..., description="Type of entity")

    # Common fields
    title: str = Field(..., description="Result title")
    snippet: str = Field(default="", description="Text snippet with match context")

    # Relevance scores
    keyword_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Keyword match score (0-1)"
    )
    semantic_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Semantic similarity score (0-1)"
    )
    combined_score: float = Field(
        ..., ge=0.0, le=1.0, description="Weighted combined score"
    )

    # Context - related case info
    case_id: str | None = Field(default=None, description="Related case ID string")
    case_uuid: UUID | None = Field(default=None, description="Related case UUID")

    # Entity-specific metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional entity-specific data"
    )

    created_at: datetime = Field(..., description="Entity creation timestamp")


class SearchResponse(PaginatedResponse):
    """Paginated search results response."""

    items: list[SearchResultItem] = Field(
        default_factory=list, description="Search results"
    )
    query: str = Field(..., description="Original search query")
    mode: SearchMode = Field(..., description="Search mode used")
    entity_type_counts: dict[str, int] = Field(
        default_factory=dict, description="Count of results by entity type"
    )
    search_time_ms: float = Field(..., description="Search execution time in ms")


class SearchSuggestion(BaseSchema):
    """Search autocomplete suggestion."""

    type: str = Field(..., description="Suggestion type (case_id, title, entity)")
    value: str = Field(..., description="Suggestion value")
    entity_type: str | None = Field(
        default=None, description="Entity type for entity suggestions"
    )


class SearchSuggestResponse(BaseSchema):
    """Search suggestions response."""

    suggestions: list[SearchSuggestion] = Field(
        default_factory=list, description="List of suggestions"
    )
