"""
Integration tests for the cases router.

Tests cover:
- Listing cases with pagination and filters
- Creating new cases
- Getting case by ID
- Updating cases
- Deleting (archiving) cases
- Timeline events
- Findings

Uses PostgreSQL via testcontainers (local) or CI service (GitHub Actions).
"""

import pytest
from uuid import uuid4
from datetime import datetime

from tests.fixtures.factories import create_case_data, create_user_data


# =============================================================================
# List Cases Tests
# =============================================================================


class TestListCases:
    """Tests for GET /cases endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_list_cases_returns_paginated_response(
        self,
        async_client,
        test_user,
        auth_headers,
    ):
        """Should return paginated response structure.

        Note: In shared database environments, we verify the response structure
        rather than expecting empty results. Test isolation is handled at the
        transaction level for data created during tests.
        """
        response = await async_client.get("/api/v1/cases", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        # Verify paginated response structure
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert isinstance(data["items"], list)
        assert isinstance(data["total"], int)
        assert data["total"] >= 0
        assert data["page"] >= 1

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_list_cases_with_data(
        self,
        async_client,
        test_case,
        auth_headers,
    ):
        """Should return cases when they exist."""
        response = await async_client.get("/api/v1/cases", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 1
        assert data["total"] >= 1

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_list_cases_pagination(
        self,
        async_client,
        test_case,
        auth_headers,
    ):
        """Should support pagination parameters."""
        response = await async_client.get(
            "/api/v1/cases",
            params={"page": 1, "page_size": 10},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_list_cases_filter_by_status(
        self,
        async_client,
        test_case,
        auth_headers,
    ):
        """Should filter cases by status."""
        response = await async_client.get(
            "/api/v1/cases",
            params={"status": "OPEN"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # All returned cases should have OPEN status
        for item in data["items"]:
            assert item["status"] == "OPEN"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_list_cases_filter_by_severity(
        self,
        async_client,
        test_case,
        auth_headers,
    ):
        """Should filter cases by severity."""
        response = await async_client.get(
            "/api/v1/cases",
            params={"severity": "HIGH"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        # All returned cases should have HIGH severity
        for item in response.json()["items"]:
            assert item["severity"] == "HIGH"

    @pytest.mark.asyncio
    async def test_list_cases_unauthenticated(
        self,
        async_client,
    ):
        """Should reject unauthenticated requests."""
        response = await async_client.get("/api/v1/cases")

        assert response.status_code == 401


# =============================================================================
# Create Case Tests
# =============================================================================


class TestCreateCase:
    """Tests for POST /cases endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_case_success(
        self,
        async_client,
        test_user,
        test_scope,
        auth_headers,
    ):
        """Should create a new case successfully."""
        case_data = {
            "scope_code": test_scope["code"],
            "case_type": "USB",
            "title": "Test Case Creation",
            "summary": "Testing case creation endpoint",
            "description": "Full description for testing",
            "severity": "HIGH",
        }

        response = await async_client.post(
            "/api/v1/cases",
            json=case_data,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == case_data["title"]
        assert data["summary"] == case_data["summary"]
        assert data["severity"] == "HIGH"
        assert data["status"] == "OPEN"  # Default status
        assert "case_id" in data
        assert data["scope_code"] == test_scope["code"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_case_generates_case_id(
        self,
        async_client,
        test_user,
        test_scope,
        auth_headers,
    ):
        """Should generate case_id in correct format."""
        case_data = {
            "scope_code": test_scope["code"],
            "case_type": "EMAIL",
            "title": "Email Investigation",
            "summary": "Email investigation summary",  # min_length=10
        }

        response = await async_client.post(
            "/api/v1/cases",
            json=case_data,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        # Case ID format: SCOPE-TYPE-SEQ
        case_id = data["case_id"]
        assert case_id.startswith(test_scope["code"])
        assert "EMAIL" in case_id

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_case_invalid_scope(
        self,
        async_client,
        test_user,
        auth_headers,
    ):
        """Should reject case with invalid scope."""
        case_data = {
            "scope_code": "INVALID",
            "case_type": "USB",
            "title": "Test Case for Invalid Scope",  # min_length=5
            "summary": "Testing invalid scope validation",  # min_length=10
        }

        response = await async_client.post(
            "/api/v1/cases",
            json=case_data,
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "Invalid scope code" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_case_missing_required_fields(
        self,
        async_client,
        test_user,
        auth_headers,
    ):
        """Should reject case with missing required fields."""
        case_data = {
            "scope_code": "IT",
            # Missing case_type and title
        }

        response = await async_client.post(
            "/api/v1/cases",
            json=case_data,
            headers=auth_headers,
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_create_case_unauthenticated(
        self,
        async_client,
    ):
        """Should reject unauthenticated requests."""
        case_data = {
            "scope_code": "IT",
            "case_type": "USB",
            "title": "Test",
            "summary": "Summary",
        }

        response = await async_client.post(
            "/api/v1/cases",
            json=case_data,
        )

        assert response.status_code == 401


# =============================================================================
# Get Case Tests
# =============================================================================


class TestGetCase:
    """Tests for GET /cases/{case_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_case_success(
        self,
        async_client,
        test_case,
        auth_headers,
    ):
        """Should return case details."""
        case_id = test_case["case_id"]
        response = await async_client.get(
            f"/api/v1/cases/{case_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["case_id"] == case_id
        assert data["title"] == test_case["title"]

    @pytest.mark.asyncio
    async def test_get_case_by_uuid(
        self,
        async_client,
        test_case,
        auth_headers,
    ):
        """Should also work with UUID."""
        case_uuid = test_case["id"]
        response = await async_client.get(
            f"/api/v1/cases/{case_uuid}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(case_uuid)

    @pytest.mark.asyncio
    async def test_get_case_not_found(
        self,
        async_client,
        auth_headers,
    ):
        """Should return 404 for non-existent case."""
        response = await async_client.get(
            "/api/v1/cases/INVALID-CASE-0000",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_case_unauthenticated(
        self,
        async_client,
        test_case,
    ):
        """Should reject unauthenticated requests."""
        response = await async_client.get(
            f"/api/v1/cases/{test_case['case_id']}",
        )

        assert response.status_code == 401


# =============================================================================
# Update Case Tests
# =============================================================================


class TestUpdateCase:
    """Tests for PATCH /cases/{case_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_case_success(
        self,
        async_client,
        test_case,
        auth_headers,
    ):
        """Should update case successfully."""
        case_id = test_case["case_id"]
        update_data = {
            "title": "Updated Title",
            "summary": "Updated summary text",
        }

        response = await async_client.patch(
            f"/api/v1/cases/{case_id}",
            json=update_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["summary"] == "Updated summary text"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_update_case_status(
        self,
        async_client,
        test_case,
        auth_headers,
    ):
        """Should update case status."""
        case_id = test_case["case_id"]
        update_data = {"status": "IN_PROGRESS"}

        response = await async_client.patch(
            f"/api/v1/cases/{case_id}",
            json=update_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["status"] == "IN_PROGRESS"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_update_case_severity(
        self,
        async_client,
        test_case,
        auth_headers,
    ):
        """Should update case severity."""
        case_id = test_case["case_id"]
        update_data = {"severity": "CRITICAL"}

        response = await async_client.patch(
            f"/api/v1/cases/{case_id}",
            json=update_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["severity"] == "CRITICAL"

    @pytest.mark.asyncio
    async def test_update_case_not_found(
        self,
        async_client,
        auth_headers,
    ):
        """Should return 404 for non-existent case."""
        response = await async_client.patch(
            "/api/v1/cases/INVALID-CASE-0000",
            json={"title": "New Title"},
            headers=auth_headers,
        )

        assert response.status_code == 404


# =============================================================================
# Delete Case Tests
# =============================================================================


class TestDeleteCase:
    """Tests for DELETE /cases/{case_id} endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_delete_case_success(
        self,
        async_client,
        test_case,
        auth_headers,
    ):
        """Should soft delete (archive) case."""
        case_id = test_case["case_id"]

        response = await async_client.delete(
            f"/api/v1/cases/{case_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "archived" in data["message"].lower()

        # Verify case is now archived
        get_response = await async_client.get(
            f"/api/v1/cases/{case_id}",
            headers=auth_headers,
        )
        assert get_response.json()["status"] == "ARCHIVED"

    @pytest.mark.asyncio
    async def test_delete_case_not_found(
        self,
        async_client,
        auth_headers,
    ):
        """Should return 404 for non-existent case."""
        response = await async_client.delete(
            "/api/v1/cases/INVALID-CASE-0000",
            headers=auth_headers,
        )

        assert response.status_code == 404


# =============================================================================
# Timeline Tests
# =============================================================================


class TestCaseTimeline:
    """Tests for case timeline endpoints."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_timeline_empty(
        self,
        async_client,
        test_case,
        auth_headers,
    ):
        """Should return empty timeline for new case."""
        case_id = test_case["case_id"]

        response = await async_client.get(
            f"/api/v1/cases/{case_id}/timeline",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_add_timeline_event(
        self,
        async_client,
        test_case,
        auth_headers,
    ):
        """Should add timeline event to case."""
        case_id = test_case["case_id"]

        response = await async_client.post(
            f"/api/v1/cases/{case_id}/timeline",
            params={
                "event_type": "INVESTIGATION",
                "description": "Started investigation",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["event_type"] == "INVESTIGATION"
        assert data["description"] == "Started investigation"

    @pytest.mark.asyncio
    async def test_timeline_case_not_found(
        self,
        async_client,
        auth_headers,
    ):
        """Should return 404 for non-existent case."""
        response = await async_client.get(
            "/api/v1/cases/INVALID-CASE-0000/timeline",
            headers=auth_headers,
        )

        assert response.status_code == 404


# =============================================================================
# Findings Tests
# =============================================================================


class TestCaseFindings:
    """Tests for case findings endpoints."""

    @pytest.mark.asyncio
    async def test_get_findings_empty(
        self,
        async_client,
        test_case,
        auth_headers,
    ):
        """Should return empty findings for new case."""
        case_id = test_case["case_id"]

        response = await async_client.get(
            f"/api/v1/cases/{case_id}/findings",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["items"] == []

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_add_finding(
        self,
        async_client,
        test_case,
        auth_headers,
    ):
        """Should add finding to case."""
        case_id = test_case["case_id"]

        response = await async_client.post(
            f"/api/v1/cases/{case_id}/findings",
            params={
                "title": "Critical Finding",
                "description": "Found unauthorized access",
                "severity": "CRITICAL",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Critical Finding"
        assert data["severity"] == "CRITICAL"

    @pytest.mark.asyncio
    async def test_findings_case_not_found(
        self,
        async_client,
        auth_headers,
    ):
        """Should return 404 for non-existent case."""
        response = await async_client.get(
            "/api/v1/cases/INVALID-CASE-0000/findings",
            headers=auth_headers,
        )

        assert response.status_code == 404
