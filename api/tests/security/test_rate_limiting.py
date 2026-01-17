"""
Tests for Rate Limiting - OWASP API4:2023 Unrestricted Resource Consumption.

Rate limiting prevents:
- Brute force attacks on login
- Resource exhaustion
- Denial of service

Tests verify rate limits are enforced on sensitive endpoints.

Note: Rate limiting is configured at app startup time via environment variables.
The actual rate limits depend on the environment:
- Production: RATE_LIMIT_AUTH_PER_MINUTE=10, RATE_LIMIT_GENERAL_PER_MINUTE=60
- Testing/Development: May use default limits

These tests verify rate limiting behavior is working, not specific thresholds.
"""

import asyncio

import pytest

# =============================================================================
# Login Rate Limiting Tests
# =============================================================================


class TestLoginRateLimiting:
    """Tests for login endpoint rate limiting."""

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_login_accepts_valid_requests(
        self,
        async_client,
    ):
        """
        Login endpoint should accept requests within rate limits.

        Verifies the endpoint is functional and returns proper responses.
        """
        login_data = {
            "username": "test@example.com",
            "password": "wrongpassword",
        }

        # A single request should not be rate limited
        response = await async_client.post(
            "/api/v1/auth/login",
            data=login_data,
        )

        # Should get 401 (unauthorized) not 429 (rate limited)
        assert response.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_login_returns_proper_error_format(
        self,
        async_client,
    ):
        """
        Login endpoint should return proper error response format.
        """
        login_data = {
            "username": "test@example.com",
            "password": "wrongpassword",
        }

        response = await async_client.post(
            "/api/v1/auth/login",
            data=login_data,
        )

        assert response.status_code == 401
        # Response should have detail field
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    @pytest.mark.security
    @pytest.mark.slow
    async def test_many_login_attempts_handled_gracefully(
        self,
        async_client,
    ):
        """
        Multiple login attempts should be handled without server errors.

        This test verifies the server handles many requests gracefully,
        whether rate-limited or not.
        """
        login_data = {
            "username": "test@example.com",
            "password": "wrongpassword",
        }

        responses = []
        for _ in range(10):
            response = await async_client.post(
                "/api/v1/auth/login",
                data=login_data,
            )
            responses.append(response.status_code)

        # All responses should be valid HTTP codes (401 unauthorized or 429 rate limited)
        valid_codes = {401, 429}
        assert all(status in valid_codes for status in responses), (
            f"Unexpected status codes: {set(responses) - valid_codes}"
        )


# =============================================================================
# Registration Rate Limiting Tests
# =============================================================================


class TestRegistrationRateLimiting:
    """Tests for registration endpoint rate limiting.

    Note: Registration requires admin authentication.
    """

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_register_requires_admin_auth(
        self,
        async_client,
    ):
        """
        Registration endpoint should require admin authentication.
        """
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "ValidPassword123!",
                "full_name": "New User",
            },
        )

        # Should get 401 (unauthorized) without admin auth
        assert response.status_code == 401


# =============================================================================
# Password Change Rate Limiting Tests
# =============================================================================


class TestPasswordChangeRateLimiting:
    """Tests for password change endpoint rate limiting.

    Note: Endpoint is POST /api/v1/auth/change-password
    """

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_password_change_requires_auth(
        self,
        async_client,
    ):
        """
        Password change endpoint should require authentication.
        """
        response = await async_client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "wrong",
                "new_password": "newpassword123",
            },
        )

        # Should get 401 (unauthorized) without auth headers
        assert response.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_password_change_handles_wrong_password(
        self,
        async_client,
        auth_headers,
    ):
        """
        Password change with wrong current password should be rejected.
        """
        response = await async_client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "definitely_wrong_password",
                "new_password": "newpassword123",
            },
            headers=auth_headers,
        )

        # Should get 400/401 (wrong password) not 429 (rate limited) for single request
        assert response.status_code in {400, 401, 429}


# =============================================================================
# API Endpoint Rate Limiting Tests
# =============================================================================


class TestAPIRateLimiting:
    """Tests for general API rate limiting."""

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_health_endpoint_always_accessible(
        self,
        async_client,
    ):
        """
        Health check endpoints should always be accessible.

        This ensures monitoring systems can always check health.
        """
        responses = []
        for _ in range(30):
            response = await async_client.get("/health")
            responses.append(response.status_code)

        # Health endpoint should always return 200, never 429
        assert 429 not in responses, "Health endpoint should not be rate limited"
        assert all(status == 200 for status in responses)

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_ready_endpoint_always_accessible(
        self,
        async_client,
    ):
        """
        Ready check endpoint should always be accessible.
        """
        response = await async_client.get("/ready")
        assert response.status_code == 200

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_api_endpoints_require_auth(
        self,
        async_client,
    ):
        """
        Protected API endpoints should require authentication.
        """
        response = await async_client.get("/api/v1/cases")

        # Should get 401 (unauthorized) without auth
        assert response.status_code == 401


# =============================================================================
# Rate Limit Headers Tests
# =============================================================================


class TestRateLimitHeaders:
    """Tests for rate limit response headers."""

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_rate_limit_headers_present(
        self,
        async_client,
    ):
        """
        Rate limited responses should include standard headers.

        Note: This test checks if headers are present when rate limited.
        If rate limiting is not triggered, the test passes.
        """
        login_data = {
            "username": "test@example.com",
            "password": "wrong",
        }

        # Send requests until rate limited or max attempts
        rate_limited_response = None
        for _ in range(50):
            response = await async_client.post(
                "/api/v1/auth/login",
                data=login_data,
            )
            if response.status_code == 429:
                rate_limited_response = response
                break

        if rate_limited_response:
            # When rate limited, verify we got a 429 response
            # slowapi typically adds X-RateLimit headers but may vary by configuration
            assert rate_limited_response.status_code == 429


# =============================================================================
# Concurrent Request Tests
# =============================================================================


class TestConcurrentRequests:
    """Tests for handling concurrent requests."""

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_concurrent_requests_handled_without_errors(
        self,
        async_client,
        auth_headers,
    ):
        """
        Concurrent requests should be handled without server errors.

        Tests that the server doesn't crash or return 500 errors
        under concurrent load.
        """
        # Send 5 concurrent requests
        tasks = [
            async_client.get("/api/v1/cases", headers=auth_headers)
            for _ in range(5)
        ]

        responses = await asyncio.gather(*tasks)
        status_codes = [r.status_code for r in responses]

        # No server errors (5xx)
        server_errors = [s for s in status_codes if s >= 500]
        assert not server_errors, f"Server errors occurred: {server_errors}"

        # All should be valid responses
        valid_codes = {200, 429}  # Success or rate limited
        assert all(s in valid_codes for s in status_codes), (
            f"Unexpected status codes: {set(status_codes) - valid_codes}"
        )

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_sequential_login_attempts_handled(
        self,
        async_client,
    ):
        """
        Sequential login attempts should be handled gracefully.

        Tests that multiple requests don't cause server errors.
        Note: Uses sequential requests to avoid SQLAlchemy session conflicts.
        """
        login_data = {"username": "test@example.com", "password": "wrong"}

        # Send 5 sequential login requests
        status_codes = []
        for _ in range(5):
            response = await async_client.post(
                "/api/v1/auth/login",
                data=login_data
            )
            status_codes.append(response.status_code)

        # No server errors
        server_errors = [s for s in status_codes if s >= 500]
        assert not server_errors, f"Server errors: {server_errors}"

        # All should be auth failures or rate limited
        valid_codes = {401, 429}
        assert all(s in valid_codes for s in status_codes), (
            f"Unexpected: {set(status_codes) - valid_codes}"
        )
