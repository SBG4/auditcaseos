# Feature 3.13: Advanced Search Implementation Plan

## Overview
Implement full-text and semantic search across all content in AuditCaseOS.

**Status**: Ready for implementation
**Estimated Files**: 6 new, 6 modified

---

## Architecture Decision

### Hybrid Search Approach (Recommended)
- **Keyword Search**: ILIKE pattern matching (existing pattern in case_service.py)
- **Semantic Search**: pgvector cosine similarity (existing embedding_service.py)
- **Hybrid Ranking**: 40% keyword + 60% semantic weighted scoring

**Why ILIKE over tsvector**: No migration required, existing pattern works, can add tsvector later if performance needs it.

---

## Implementation Steps

### Step 1: Backend Schemas
**File**: `api/app/schemas/search.py` (NEW)

Create:
- `SearchEntityType` enum (case, evidence, finding, entity, timeline, all)
- `SearchMode` enum (keyword, semantic, hybrid)
- `SearchRequest` schema with filters (query, entity_types, scope, status, severity, dates)
- `SearchResultItem` schema (id, entity_type, title, snippet, scores, metadata)
- `SearchResponse` schema (paginated with entity_type_counts, search_time_ms)

### Step 2: Backend Service
**File**: `api/app/services/search_service.py` (NEW)

Create `SearchService` class with:
- `search()` - main hybrid search method
- `_keyword_search()` - ILIKE across all entity tables
- `_semantic_search()` - pgvector similarity using existing embedding_service
- `_merge_results()` - deduplicate and combine scores
- Singleton: `search_service = SearchService()`

Key SQL patterns:
```sql
-- Keyword (ILIKE)
WHERE title ILIKE :pattern OR summary ILIKE :pattern

-- Semantic (pgvector)
SELECT 1 - (embedding <=> CAST(:query_vec AS vector)) as similarity
FROM embeddings WHERE similarity >= :min_similarity
```

### Step 3: Backend Router
**File**: `api/app/routers/search.py` (NEW)

Endpoints:
- `GET /api/v1/search` - main search with filters
- `GET /api/v1/search/suggest` - autocomplete suggestions

Query params: q, entity_types, mode, scope_codes, case_types, statuses, severities, min_similarity, page, page_size

### Step 4: Register Router
**Files**:
- `api/app/main.py` (MODIFY)
- `api/app/routers/__init__.py` (MODIFY)
- `api/app/services/__init__.py` (MODIFY)

### Step 5: Frontend Types
**File**: `frontend/src/types/index.ts` (MODIFY)

Add:
- `SearchEntityType`, `SearchMode` types
- `SearchResultItem`, `SearchResponse` interfaces
- `SearchSuggestion` interface

### Step 6: Frontend API Service
**File**: `frontend/src/services/api.ts` (MODIFY)

Add `searchApi` object with:
- `search(params)` - main search
- `suggest(q, limit)` - autocomplete

### Step 7: useDebounce Hook
**File**: `frontend/src/hooks/useDebounce.ts` (NEW)

Simple debounce hook for search input (300ms delay).

### Step 8: SearchBar Component
**File**: `frontend/src/components/search/SearchBar.tsx` (NEW)

Features:
- Input with MagnifyingGlassIcon
- Cmd+K keyboard shortcut
- Debounced suggestions dropdown
- Arrow key navigation
- Navigate to /search on submit

### Step 9: Search Results Page
**File**: `frontend/src/pages/Search.tsx` (NEW)

Features:
- URL params sync (q, mode, type)
- Entity type filter pills with counts
- Result cards by entity type (icon, color coded)
- Score indicators (keyword %, semantic %)
- Pagination
- Loading/empty/error states

### Step 10: Integrate into Layout
**Files**:
- `frontend/src/components/layout/Header.tsx` (MODIFY) - Add SearchBar
- `frontend/src/App.tsx` (MODIFY) - Add /search route

### Step 11: Update PROJECT_SPEC.xml
Mark Feature 3.13 as COMPLETED, add changelog entry, bump version to 0.5.4

### Step 12: Git Commit & Push
Commit all changes with descriptive message.

---

## Files Summary

### New Files (6)
1. `api/app/schemas/search.py`
2. `api/app/services/search_service.py`
3. `api/app/routers/search.py`
4. `frontend/src/hooks/useDebounce.ts`
5. `frontend/src/components/search/SearchBar.tsx`
6. `frontend/src/pages/Search.tsx`

### Modified Files (6)
1. `api/app/main.py` - register router
2. `api/app/routers/__init__.py` - export router
3. `api/app/services/__init__.py` - export service
4. `frontend/src/types/index.ts` - add types
5. `frontend/src/services/api.ts` - add searchApi
6. `frontend/src/components/layout/Header.tsx` - add SearchBar
7. `frontend/src/App.tsx` - add route

---

## Critical Reference Files

| File | Purpose |
|------|---------|
| `api/app/services/embedding_service.py` | Semantic search patterns (lines 473-549) |
| `api/app/services/case_service.py` | ILIKE search pattern (lines 226-229) |
| `api/app/schemas/common.py` | Base schemas (PaginatedResponse) |
| `frontend/src/pages/CaseList.tsx` | Search UI pattern model |
| `configs/postgres/init.sql` | Database schema reference |

---

## API Endpoint Design

```
GET /api/v1/search
  ?q=USB exfiltration          # Required, 2-500 chars
  &entity_types=case,evidence  # Optional, default: all
  &mode=hybrid                 # keyword|semantic|hybrid
  &scope_codes=FIN,IT          # Optional filter
  &statuses=OPEN,IN_PROGRESS   # Optional filter
  &severities=HIGH,CRITICAL    # Optional filter
  &min_similarity=0.5          # For semantic (0-1)
  &page=1&page_size=20         # Pagination

Response:
{
  "items": [...],
  "total": 42,
  "entity_type_counts": {"case": 10, "evidence": 20, ...},
  "search_time_ms": 123.45,
  "query": "USB exfiltration",
  "mode": "hybrid"
}
```

---

## Verification Checklist

- [ ] Backend search returns results for keyword queries
- [ ] Backend search returns results for semantic queries
- [ ] Hybrid mode combines and deduplicates results
- [ ] Frontend SearchBar shows suggestions
- [ ] Cmd+K opens search
- [ ] /search page displays results with filters
- [ ] Pagination works
- [ ] Entity type filtering works
- [ ] Links navigate to correct case/entity
