"""
Prometheus metrics configuration for AuditCaseOS API.

Uses prometheus-fastapi-instrumentator for automatic metrics collection.
Source: https://github.com/trallnag/prometheus-fastapi-instrumentator

Metrics exposed at /metrics endpoint:
- HTTP request count by method, path, status
- HTTP request latency histogram
- HTTP requests in progress
- Custom business metrics

Integration with Grafana:
- Import dashboard ID 14282 for FastAPI metrics
"""

from prometheus_fastapi_instrumentator import Instrumentator, metrics
from prometheus_fastapi_instrumentator.metrics import Info

from app.config import get_settings


def setup_prometheus(app) -> Instrumentator:
    """
    Configure Prometheus metrics for the FastAPI application.

    Args:
        app: FastAPI application instance

    Returns:
        Instrumentator: Configured Prometheus instrumentator

    Metrics collected:
    - http_requests_total: Counter of HTTP requests
    - http_request_duration_seconds: Histogram of request latency
    - http_requests_in_progress: Gauge of in-progress requests
    - http_request_size_bytes: Histogram of request body sizes
    - http_response_size_bytes: Histogram of response body sizes

    Source: https://prometheus.io/docs/practices/naming/
    """
    settings = get_settings()

    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=False,  # Don't require env var, control via is_production
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/health", "/metrics"],
        inprogress_name="http_requests_inprogress",
        inprogress_labels=True,
    )

    # Add default metrics
    instrumentator.add(
        metrics.default(
            metric_namespace="auditcaseos",
            metric_subsystem="api",
            latency_lowr_buckets=[0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0],
        )
    )

    # Add request size metric
    instrumentator.add(
        metrics.request_size(
            metric_namespace="auditcaseos",
            metric_subsystem="api",
        )
    )

    # Add response size metric
    instrumentator.add(
        metrics.response_size(
            metric_namespace="auditcaseos",
            metric_subsystem="api",
        )
    )

    # Add custom business metrics
    instrumentator.add(cases_metrics())
    instrumentator.add(auth_metrics())

    # Instrument the app
    instrumentator.instrument(app)

    # Expose /metrics endpoint (only in non-production or with explicit flag)
    if not settings.is_production or settings.debug:
        instrumentator.expose(app, endpoint="/metrics", include_in_schema=False)

    return instrumentator


def cases_metrics() -> metrics.Info:
    """
    Custom metrics for case operations.

    Tracks:
    - Case creation events
    - Case status changes
    - Evidence uploads
    """
    from prometheus_client import Counter

    # These Counters register with Prometheus on creation (used by route handlers)
    Counter(
        "auditcaseos_cases_created_total",
        "Total number of cases created",
        ["case_type", "scope"],
    )

    Counter(
        "auditcaseos_evidence_uploaded_total",
        "Total evidence files uploaded",
        ["file_type"],
    )

    def instrumentation(info: Info) -> None:
        # This is called on each request
        # Custom metrics would be incremented in the actual route handlers
        pass

    return instrumentation


def auth_metrics() -> metrics.Info:
    """
    Custom metrics for authentication operations.

    Tracks:
    - Login attempts (success/failure)
    - Token generation
    - Password changes
    """
    from prometheus_client import Counter

    # This Counter registers with Prometheus on creation (used by auth router)
    Counter(
        "auditcaseos_login_attempts_total",
        "Total login attempts",
        ["status"],  # success, failure
    )

    def instrumentation(info: Info) -> None:
        # Metrics incremented in auth router
        pass

    return instrumentation


# Expose counters for use in routers
def get_cases_created_counter():
    """Get the cases created counter for incrementing in routes."""
    from prometheus_client import REGISTRY, Counter

    try:
        return REGISTRY._names_to_collectors.get("auditcaseos_cases_created_total")
    except Exception:
        return Counter(
            "auditcaseos_cases_created_total",
            "Total number of cases created",
            ["case_type", "scope"],
        )


def get_login_attempts_counter():
    """Get the login attempts counter for incrementing in routes."""
    from prometheus_client import REGISTRY, Counter

    try:
        return REGISTRY._names_to_collectors.get("auditcaseos_login_attempts_total")
    except Exception:
        return Counter(
            "auditcaseos_login_attempts_total",
            "Total login attempts",
            ["status"],
        )
