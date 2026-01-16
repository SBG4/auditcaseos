"""Service layer for AuditCaseOS API."""

from .analytics_service import AnalyticsService
from .audit_service import AuditService
from .cache_service import CacheService, get_cache_service, set_cache_service
from .case_service import CaseService
from .embedding_service import EmbeddingService
from .entity_service import EntityService
from .nextcloud_service import NextcloudService
from .notification_service import NotificationService
from .ollama_service import OllamaService
from .onlyoffice_service import OnlyOfficeService
from .paperless_service import PaperlessService
from .report_service import ReportService
from .scheduler_service import SchedulerService
from .search_service import SearchService
from .storage_service import StorageService
from .websocket_service import ConnectionManager
from .workflow_executor import WorkflowExecutor
from .workflow_service import WorkflowService

__all__ = [
    "AnalyticsService",
    "AuditService",
    "CacheService",
    "CaseService",
    "ConnectionManager",
    "EmbeddingService",
    "EntityService",
    "NextcloudService",
    "NotificationService",
    "OllamaService",
    "OnlyOfficeService",
    "PaperlessService",
    "ReportService",
    "SchedulerService",
    "SearchService",
    "StorageService",
    "WorkflowExecutor",
    "WorkflowService",
    "get_cache_service",
    "set_cache_service",
]
