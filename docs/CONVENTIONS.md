# AuditCaseOS Development Conventions

Best practices compiled from official documentation sources.

## Sources
- FastAPI (fastapi.tiangolo.com)
- Pydantic (docs.pydantic.dev)
- SQLAlchemy (docs.sqlalchemy.org)
- React (react.dev)
- TypeScript (typescriptlang.org)
- Docker (docs.docker.com)
- OWASP (owasp.org)
- OpenTelemetry (opentelemetry.io)
- PostgreSQL (postgresql.org)
- RFC Standards (rfc-editor.org)

---

## Python/FastAPI Backend

### Async Patterns
| Rule | Description |
|------|-------------|
| PY-ASYNC-1 | Use `async def` for I/O-bound operations (database, API calls, file I/O) |
| PY-ASYNC-2 | Use regular `def` for CPU-bound operations (runs in threadpool automatically) |
| PY-ASYNC-3 | Use regular `def` when libraries don't support await (safe default) |
| PY-ASYNC-4 | Use `lifespan` parameter instead of deprecated `on_startup`/`on_shutdown` |
| PY-ASYNC-5 | Use `BackgroundTasks` for simple async; Celery for heavy computation |

### Dependency Injection
| Rule | Description |
|------|-------------|
| PY-DI-1 | Use Annotated syntax: `CommonsDep = Annotated[dict, Depends(common_parameters)]` |
| PY-DI-2 | Use yield dependencies for resource management (DB sessions, connections) |
| PY-DI-3 | Use `app.dependency_overrides` for testing |
| PY-DI-4 | Dependencies are cached per-request by default |

### Pydantic v2 Models
| Rule | Description |
|------|-------------|
| PY-PYDANTIC-1 | Use `ConfigDict` instead of `class Config`: `model_config = ConfigDict(...)` |
| PY-PYDANTIC-2 | Use `frozen=True` for immutable models |
| PY-PYDANTIC-3 | Use `extra="forbid"` to reject unknown fields |
| PY-PYDANTIC-4 | Use `@field_validator` (not deprecated `@validator`) for single field validation |
| PY-PYDANTIC-5 | Use `@model_validator` for cross-field validation |
| PY-PYDANTIC-6 | Use `mode="before"` or `mode="after"` for validation timing |

### SQLAlchemy 2.0 Async
| Rule | Description |
|------|-------------|
| PY-DB-1 | Use `create_async_engine()` and `async_sessionmaker` for async operations |
| PY-DB-2 | Set `expire_on_commit=False` for async sessions (REQUIRED) |
| PY-DB-3 | Use `selectinload()` for one-to-many/many-to-many relationships |
| PY-DB-4 | Use `joinedload()` for many-to-one relationships |
| PY-DB-5 | NEVER use lazy loading in async - use eager loading always |
| PY-DB-6 | One `AsyncSession` per task - critical for asyncio concurrency |

### Error Handling
| Rule | Description |
|------|-------------|
| PY-ERR-1 | Use `HTTPException` with status codes from `fastapi.status` |
| PY-ERR-2 | Pass JSON-serializable detail (can be dict, list, not just strings) |
| PY-ERR-3 | Override `RequestValidationError` handler for custom validation responses |
| PY-ERR-4 | Register handler for Starlette's `HTTPException` to catch all HTTP errors |

### Security
| Rule | Description |
|------|-------------|
| PY-SEC-1 | CORS: Explicitly list allowed origins (avoid `["*"]` in production) |
| PY-SEC-2 | Use `OAuth2PasswordBearer` for standard OAuth2 password flow |
| PY-SEC-3 | Use bcrypt or passlib for password hashing |
| PY-SEC-4 | JWT is signed, not encrypted - don't store sensitive data in payload |
| PY-SEC-5 | Use Pydantic models with `Field()` constraints for input validation |

---

## React/TypeScript Frontend

### React Hooks Rules
| Rule | Description |
|------|-------------|
| REACT-HOOK-1 | Only call Hooks at the top level - never in loops, conditions, or nested functions |
| REACT-HOOK-2 | Custom hooks must start with "use" followed by capital letter |
| REACT-HOOK-3 | `useEffect` is an escape hatch - avoid for data fetching, use libraries instead |
| REACT-HOOK-4 | Use `useReducer` + Context for complex state management |

### React 19 Features
| Rule | Description |
|------|-------------|
| REACT-19-1 | Use `use` Hook for reading resources in render (can be in conditionals) |
| REACT-19-2 | Use `useOptimistic` for optimistic UI updates |
| REACT-19-3 | Use `useActionState` for form submissions and mutations |
| REACT-19-4 | `ref` is now a prop - `forwardRef` no longer required (deprecated) |
| REACT-19-5 | Use `startTransition` for non-urgent updates to prevent UI jank |

### Performance
| Rule | Description |
|------|-------------|
| REACT-PERF-1 | React Compiler handles memoization automatically - trust it first |
| REACT-PERF-2 | Use `memo()` only when profiling shows expensive re-renders with same props |
| REACT-PERF-3 | Use `useMemo()` for expensive calculations with rarely-changing dependencies |
| REACT-PERF-4 | Use `useCallback()` only when passing functions to memo components |
| REACT-PERF-5 | Most performance problems come from Effect chains - remove unnecessary dependencies |

### TypeScript Strict Mode
| Rule | Description |
|------|-------------|
| TS-STRICT-1 | Enable `strict: true` in tsconfig.json (enables all strict checks) |
| TS-STRICT-2 | NEVER use `any` - use `unknown` when type is truly unknown |
| TS-STRICT-3 | Use `object` not `Object` for non-primitive types |
| TS-STRICT-4 | Generic type parameters must be used meaningfully |
| TS-STRICT-5 | Enable `exactOptionalPropertyTypes` for stricter optional handling |

### State Management
| Rule | Description |
|------|-------------|
| REACT-STATE-1 | Group related state together - if always updated together, merge into one |
| REACT-STATE-2 | Avoid redundant state - calculate from props/existing state during render |
| REACT-STATE-3 | Avoid deeply nested state - prefer flat structures |
| REACT-STATE-4 | Separate contexts for state and dispatch when using Context + Reducer |

### TailwindCSS
| Rule | Description |
|------|-------------|
| TW-1 | Use framework components for reusable styles - prefer over `@apply` |
| TW-2 | Use `@apply` sparingly - only for small elements where partials feel heavy |
| TW-3 | Don't over-extract - ensure you're using something more than once |
| TW-4 | Use container queries for portable, reusable components |
| TW-5 | Use `dark:` variant with prefers-color-scheme or manual toggle |

---

## Docker/DevOps

### Dockerfile Optimization
| Rule | Description |
|------|-------------|
| DOCKER-BUILD-1 | Use multi-stage builds - separate build and runtime stages |
| DOCKER-BUILD-2 | Order layers by change frequency - rarely-changing first |
| DOCKER-BUILD-3 | Copy dependency files first, install, then copy source |
| DOCKER-BUILD-4 | Use `--mount=type=cache` for persistent build caches |
| DOCKER-BUILD-5 | Use `COPY --link` for better layer caching |

### Container Security (OWASP)
| Rule | Severity | Description |
|------|----------|-------------|
| DOCKER-SEC-1 | CRITICAL | Run as non-root user - use USER directive with explicit UID/GID |
| DOCKER-SEC-2 | CRITICAL | Use read-only filesystem - prevents container breakout |
| DOCKER-SEC-3 | CRITICAL | Never mount Docker socket (`/var/run/docker.sock`) |
| DOCKER-SEC-4 | HIGH | Drop all capabilities, add only needed |
| DOCKER-SEC-5 | HIGH | Enable no-new-privileges: `security_opt: - no-new-privileges:true` |
| DOCKER-SEC-6 | MEDIUM | Use tmpfs for /tmp with noexec,nosuid flags |
| DOCKER-SEC-7 | HIGH | Never embed secrets in images - use Docker secrets or env files |

### Health Checks
| Rule | Description |
|------|-------------|
| DOCKER-HEALTH-1 | Always define healthcheck with test, interval, timeout, retries, start_period |
| DOCKER-HEALTH-2 | Use `condition: service_healthy` in depends_on for startup order |
| DOCKER-HEALTH-3 | PostgreSQL: `pg_isready -U $USER -d $DB` |
| DOCKER-HEALTH-4 | Redis: `redis-cli ping` |
| DOCKER-HEALTH-5 | HTTP: `curl -f http://localhost/health \|\| exit 1` |

---

## API Design

### HTTP Methods (RFC 9110)
| Rule | Description |
|------|-------------|
| API-HTTP-1 | GET, HEAD, OPTIONS are safe and idempotent - use for reads |
| API-HTTP-2 | PUT, DELETE are idempotent but not safe - use for replacements and deletions |
| API-HTTP-3 | POST is NOT idempotent - repeated requests may create multiple resources |
| API-HTTP-4 | PATCH is for partial updates - not guaranteed idempotent |

### Error Responses (RFC 9457)
| Rule | Description |
|------|-------------|
| API-ERR-1 | Use `Content-Type: application/problem+json` |
| API-ERR-2 | Include: type (URI), title, status, detail, instance |
| API-ERR-3 | Extend with custom fields for problem-specific data |
| API-ERR-4 | 400 for structural problems; 422 for validation/business rule errors |
| API-ERR-5 | 401 for unauthenticated; 403 for unauthorized |

### Pagination (JSON:API)
| Rule | Description |
|------|-------------|
| API-PAGE-1 | Use page query parameter family: `page[number]`, `page[size]` |
| API-PAGE-2 | Include pagination links: self, first, prev, next, last |
| API-PAGE-3 | Put total count in meta: totalPages, totalRecords |
| API-PAGE-4 | self link must contain all query parameters used |

---

## Database (PostgreSQL)

### Indexing
| Rule | Description |
|------|-------------|
| DB-IDX-1 | B-tree is default - use for equality and range queries, ORDER BY |
| DB-IDX-2 | GIN for full-text search, arrays, JSONB |
| DB-IDX-3 | BRIN for very large tables with natural ordering (time-series) |
| DB-IDX-4 | Use partial indexes for relevant rows: `WHERE status = 'active'` |
| DB-IDX-5 | Use covering indexes (INCLUDE) for index-only scans |
| DB-IDX-6 | Multicolumn index column order matters for query optimization |

### Connection Pooling
| Rule | Description |
|------|-------------|
| DB-POOL-1 | Use PgBouncer with transaction pooling for web applications |
| DB-POOL-2 | Set `server_reset_query = DISCARD ALL` |
| DB-POOL-3 | Remove application-level pooling when using PgBouncer |
| DB-POOL-4 | Run multiple PgBouncer instances on multi-core systems |

### Query Optimization
| Rule | Description |
|------|-------------|
| DB-OPT-1 | Use `EXPLAIN ANALYZE` to identify slow queries |
| DB-OPT-2 | Keep statistics current: `ANALYZE table_name` |
| DB-OPT-3 | Increase `work_mem` if EXPLAIN shows "external merge Disk" |
| DB-OPT-4 | Lower `random_page_cost` for SSDs (1.1 instead of default 4.0) |
| DB-OPT-5 | Set `effective_cache_size` to expected available memory cache |

---

## Testing Requirements

| Rule | Severity | Description |
|------|----------|-------------|
| TEST-1 | CRITICAL | Test BOTH API responses AND actual browser functionality |
| TEST-2 | HIGH | For features with external URLs, verify browser accessibility |
| TEST-3 | HIGH | Test file upload with files >1MB, >10MB, and >50MB |
| TEST-4 | MEDIUM | After URL config changes, restart containers and clear browser cache |
