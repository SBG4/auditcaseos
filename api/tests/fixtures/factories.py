"""
Test data factories for AuditCaseOS.

Provides factory functions to create test data with sensible defaults
while allowing customization for specific test scenarios.

Pattern: Factory Functions (simpler than factory_boy for our needs)
Source: pytest best practices
"""

import uuid
from datetime import datetime, timezone
from typing import Any

# Default test passwords
DEFAULT_PASSWORD = "TestPassword123!"
ADMIN_PASSWORD = "AdminPassword123!"

# =============================================================================
# USER FACTORIES
# =============================================================================


def create_user_data(
    *,
    username: str | None = None,
    email: str | None = None,
    password: str = DEFAULT_PASSWORD,
    full_name: str = "Test User",
    role: str = "viewer",
    department: str | None = None,
    is_active: bool = True,
) -> dict[str, Any]:
    """
    Create user data dictionary for testing.

    Args:
        username: Username (auto-generated if None)
        email: Email (auto-generated if None)
        password: Plain text password
        full_name: User's full name
        role: User role (viewer, auditor, admin)
        department: Optional department
        is_active: Whether user is active

    Returns:
        Dictionary suitable for user creation
    """
    uid = uuid.uuid4().hex[:8]
    return {
        "username": username or f"testuser_{uid}",
        "email": email or f"testuser_{uid}@example.com",
        "password": password,
        "full_name": full_name,
        "role": role,
        "department": department,
        "is_active": is_active,
    }


def create_admin_data(**kwargs) -> dict[str, Any]:
    """Create admin user data."""
    defaults = {
        "username": f"admin_{uuid.uuid4().hex[:8]}",
        "email": f"admin_{uuid.uuid4().hex[:8]}@example.com",
        "password": ADMIN_PASSWORD,
        "full_name": "Test Admin",
        "role": "admin",
    }
    defaults.update(kwargs)
    return create_user_data(**defaults)


def create_auditor_data(**kwargs) -> dict[str, Any]:
    """Create auditor user data."""
    defaults = {
        "role": "auditor",
        "full_name": "Test Auditor",
    }
    defaults.update(kwargs)
    return create_user_data(**defaults)


# =============================================================================
# CASE FACTORIES
# =============================================================================

# Valid case types from database schema (case_type enum)
CASE_TYPES = ["USB", "EMAIL", "WEB", "POLICY"]

# Valid case statuses (case_status enum)
CASE_STATUSES = ["OPEN", "IN_PROGRESS", "PENDING_REVIEW", "CLOSED", "ARCHIVED"]

# Valid severity levels (severity_level enum)
SEVERITY_LEVELS = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

# Valid scope codes (from scopes table)
SCOPE_CODES = [
    "FIN", "HR", "IT", "SEC", "OPS", "LEG", "PRO", "MKT",
    "RND", "QA", "ENV", "SAF", "EXT", "GOV", "GEN"
]


def create_case_data(
    *,
    scope_code: str = "IT",
    case_type: str = "USB",
    status: str = "OPEN",
    severity: str = "MEDIUM",
    title: str | None = None,
    summary: str | None = None,
    description: str | None = None,
    subject_user: str | None = None,
    subject_computer: str | None = None,
    subject_devices: list[str] | None = None,
    related_users: list[str] | None = None,
    tags: list[str] | None = None,
    incident_date: datetime | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create case data dictionary for testing.

    Args:
        scope_code: Scope code (FIN, HR, IT, etc.)
        case_type: Case type (USB, EMAIL, WEB, etc.)
        status: Case status
        severity: Severity level
        title: Case title (auto-generated if None)
        summary: Case summary
        description: Detailed description
        subject_user: Subject of investigation
        subject_computer: Computer involved
        subject_devices: List of devices
        related_users: List of related users
        tags: List of tags
        incident_date: When incident occurred
        metadata: Additional metadata

    Returns:
        Dictionary suitable for case creation
    """
    uid = uuid.uuid4().hex[:6]
    return {
        "scope_code": scope_code,
        "case_type": case_type,
        "status": status,
        "severity": severity,
        "title": title or f"Test Case {uid}",
        "summary": summary or f"Test case summary for {uid}",
        "description": description or f"Detailed description for test case {uid}",
        "subject_user": subject_user,
        "subject_computer": subject_computer,
        "subject_devices": subject_devices or [],
        "related_users": related_users or [],
        "tags": tags or ["test"],
        "incident_date": incident_date,
        "metadata": metadata or {},
    }


def create_critical_case_data(**kwargs) -> dict[str, Any]:
    """Create critical severity case data."""
    defaults = {
        "severity": "CRITICAL",
        "title": "Critical Security Incident",
        "status": "OPEN",
    }
    defaults.update(kwargs)
    return create_case_data(**defaults)


def create_closed_case_data(**kwargs) -> dict[str, Any]:
    """Create closed case data."""
    defaults = {
        "status": "CLOSED",
        "title": "Completed Investigation",
    }
    defaults.update(kwargs)
    return create_case_data(**defaults)


# =============================================================================
# EVIDENCE FACTORIES
# =============================================================================

# Common MIME types for testing
MIME_TYPES = {
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "txt": "text/plain",
    "png": "image/png",
    "jpg": "image/jpeg",
    "eml": "message/rfc822",
    "msg": "application/vnd.ms-outlook",
}


def create_evidence_data(
    *,
    file_name: str | None = None,
    file_path: str | None = None,
    file_size: int = 1024,
    mime_type: str = "application/pdf",
    file_hash: str | None = None,
    description: str | None = None,
    extracted_text: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create evidence data dictionary for testing.

    Args:
        file_name: Original filename
        file_path: Storage path
        file_size: File size in bytes
        mime_type: MIME type
        file_hash: SHA-256 hash
        description: Evidence description
        extracted_text: Text extracted from file
        metadata: Additional metadata

    Returns:
        Dictionary suitable for evidence creation
    """
    uid = uuid.uuid4().hex[:8]
    return {
        "file_name": file_name or f"evidence_{uid}.pdf",
        "file_path": file_path or f"evidence/test/{uid}.pdf",
        "file_size": file_size,
        "mime_type": mime_type,
        "file_hash": file_hash or f"sha256:{uuid.uuid4().hex}",
        "description": description or f"Test evidence file {uid}",
        "extracted_text": extracted_text,
        "metadata": metadata or {},
    }


def create_email_evidence_data(**kwargs) -> dict[str, Any]:
    """Create email evidence data."""
    defaults = {
        "file_name": "suspicious_email.eml",
        "mime_type": "message/rfc822",
        "description": "Suspicious email from external source",
    }
    defaults.update(kwargs)
    return create_evidence_data(**defaults)


def create_screenshot_evidence_data(**kwargs) -> dict[str, Any]:
    """Create screenshot evidence data."""
    defaults = {
        "file_name": "screenshot.png",
        "mime_type": "image/png",
        "description": "Screenshot of suspicious activity",
    }
    defaults.update(kwargs)
    return create_evidence_data(**defaults)


# =============================================================================
# FINDING FACTORIES
# =============================================================================


def create_finding_data(
    *,
    title: str | None = None,
    description: str | None = None,
    severity: str = "MEDIUM",
    evidence_ids: list[str] | None = None,
) -> dict[str, Any]:
    """
    Create finding data dictionary for testing.

    Args:
        title: Finding title
        description: Finding description
        severity: Severity level
        evidence_ids: List of related evidence UUIDs

    Returns:
        Dictionary suitable for finding creation
    """
    uid = uuid.uuid4().hex[:6]
    return {
        "title": title or f"Finding {uid}",
        "description": description or f"Description of finding {uid}",
        "severity": severity,
        "evidence_ids": evidence_ids or [],
    }


def create_critical_finding_data(**kwargs) -> dict[str, Any]:
    """Create critical severity finding data."""
    defaults = {
        "severity": "CRITICAL",
        "title": "Critical Security Vulnerability",
        "description": "A critical security vulnerability was discovered.",
    }
    defaults.update(kwargs)
    return create_finding_data(**defaults)


# =============================================================================
# TIMELINE EVENT FACTORIES
# =============================================================================

# Valid event types
EVENT_TYPES = [
    "CREATED", "UPDATED", "STATUS_CHANGE", "EVIDENCE_ADDED",
    "FINDING_ADDED", "COMMENT", "ASSIGNMENT", "OTHER"
]


def create_timeline_event_data(
    *,
    event_type: str = "OTHER",
    event_time: datetime | None = None,
    description: str | None = None,
    source: str = "user",
    evidence_id: str | None = None,
) -> dict[str, Any]:
    """
    Create timeline event data dictionary for testing.

    Args:
        event_type: Type of event
        event_time: When the event occurred
        description: Event description
        source: Event source (user, system, etc.)
        evidence_id: Related evidence UUID

    Returns:
        Dictionary suitable for timeline event creation
    """
    return {
        "event_type": event_type,
        "event_time": event_time or datetime.now(timezone.utc),
        "description": description or f"Test event at {datetime.now(timezone.utc).isoformat()}",
        "source": source,
        "evidence_id": evidence_id,
    }


# =============================================================================
# ENTITY FACTORIES
# =============================================================================

# Valid entity types
ENTITY_TYPES = [
    "EMAIL", "IP_ADDRESS", "DOMAIN", "URL", "HASH",
    "USERNAME", "FILE_PATH", "PHONE", "DATE", "AMOUNT"
]


def create_entity_data(
    *,
    entity_type: str = "EMAIL",
    value: str | None = None,
    context: str | None = None,
    confidence: float = 0.95,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create entity data dictionary for testing.

    Args:
        entity_type: Type of entity
        value: Entity value
        context: Context where entity was found
        confidence: Extraction confidence (0-1)
        metadata: Additional metadata

    Returns:
        Dictionary suitable for entity creation
    """
    uid = uuid.uuid4().hex[:6]
    default_values = {
        "EMAIL": f"user_{uid}@example.com",
        "IP_ADDRESS": "192.168.1.100",
        "DOMAIN": "suspicious-domain.com",
        "URL": "https://suspicious-domain.com/path",
        "HASH": f"sha256:{uuid.uuid4().hex}",
        "USERNAME": f"user_{uid}",
    }
    return {
        "entity_type": entity_type,
        "value": value or default_values.get(entity_type, f"value_{uid}"),
        "context": context or f"Found in test evidence {uid}",
        "confidence": confidence,
        "metadata": metadata or {},
    }


# =============================================================================
# WORKFLOW FACTORIES
# =============================================================================


def create_workflow_rule_data(
    *,
    name: str | None = None,
    description: str | None = None,
    trigger_type: str = "EVENT",
    trigger_config: dict[str, Any] | None = None,
    is_enabled: bool = True,
) -> dict[str, Any]:
    """
    Create workflow rule data dictionary for testing.

    Args:
        name: Rule name
        description: Rule description
        trigger_type: Type of trigger (STATUS_CHANGE, TIME_BASED, EVENT, CONDITION)
        trigger_config: Trigger configuration
        is_enabled: Whether rule is enabled

    Returns:
        Dictionary suitable for workflow rule creation
    """
    uid = uuid.uuid4().hex[:6]
    return {
        "name": name or f"Test Rule {uid}",
        "description": description or f"Test workflow rule {uid}",
        "trigger_type": trigger_type,
        "trigger_config": trigger_config or {"event": "case_created"},
        "is_enabled": is_enabled,
    }


def create_workflow_action_data(
    *,
    action_type: str = "SEND_NOTIFICATION",
    action_config: dict[str, Any] | None = None,
    order: int = 1,
) -> dict[str, Any]:
    """
    Create workflow action data dictionary for testing.

    Args:
        action_type: Type of action
        action_config: Action configuration
        order: Execution order

    Returns:
        Dictionary suitable for workflow action creation
    """
    return {
        "action_type": action_type,
        "action_config": action_config or {
            "message": "Test notification",
            "priority": "NORMAL",
        },
        "order": order,
    }


# =============================================================================
# NOTIFICATION FACTORIES
# =============================================================================


def create_notification_data(
    *,
    title: str | None = None,
    message: str | None = None,
    notification_type: str = "INFO",
    priority: str = "NORMAL",
    related_case_id: str | None = None,
    related_entity_type: str | None = None,
    related_entity_id: str | None = None,
) -> dict[str, Any]:
    """
    Create notification data dictionary for testing.

    Args:
        title: Notification title
        message: Notification message
        notification_type: Type (INFO, WARNING, ERROR, SUCCESS)
        priority: Priority (LOW, NORMAL, HIGH, URGENT)
        related_case_id: Related case UUID
        related_entity_type: Type of related entity
        related_entity_id: Related entity UUID

    Returns:
        Dictionary suitable for notification creation
    """
    uid = uuid.uuid4().hex[:6]
    return {
        "title": title or f"Test Notification {uid}",
        "message": message or f"Test notification message {uid}",
        "notification_type": notification_type,
        "priority": priority,
        "related_case_id": related_case_id,
        "related_entity_type": related_entity_type,
        "related_entity_id": related_entity_id,
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def generate_uuid() -> str:
    """Generate a random UUID string."""
    return str(uuid.uuid4())


def generate_file_hash() -> str:
    """Generate a fake file hash."""
    return f"sha256:{uuid.uuid4().hex}{uuid.uuid4().hex[:32]}"


def generate_jwt_token() -> str:
    """Generate a fake JWT token for testing invalid token scenarios."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0In0.invalid"
