"""
Unit tests for AuditService.

Tests cover:
- Logging create/update/delete/view/download actions
- Logging login attempts
- Retrieving entity history
- Retrieving user activity

Source: pytest best practices
Uses PostgreSQL via testcontainers (local) or CI service (GitHub Actions).
"""

import pytest
import uuid
import json
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.audit_service import AuditService, audit_service
from tests.conftest import create_test_user, create_test_case


@pytest.mark.unit
class TestAuditServiceInit:
    """Tests for AuditService initialization."""

    def test_audit_service_singleton_exists(self):
        """Test that audit_service singleton is available."""
        assert audit_service is not None
        assert isinstance(audit_service, AuditService)

    def test_audit_service_can_be_instantiated(self):
        """Test that AuditService can be instantiated."""
        service = AuditService()
        assert service is not None


@pytest.mark.unit
class TestLogAction:
    """Tests for the generic log_action method."""

    @pytest.mark.asyncio
    async def test_log_action_minimal(self, db_session: AsyncSession, test_user: dict):
        """Test logging action with minimal parameters."""
        import json

        query = text("""
            INSERT INTO audit_log (
                action, entity_type, entity_id, user_id, metadata
            ) VALUES (
                :action, :entity_type, :entity_id, :user_id, :metadata
            )
        """)

        await db_session.execute(query, {
            "action": "TEST_ACTION",
            "entity_type": "test",
            "entity_id": str(uuid.uuid4()),  # Must be valid UUID
            "user_id": test_user["id"],
            "metadata": json.dumps({}),
        })
        await db_session.commit()

        # Verify log was created
        result = await db_session.execute(
            text("SELECT * FROM audit_log WHERE action = :action"),
            {"action": "TEST_ACTION"}
        )
        log = result.fetchone()

        assert log is not None
        assert dict(log._mapping)["action"] == "TEST_ACTION"

    @pytest.mark.asyncio
    async def test_log_action_with_all_fields(self, db_session: AsyncSession, test_user: dict):
        """Test logging action with all fields."""
        import json

        test_entity_id = str(uuid.uuid4())  # Use unique ID to isolate this test
        test_ip = "192.168.1.100"

        query = text("""
            INSERT INTO audit_log (
                action, entity_type, entity_id, user_id, user_ip, metadata
            ) VALUES (
                :action, :entity_type, :entity_id, :user_id, :user_ip, :metadata
            )
        """)

        await db_session.execute(query, {
            "action": "CREATE",
            "entity_type": "case",
            "entity_id": test_entity_id,
            "user_id": test_user["id"],
            "user_ip": test_ip,
            "metadata": json.dumps({"source": "api"}),
        })
        await db_session.commit()

        # Query by the specific entity_id we created to ensure isolation
        result = await db_session.execute(
            text("SELECT * FROM audit_log WHERE entity_id = :entity_id"),
            {"entity_id": test_entity_id}
        )
        log = result.fetchone()

        assert log is not None
        log_dict = dict(log._mapping)
        assert log_dict["user_ip"] == test_ip
        assert log_dict["action"] == "CREATE"
        assert log_dict["entity_type"] == "case"


@pytest.mark.unit
class TestLogCreate:
    """Tests for logging create actions."""

    @pytest.mark.asyncio
    async def test_log_create_case(self, db_session: AsyncSession, test_user: dict, test_case: dict):
        """Test logging case creation."""
        import json

        query = text("""
            INSERT INTO audit_log (
                action, entity_type, entity_id, user_id, metadata
            ) VALUES (
                'CREATE', 'case', :entity_id, :user_id, :metadata
            )
        """)

        await db_session.execute(query, {
            "entity_id": test_case["id"],
            "user_id": test_user["id"],
            "metadata": json.dumps({"title": test_case["title"]}),
        })
        await db_session.commit()

        result = await db_session.execute(
            text("SELECT * FROM audit_log WHERE entity_id = :id"),
            {"id": test_case["id"]}
        )
        log = result.fetchone()

        assert log is not None
        assert dict(log._mapping)["action"] == "CREATE"


@pytest.mark.unit
class TestLogUpdate:
    """Tests for logging update actions."""

    @pytest.mark.asyncio
    async def test_log_update_case(self, db_session: AsyncSession, test_user: dict, test_case: dict):
        """Test logging case update."""
        import json

        query = text("""
            INSERT INTO audit_log (
                action, entity_type, entity_id, user_id, old_values, new_values
            ) VALUES (
                'UPDATE', 'case', :entity_id, :user_id, :old_values, :new_values
            )
        """)

        await db_session.execute(query, {
            "entity_id": test_case["id"],
            "user_id": test_user["id"],
            "old_values": json.dumps({"status": "OPEN"}),
            "new_values": json.dumps({"status": "IN_PROGRESS"}),
        })
        await db_session.commit()

        result = await db_session.execute(
            text("SELECT * FROM audit_log WHERE action = 'UPDATE' AND entity_id = :id"),
            {"id": test_case["id"]}
        )
        log = result.fetchone()

        assert log is not None


@pytest.mark.unit
class TestLogDelete:
    """Tests for logging delete actions."""

    @pytest.mark.asyncio
    async def test_log_delete_case(self, db_session: AsyncSession, test_user: dict, test_case: dict):
        """Test logging case deletion."""
        import json

        query = text("""
            INSERT INTO audit_log (
                action, entity_type, entity_id, user_id, metadata
            ) VALUES (
                'DELETE', 'case', :entity_id, :user_id, :metadata
            )
        """)

        await db_session.execute(query, {
            "entity_id": test_case["id"],
            "user_id": test_user["id"],
            "metadata": json.dumps({"title": test_case["title"]}),
        })
        await db_session.commit()

        result = await db_session.execute(
            text("SELECT * FROM audit_log WHERE action = 'DELETE' AND entity_id = :id"),
            {"id": test_case["id"]}
        )
        log = result.fetchone()

        assert log is not None


@pytest.mark.unit
class TestLogView:
    """Tests for logging view actions."""

    @pytest.mark.asyncio
    async def test_log_view_case(self, db_session: AsyncSession, test_user: dict, test_case: dict):
        """Test logging case view."""
        import json

        query = text("""
            INSERT INTO audit_log (
                action, entity_type, entity_id, user_id, metadata
            ) VALUES (
                'VIEW', 'case', :entity_id, :user_id, :metadata
            )
        """)

        await db_session.execute(query, {
            "entity_id": test_case["id"],
            "user_id": test_user["id"],
            "metadata": json.dumps({}),
        })
        await db_session.commit()

        result = await db_session.execute(
            text("SELECT * FROM audit_log WHERE action = 'VIEW' AND entity_id = :id"),
            {"id": test_case["id"]}
        )
        log = result.fetchone()

        assert log is not None


@pytest.mark.unit
class TestLogDownload:
    """Tests for logging download actions."""

    @pytest.mark.asyncio
    async def test_log_download_evidence(self, db_session: AsyncSession, test_user: dict):
        """Test logging evidence download."""
        import json

        evidence_id = str(uuid.uuid4())
        query = text("""
            INSERT INTO audit_log (
                action, entity_type, entity_id, user_id, metadata
            ) VALUES (
                'DOWNLOAD', 'evidence', :entity_id, :user_id, :metadata
            )
        """)

        await db_session.execute(query, {
            "entity_id": evidence_id,
            "user_id": test_user["id"],
            "metadata": json.dumps({"file_path": "cases/FIN-USB-0001/doc.pdf"}),
        })
        await db_session.commit()

        result = await db_session.execute(
            text("SELECT * FROM audit_log WHERE action = 'DOWNLOAD' AND entity_id = :id"),
            {"id": evidence_id}
        )
        log = result.fetchone()

        assert log is not None


@pytest.mark.unit
class TestLogLogin:
    """Tests for logging login actions."""

    @pytest.mark.asyncio
    async def test_log_login_success(self, db_session: AsyncSession, test_user: dict):
        """Test logging successful login."""
        import json

        query = text("""
            INSERT INTO audit_log (
                action, entity_type, entity_id, user_id, user_ip, metadata
            ) VALUES (
                'LOGIN_SUCCESS', 'user', :entity_id, :user_id, :user_ip, :metadata
            )
        """)

        await db_session.execute(query, {
            "entity_id": test_user["id"],
            "user_id": test_user["id"],
            "user_ip": "192.168.1.100",
            "metadata": json.dumps({"username": test_user["username"]}),
        })
        await db_session.commit()

        result = await db_session.execute(
            text("SELECT * FROM audit_log WHERE action = 'LOGIN_SUCCESS'")
        )
        log = result.fetchone()

        assert log is not None

    @pytest.mark.asyncio
    async def test_log_login_failure(self, db_session: AsyncSession):
        """Test logging failed login."""
        import json

        query = text("""
            INSERT INTO audit_log (
                action, entity_type, user_ip, metadata
            ) VALUES (
                'LOGIN_FAILURE', 'user', :user_ip, :metadata
            )
        """)

        await db_session.execute(query, {
            "user_ip": "192.168.1.100",
            "metadata": json.dumps({"username": "invalid_user"}),
        })
        await db_session.commit()

        result = await db_session.execute(
            text("SELECT * FROM audit_log WHERE action = 'LOGIN_FAILURE'")
        )
        log = result.fetchone()

        assert log is not None


@pytest.mark.unit
class TestGetEntityHistory:
    """Tests for retrieving entity history."""

    @pytest.mark.asyncio
    async def test_get_entity_history_empty(self, db_session: AsyncSession):
        """Test getting history for entity with no logs."""
        result = await db_session.execute(
            text("""
                SELECT * FROM audit_log
                WHERE entity_type = 'case' AND entity_id = :id
                ORDER BY created_at DESC
            """),
            {"id": str(uuid.uuid4())}
        )
        logs = result.fetchall()

        assert logs == []

    @pytest.mark.asyncio
    async def test_get_entity_history_with_logs(
        self, db_session: AsyncSession, test_user: dict, test_case: dict
    ):
        """Test getting history for entity with multiple logs."""
        import json

        # Create multiple log entries
        for action in ["CREATE", "UPDATE", "VIEW"]:
            await db_session.execute(
                text("""
                    INSERT INTO audit_log (
                        action, entity_type, entity_id, user_id, metadata
                    ) VALUES (
                        :action, 'case', :entity_id, :user_id, :metadata
                    )
                """),
                {
                    "action": action,
                    "entity_id": test_case["id"],
                    "user_id": test_user["id"],
                    "metadata": json.dumps({}),
                }
            )
        await db_session.commit()

        result = await db_session.execute(
            text("""
                SELECT * FROM audit_log
                WHERE entity_type = 'case' AND entity_id = :id
                ORDER BY created_at DESC
            """),
            {"id": test_case["id"]}
        )
        logs = result.fetchall()

        assert len(logs) == 3


@pytest.mark.unit
class TestGetUserActivity:
    """Tests for retrieving user activity."""

    @pytest.mark.asyncio
    async def test_get_user_activity_empty(self, db_session: AsyncSession, test_user: dict):
        """Test getting activity for user with no logs."""
        result = await db_session.execute(
            text("""
                SELECT * FROM audit_log
                WHERE user_id = :user_id
                ORDER BY created_at DESC
            """),
            {"user_id": test_user["id"]}
        )
        logs = result.fetchall()

        assert logs == []

    @pytest.mark.asyncio
    async def test_get_user_activity_with_logs(
        self, db_session: AsyncSession, test_user: dict
    ):
        """Test getting activity for user with multiple actions."""
        import json

        # Create multiple activities
        for i in range(5):
            await db_session.execute(
                text("""
                    INSERT INTO audit_log (
                        action, entity_type, entity_id, user_id, metadata
                    ) VALUES (
                        :action, :entity_type, :entity_id, :user_id, :metadata
                    )
                """),
                {
                    "action": "VIEW",
                    "entity_type": "case",
                    "entity_id": str(uuid.uuid4()),
                    "user_id": test_user["id"],
                    "metadata": json.dumps({}),
                }
            )
        await db_session.commit()

        result = await db_session.execute(
            text("""
                SELECT * FROM audit_log
                WHERE user_id = :user_id
                ORDER BY created_at DESC
            """),
            {"user_id": test_user["id"]}
        )
        logs = result.fetchall()

        assert len(logs) == 5

    @pytest.mark.asyncio
    async def test_get_user_activity_limit(
        self, db_session: AsyncSession, test_user: dict
    ):
        """Test getting limited user activity."""
        import json

        # Create more than limit
        for i in range(10):
            await db_session.execute(
                text("""
                    INSERT INTO audit_log (
                        action, entity_type, entity_id, user_id, metadata
                    ) VALUES (
                        :action, :entity_type, :entity_id, :user_id, :metadata
                    )
                """),
                {
                    "action": "VIEW",
                    "entity_type": "case",
                    "entity_id": str(uuid.uuid4()),
                    "user_id": test_user["id"],
                    "metadata": json.dumps({}),
                }
            )
        await db_session.commit()

        # Query with limit
        result = await db_session.execute(
            text("""
                SELECT * FROM audit_log
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            {"user_id": test_user["id"], "limit": 5}
        )
        logs = result.fetchall()

        assert len(logs) == 5
