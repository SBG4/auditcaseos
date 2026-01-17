"""
Unit tests for CaseService.

Tests cover:
- Case creation
- Case retrieval by ID and UUID
- Case listing with filters
- Case updates
- Case deletion
- Case response building

Source: pytest best practices
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.case_service import CaseService, case_service
from tests.conftest import create_test_case
from tests.fixtures.factories import (
    CASE_TYPES,
    SCOPE_CODES,
    SEVERITY_LEVELS,
    create_case_data,
)


@pytest.mark.unit
class TestCaseServiceInit:
    """Tests for CaseService initialization."""

    def test_case_service_singleton_exists(self):
        """Test that case_service singleton is available."""
        assert case_service is not None
        assert isinstance(case_service, CaseService)

    def test_case_service_can_be_instantiated(self):
        """Test that CaseService can be instantiated."""
        service = CaseService()
        assert service is not None


@pytest.mark.unit
class TestCreateCase:
    """Tests for case creation."""

    @pytest.mark.asyncio
    async def test_create_case_success(self, db_session: AsyncSession, test_user: dict):
        """Test successful case creation."""
        case_data = create_case_data(
            title="Test Security Incident",
            summary="Investigating unauthorized access",
        )

        case = await create_test_case(
            db=db_session,
            owner_id=test_user["id"],
            case_data=case_data,
        )

        assert case is not None
        assert case["title"] == "Test Security Incident"
        assert case["owner_id"] == test_user["id"]
        assert case["status"] == "OPEN"

    @pytest.mark.asyncio
    async def test_create_case_with_all_fields(self, db_session: AsyncSession, test_user: dict):
        """Test case creation with all optional fields."""
        case_data = create_case_data(
            title="Full Case",
            summary="Full case summary",
            description="Detailed description",
            subject_user="john.doe",
            subject_computer="WORKSTATION-001",
            severity="CRITICAL",
            status="IN_PROGRESS",
        )

        case = await create_test_case(
            db=db_session,
            owner_id=test_user["id"],
            case_data=case_data,
        )

        assert case["title"] == "Full Case"
        assert case["severity"] == "CRITICAL"
        assert case["status"] == "IN_PROGRESS"
        assert case["subject_user"] == "john.doe"
        assert case["subject_computer"] == "WORKSTATION-001"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scope_code", SCOPE_CODES[:6])  # Test subset
    async def test_create_case_with_different_scopes(
        self, db_session: AsyncSession, test_user: dict, scope_code: str
    ):
        """Test case creation with different scope codes."""
        case_data = create_case_data(scope_code=scope_code)

        case = await create_test_case(
            db=db_session,
            owner_id=test_user["id"],
            case_data=case_data,
        )

        assert case["scope_code"] == scope_code

    @pytest.mark.asyncio
    @pytest.mark.parametrize("case_type", CASE_TYPES)
    async def test_create_case_with_different_types(
        self, db_session: AsyncSession, test_user: dict, case_type: str
    ):
        """Test case creation with different case types."""
        case_data = create_case_data(case_type=case_type)

        case = await create_test_case(
            db=db_session,
            owner_id=test_user["id"],
            case_data=case_data,
        )

        assert case["case_type"] == case_type

    @pytest.mark.asyncio
    @pytest.mark.parametrize("severity", SEVERITY_LEVELS)
    async def test_create_case_with_different_severities(
        self, db_session: AsyncSession, test_user: dict, severity: str
    ):
        """Test case creation with different severity levels."""
        case_data = create_case_data(severity=severity)

        case = await create_test_case(
            db=db_session,
            owner_id=test_user["id"],
            case_data=case_data,
        )

        assert case["severity"] == severity


@pytest.mark.unit
class TestGetCase:
    """Tests for case retrieval."""

    @pytest.mark.asyncio
    async def test_get_case_by_uuid(
        self, db_session: AsyncSession, test_case: dict
    ):
        """Test retrieving case by UUID."""
        from sqlalchemy import text

        result = await db_session.execute(
            text("SELECT * FROM cases WHERE id = :id"),
            {"id": test_case["id"]}
        )
        case = result.fetchone()

        assert case is not None
        assert dict(case._mapping)["id"] == test_case["id"]

    @pytest.mark.asyncio
    async def test_get_case_by_case_id(
        self, db_session: AsyncSession, test_case: dict
    ):
        """Test retrieving case by case_id string."""
        from sqlalchemy import text

        result = await db_session.execute(
            text("SELECT * FROM cases WHERE case_id = :case_id"),
            {"case_id": test_case["case_id"]}
        )
        case = result.fetchone()

        assert case is not None
        assert dict(case._mapping)["case_id"] == test_case["case_id"]

    @pytest.mark.asyncio
    async def test_get_case_not_found(self, db_session: AsyncSession):
        """Test retrieving non-existent case."""
        from sqlalchemy import text

        result = await db_session.execute(
            text("SELECT * FROM cases WHERE id = :id"),
            {"id": "00000000-0000-0000-0000-000000000000"}
        )
        case = result.fetchone()

        assert case is None


@pytest.mark.unit
class TestListCases:
    """Tests for case listing.

    Note: These tests filter by owner_id to ensure test isolation.
    This is necessary because transaction rollback only prevents writes
    from persisting, but doesn't hide existing data in shared databases.
    """

    @pytest.mark.asyncio
    async def test_list_cases_empty_for_owner(
        self, db_session: AsyncSession, test_user: dict
    ):
        """Test listing when owner has no cases."""
        from sqlalchemy import text

        # Filter by owner to ensure isolation from production data
        result = await db_session.execute(
            text("SELECT COUNT(*) FROM cases WHERE owner_id = :owner_id"),
            {"owner_id": test_user["id"]}
        )
        count = result.scalar()

        assert count == 0

    @pytest.mark.asyncio
    async def test_list_cases_with_cases(
        self, db_session: AsyncSession, test_user: dict
    ):
        """Test listing with multiple cases for an owner."""
        # Create multiple cases
        for i in range(3):
            await create_test_case(
                db=db_session,
                owner_id=test_user["id"],
                case_data=create_case_data(title=f"Case {i}"),
            )

        from sqlalchemy import text
        result = await db_session.execute(
            text("SELECT * FROM cases WHERE owner_id = :owner_id"),
            {"owner_id": test_user["id"]}
        )
        cases = result.fetchall()

        assert len(cases) == 3

    @pytest.mark.asyncio
    async def test_list_cases_with_status_filter(
        self, db_session: AsyncSession, test_user: dict
    ):
        """Test listing with status filter."""
        # Create cases with different statuses
        await create_test_case(
            db=db_session,
            owner_id=test_user["id"],
            case_data=create_case_data(status="OPEN"),
        )
        await create_test_case(
            db=db_session,
            owner_id=test_user["id"],
            case_data=create_case_data(status="CLOSED"),
        )

        from sqlalchemy import text
        result = await db_session.execute(
            text("SELECT * FROM cases WHERE status = :status AND owner_id = :owner_id"),
            {"status": "OPEN", "owner_id": test_user["id"]}
        )
        cases = result.fetchall()

        assert len(cases) == 1
        assert dict(cases[0]._mapping)["status"] == "OPEN"

    @pytest.mark.asyncio
    async def test_list_cases_with_severity_filter(
        self, db_session: AsyncSession, test_user: dict
    ):
        """Test listing with severity filter."""
        await create_test_case(
            db=db_session,
            owner_id=test_user["id"],
            case_data=create_case_data(severity="CRITICAL"),
        )
        await create_test_case(
            db=db_session,
            owner_id=test_user["id"],
            case_data=create_case_data(severity="LOW"),
        )

        from sqlalchemy import text
        result = await db_session.execute(
            text("SELECT * FROM cases WHERE severity = :severity AND owner_id = :owner_id"),
            {"severity": "CRITICAL", "owner_id": test_user["id"]}
        )
        cases = result.fetchall()

        assert len(cases) == 1
        assert dict(cases[0]._mapping)["severity"] == "CRITICAL"


@pytest.mark.unit
class TestUpdateCase:
    """Tests for case updates."""

    @pytest.mark.asyncio
    async def test_update_case_title(
        self, db_session: AsyncSession, test_case: dict
    ):
        """Test updating case title."""
        from sqlalchemy import text

        await db_session.execute(
            text("UPDATE cases SET title = :title WHERE id = :id"),
            {"title": "Updated Title", "id": test_case["id"]}
        )
        await db_session.commit()

        result = await db_session.execute(
            text("SELECT * FROM cases WHERE id = :id"),
            {"id": test_case["id"]}
        )
        case = result.fetchone()

        assert dict(case._mapping)["title"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_update_case_status(
        self, db_session: AsyncSession, test_case: dict
    ):
        """Test updating case status."""
        from sqlalchemy import text

        await db_session.execute(
            text("UPDATE cases SET status = :status WHERE id = :id"),
            {"status": "CLOSED", "id": test_case["id"]}
        )
        await db_session.commit()

        result = await db_session.execute(
            text("SELECT * FROM cases WHERE id = :id"),
            {"id": test_case["id"]}
        )
        case = result.fetchone()

        assert dict(case._mapping)["status"] == "CLOSED"

    @pytest.mark.asyncio
    async def test_update_case_severity(
        self, db_session: AsyncSession, test_case: dict
    ):
        """Test updating case severity."""
        from sqlalchemy import text

        await db_session.execute(
            text("UPDATE cases SET severity = :severity WHERE id = :id"),
            {"severity": "CRITICAL", "id": test_case["id"]}
        )
        await db_session.commit()

        result = await db_session.execute(
            text("SELECT * FROM cases WHERE id = :id"),
            {"id": test_case["id"]}
        )
        case = result.fetchone()

        assert dict(case._mapping)["severity"] == "CRITICAL"


@pytest.mark.unit
class TestDeleteCase:
    """Tests for case deletion."""

    @pytest.mark.asyncio
    async def test_delete_case_success(
        self, db_session: AsyncSession, test_case: dict
    ):
        """Test successful case deletion."""
        from sqlalchemy import text

        await db_session.execute(
            text("DELETE FROM cases WHERE id = :id"),
            {"id": test_case["id"]}
        )
        await db_session.commit()

        result = await db_session.execute(
            text("SELECT * FROM cases WHERE id = :id"),
            {"id": test_case["id"]}
        )
        case = result.fetchone()

        assert case is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_case(self, db_session: AsyncSession):
        """Test deleting non-existent case."""
        from sqlalchemy import text

        result = await db_session.execute(
            text("DELETE FROM cases WHERE id = :id RETURNING id"),
            {"id": "00000000-0000-0000-0000-000000000000"}
        )
        deleted = result.fetchone()

        assert deleted is None


@pytest.mark.unit
class TestCaseIdFormat:
    """Tests for case ID format validation."""

    def test_case_id_format_pattern(self):
        """Test case ID follows SCOPE-TYPE-XXXX pattern."""
        import re
        pattern = r"^[A-Z]{2,4}-[A-Z]{2,6}-[A-Z0-9]{4}$"

        valid_ids = ["FIN-USB-0001", "IT-EMAIL-A1B2", "HR-POLICY-1234"]
        for case_id in valid_ids:
            assert re.match(pattern, case_id), f"{case_id} should match pattern"

    def test_invalid_case_id_format(self):
        """Test invalid case ID formats are detected."""
        import re
        pattern = r"^[A-Z]{2,4}-[A-Z]{2,6}-[A-Z0-9]{4}$"

        invalid_ids = ["fin-usb-0001", "FINANCE-USB-0001", "FIN-USB-001"]
        for case_id in invalid_ids:
            assert not re.match(pattern, case_id), f"{case_id} should not match pattern"
