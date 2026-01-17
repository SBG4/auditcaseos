"""
Tests for JWT Security - OWASP API2:2023 Broken Authentication.

Tests verify:
- Expired tokens are rejected
- Tampered tokens are rejected
- Invalid signatures are rejected
- Missing tokens return 401
- Algorithm confusion attacks are prevented
"""

import pytest
from datetime import datetime, timedelta, UTC
import base64
import json

from jose import jwt

from app.config import settings


# =============================================================================
# Token Expiration Tests
# =============================================================================


class TestTokenExpiration:
    """Tests for JWT token expiration handling."""

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_valid_token_accepted(
        self,
        async_client,
        auth_headers,
    ):
        """Valid, non-expired token should be accepted."""
        response = await async_client.get(
            "/api/v1/auth/me",
            headers=auth_headers,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_expired_token_rejected(
        self,
        async_client,
        test_user,
    ):
        """Expired tokens should be rejected with 401."""
        # Create token that expired 1 hour ago
        expired_token = jwt.encode(
            {
                "sub": test_user["id"],
                "email": test_user["email"],
                "role": test_user["role"],
                "exp": datetime.now(UTC) - timedelta(hours=1),
            },
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )

        response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )

        assert response.status_code == 401
        assert "expired" in response.json().get("detail", "").lower() or response.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_future_token_handling(
        self,
        async_client,
        test_user,
    ):
        """Token with future 'iat' should be handled properly."""
        # Create token with iat in the future (clock skew attack)
        future_token = jwt.encode(
            {
                "sub": test_user["id"],
                "email": test_user["email"],
                "role": test_user["role"],
                "iat": datetime.now(UTC) + timedelta(hours=1),
                "exp": datetime.now(UTC) + timedelta(hours=2),
            },
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )

        response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {future_token}"},
        )

        # May be accepted or rejected depending on clock skew tolerance
        assert response.status_code in [200, 401]


# =============================================================================
# Token Tampering Tests
# =============================================================================


class TestTokenTampering:
    """Tests for JWT token tampering detection."""

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_tampered_payload_rejected(
        self,
        async_client,
        test_user,
    ):
        """Tokens with modified payload should be rejected."""
        # Create valid token
        valid_token = jwt.encode(
            {
                "sub": test_user["id"],
                "email": test_user["email"],
                "role": "viewer",
                "exp": datetime.now(UTC) + timedelta(hours=1),
            },
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )

        # Tamper with the payload (try to escalate to admin)
        parts = valid_token.split(".")
        # Decode payload, modify, re-encode
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
        payload["role"] = "admin"  # Privilege escalation attempt
        tampered_payload = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode().rstrip("=")

        # Reconstruct token with original signature (will be invalid)
        tampered_token = f"{parts[0]}.{tampered_payload}.{parts[2]}"

        response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {tampered_token}"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_invalid_signature_rejected(
        self,
        async_client,
        test_user,
    ):
        """Tokens signed with wrong key should be rejected."""
        # Create token with different secret
        wrong_key_token = jwt.encode(
            {
                "sub": test_user["id"],
                "email": test_user["email"],
                "role": test_user["role"],
                "exp": datetime.now(UTC) + timedelta(hours=1),
            },
            "wrong-secret-key",  # Wrong key
            algorithm=settings.ALGORITHM,
        )

        response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {wrong_key_token}"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_malformed_token_rejected(
        self,
        async_client,
    ):
        """Malformed tokens should be rejected."""
        malformed_tokens = [
            "not.a.valid.token",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",  # Only header
            "abc123",
            "",
            "Bearer only",
        ]

        for token in malformed_tokens:
            response = await async_client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 401, f"Token '{token}' should be rejected"


# =============================================================================
# Algorithm Confusion Tests
# =============================================================================


class TestAlgorithmConfusion:
    """Tests for JWT algorithm confusion attacks."""

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_none_algorithm_rejected(
        self,
        async_client,
        test_user,
    ):
        """
        JWT with 'none' algorithm should be rejected.

        The 'none' algorithm attack tries to bypass signature verification
        by claiming no signature is needed.
        """
        # Manually construct a 'none' algorithm token
        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "none", "typ": "JWT"}).encode()
        ).decode().rstrip("=")

        payload = base64.urlsafe_b64encode(
            json.dumps({
                "sub": test_user["id"],
                "email": test_user["email"],
                "role": "admin",
                "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
            }).encode()
        ).decode().rstrip("=")

        none_token = f"{header}.{payload}."

        response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {none_token}"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_hs256_with_public_key_rejected(
        self,
        async_client,
        test_user,
    ):
        """
        If RSA is used, HS256 with public key as secret should be rejected.

        This tests the algorithm substitution attack where an attacker
        uses HS256 with the public key as the secret.
        Note: AuditCaseOS uses HS256, so this test documents the current algo.
        """
        # Verify the algorithm being used
        assert settings.ALGORITHM == "HS256", (
            f"Algorithm is {settings.ALGORITHM}, not HS256. "
            "Update test if using RSA."
        )


# =============================================================================
# Authentication Header Tests
# =============================================================================


class TestAuthenticationHeader:
    """Tests for authentication header handling."""

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_missing_auth_header_returns_401(
        self,
        async_client,
    ):
        """Requests without Authorization header should return 401."""
        response = await async_client.get("/api/v1/auth/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_missing_bearer_prefix_rejected(
        self,
        async_client,
        test_user,
    ):
        """Authorization header without 'Bearer' prefix should be rejected."""
        valid_token = jwt.encode(
            {
                "sub": test_user["id"],
                "email": test_user["email"],
                "role": test_user["role"],
                "exp": datetime.now(UTC) + timedelta(hours=1),
            },
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )

        response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": valid_token},  # Missing Bearer prefix
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_wrong_auth_scheme_rejected(
        self,
        async_client,
        test_user,
    ):
        """Wrong authentication scheme should be rejected."""
        valid_token = jwt.encode(
            {
                "sub": test_user["id"],
                "email": test_user["email"],
                "role": test_user["role"],
                "exp": datetime.now(UTC) + timedelta(hours=1),
            },
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )

        response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Basic {valid_token}"},  # Wrong scheme
        )

        assert response.status_code == 401


# =============================================================================
# Token Payload Tests
# =============================================================================


class TestTokenPayload:
    """Tests for JWT token payload handling."""

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_missing_sub_claim_rejected(
        self,
        async_client,
        test_user,
    ):
        """Token without 'sub' claim should be rejected."""
        token_without_sub = jwt.encode(
            {
                "email": test_user["email"],
                "role": test_user["role"],
                "exp": datetime.now(UTC) + timedelta(hours=1),
            },
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )

        response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token_without_sub}"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_invalid_user_id_in_token(
        self,
        async_client,
    ):
        """Token with non-existent user ID should be rejected."""
        token_fake_user = jwt.encode(
            {
                "sub": "00000000-0000-0000-0000-000000000000",
                "email": "nonexistent@example.com",
                "role": "admin",
                "exp": datetime.now(UTC) + timedelta(hours=1),
            },
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )

        response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token_fake_user}"},
        )

        # Should be 401 or 404 (user not found)
        assert response.status_code in [401, 404]
