"""
Tests for authentication router.

Tests cover:
- Login with username/email
- User registration (admin only)
- Get current user profile
- Password change
- User listing and management

Source: FastAPI testing best practices
"""

import pytest
from httpx import AsyncClient

from tests.conftest import create_test_user


class TestLogin:
    """Tests for the login endpoint."""

    @pytest.mark.asyncio
    async def test_login_success_with_username(self, client: AsyncClient, test_user: dict):
        """Test successful login with username."""
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "TestPassword123!"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["username"] == "testuser"
        assert data["email"] == "testuser@example.com"

    @pytest.mark.asyncio
    async def test_login_success_with_email(self, client: AsyncClient, test_user: dict):
        """Test successful login with email."""
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "testuser@example.com", "password": "TestPassword123!"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    @pytest.mark.asyncio
    async def test_login_invalid_password(self, client: AsyncClient, test_user: dict):
        """Test login with invalid password."""
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "WrongPassword"},
        )

        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with nonexistent user."""
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "nonexistent", "password": "password"},
        )

        assert response.status_code == 401


class TestGetMe:
    """Tests for the /me endpoint."""

    @pytest.mark.asyncio
    async def test_get_me_success(
        self, client: AsyncClient, test_user: dict, auth_headers: dict
    ):
        """Test getting current user profile."""
        response = await client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "testuser@example.com"
        assert data["role"] == "viewer"

    @pytest.mark.asyncio
    async def test_get_me_unauthorized(self, client: AsyncClient):
        """Test /me without authentication."""
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_invalid_token(self, client: AsyncClient):
        """Test /me with invalid token."""
        response = await client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer invalid-token"}
        )

        assert response.status_code == 401


class TestRegister:
    """Tests for user registration endpoint."""

    @pytest.mark.asyncio
    async def test_register_success(
        self, client: AsyncClient, test_admin: dict, admin_auth_headers: dict
    ):
        """Test successful user registration by admin."""
        response = await client.post(
            "/api/v1/auth/register",
            headers=admin_auth_headers,
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "NewPassword123!",
                "full_name": "New User",
                "role": "auditor",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert data["role"] == "auditor"

    @pytest.mark.asyncio
    async def test_register_non_admin_forbidden(
        self, client: AsyncClient, test_user: dict, auth_headers: dict
    ):
        """Test that non-admin cannot register users."""
        response = await client.post(
            "/api/v1/auth/register",
            headers=auth_headers,
            json={
                "username": "unauthorized",
                "email": "unauthorized@example.com",
                "password": "Password123!",
                "full_name": "Unauthorized User",
            },
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_register_duplicate_username(
        self, client: AsyncClient, test_admin: dict, admin_auth_headers: dict, test_user: dict
    ):
        """Test registration with duplicate username."""
        response = await client.post(
            "/api/v1/auth/register",
            headers=admin_auth_headers,
            json={
                "username": "testuser",  # Already exists
                "email": "different@example.com",
                "password": "Password123!",
                "full_name": "Duplicate User",
            },
        )

        assert response.status_code == 400


class TestChangePassword:
    """Tests for password change endpoint."""

    @pytest.mark.asyncio
    async def test_change_password_success(
        self, client: AsyncClient, test_user: dict, auth_headers: dict
    ):
        """Test successful password change."""
        response = await client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "TestPassword123!",
                "new_password": "NewSecurePassword456!",
            },
        )

        assert response.status_code == 200
        assert "Password changed successfully" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(
        self, client: AsyncClient, test_user: dict, auth_headers: dict
    ):
        """Test password change with wrong current password."""
        response = await client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "WrongPassword",
                "new_password": "NewPassword123!",
            },
        )

        assert response.status_code == 400
        assert "Current password is incorrect" in response.json()["detail"]


class TestListUsers:
    """Tests for user listing endpoint."""

    @pytest.mark.asyncio
    async def test_list_users_admin(
        self, client: AsyncClient, test_admin: dict, admin_auth_headers: dict, test_user: dict
    ):
        """Test that admin can list users."""
        response = await client.get("/api/v1/auth/users", headers=admin_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 2  # At least admin and test user

    @pytest.mark.asyncio
    async def test_list_users_non_admin_forbidden(
        self, client: AsyncClient, test_user: dict, auth_headers: dict
    ):
        """Test that non-admin cannot list users."""
        response = await client.get("/api/v1/auth/users", headers=auth_headers)

        assert response.status_code == 403


class TestUpdateUser:
    """Tests for user update endpoint."""

    @pytest.mark.asyncio
    async def test_update_user_success(
        self, client: AsyncClient, test_admin: dict, admin_auth_headers: dict, test_user: dict
    ):
        """Test successful user update by admin."""
        response = await client.patch(
            f"/api/v1/auth/users/{test_user['id']}",
            headers=admin_auth_headers,
            json={"full_name": "Updated Name", "department": "IT"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"
        assert data["department"] == "IT"

    @pytest.mark.asyncio
    async def test_update_user_not_found(
        self, client: AsyncClient, test_admin: dict, admin_auth_headers: dict
    ):
        """Test update nonexistent user."""
        response = await client.patch(
            "/api/v1/auth/users/00000000-0000-0000-0000-000000000000",
            headers=admin_auth_headers,
            json={"full_name": "New Name"},
        )

        assert response.status_code == 404


class TestDeactivateUser:
    """Tests for user deactivation endpoint."""

    @pytest.mark.asyncio
    async def test_deactivate_user_success(
        self, client: AsyncClient, test_admin: dict, admin_auth_headers: dict, db_session
    ):
        """Test successful user deactivation."""
        # Create a user to deactivate
        user = await create_test_user(
            db=db_session,
            username="todeactivate",
            email="todeactivate@example.com",
            password="Password123!",
            full_name="To Deactivate",
            role="viewer",
        )

        response = await client.delete(
            f"/api/v1/auth/users/{user['id']}", headers=admin_auth_headers
        )

        assert response.status_code == 200
        assert "deactivated" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_deactivate_self_forbidden(
        self, client: AsyncClient, test_admin: dict, admin_auth_headers: dict
    ):
        """Test that admin cannot deactivate themselves."""
        response = await client.delete(
            f"/api/v1/auth/users/{test_admin['id']}", headers=admin_auth_headers
        )

        assert response.status_code == 400
        assert "Cannot deactivate your own account" in response.json()["detail"]
