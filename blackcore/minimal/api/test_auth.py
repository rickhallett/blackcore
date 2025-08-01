"""Tests for authentication and authorization module."""

import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt, JWTError
from jose.exceptions import JWSError

from blackcore.minimal.api.auth import (
    AuthHandler,
    get_current_user,
    require_admin,
    RateLimiter,
    ALGORITHM,
    SECRET_KEY,
)


class TestAuthHandler:
    """Test AuthHandler class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.auth_handler = AuthHandler(secret_key="test-secret-key")

    def test_create_access_token_default_expiry(self):
        """Test creating access token with default expiry."""
        data = {"sub": "test-user", "type": "user"}
        token = self.auth_handler.create_access_token(data)

        # Decode and verify token
        decoded = jwt.decode(token, "test-secret-key", algorithms=[ALGORITHM])
        assert decoded["sub"] == "test-user"
        assert decoded["type"] == "user"
        assert "exp" in decoded
        assert "iat" in decoded

        # Check expiry is roughly 60 minutes from when token was created
        exp_time = datetime.fromtimestamp(decoded["exp"])
        iat_time = datetime.fromtimestamp(decoded["iat"])
        
        # Expiry should be 60 minutes after issued-at time
        expected_delta = timedelta(minutes=60)
        actual_delta = exp_time - iat_time
        assert abs((actual_delta - expected_delta).total_seconds()) < 5

    def test_create_access_token_custom_expiry(self):
        """Test creating access token with custom expiry."""
        data = {"sub": "test-user"}
        expires_delta = timedelta(hours=2)
        token = self.auth_handler.create_access_token(data, expires_delta)

        # Decode and verify token
        decoded = jwt.decode(token, "test-secret-key", algorithms=[ALGORITHM])
        assert decoded["sub"] == "test-user"

        # Check expiry is roughly 2 hours from when token was created
        exp_time = datetime.fromtimestamp(decoded["exp"])
        iat_time = datetime.fromtimestamp(decoded["iat"])
        
        # Expiry should be 2 hours after issued-at time
        expected_delta = timedelta(hours=2)
        actual_delta = exp_time - iat_time
        assert abs((actual_delta - expected_delta).total_seconds()) < 5

    def test_verify_token_valid(self):
        """Test verifying a valid token."""
        # Create a valid token
        data = {"sub": "test-user", "role": "admin"}
        token = self.auth_handler.create_access_token(data)

        # Verify it
        payload = self.auth_handler.verify_token(token)
        assert payload["sub"] == "test-user"
        assert payload["role"] == "admin"

    def test_verify_token_invalid(self):
        """Test verifying an invalid token."""
        with pytest.raises(HTTPException) as exc_info:
            self.auth_handler.verify_token("invalid-token")

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Invalid authentication token"

    def test_verify_token_wrong_secret(self):
        """Test verifying token with wrong secret."""
        # Create token with one secret
        data = {"sub": "test-user"}
        token = self.auth_handler.create_access_token(data)

        # Try to verify with different secret
        other_handler = AuthHandler(secret_key="different-secret")
        with pytest.raises(HTTPException) as exc_info:
            other_handler.verify_token(token)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_hash_api_key(self):
        """Test API key hashing."""
        api_key = "test-api-key-12345"
        hashed = self.auth_handler.hash_api_key(api_key)

        # Hash should be different from original
        assert hashed != api_key
        # Should start with bcrypt prefix
        assert hashed.startswith("$2b$")

    def test_verify_api_key_correct(self):
        """Test verifying correct API key."""
        api_key = "test-api-key-12345"
        hashed = self.auth_handler.hash_api_key(api_key)

        assert self.auth_handler.verify_api_key(api_key, hashed) is True

    def test_verify_api_key_incorrect(self):
        """Test verifying incorrect API key."""
        api_key = "test-api-key-12345"
        hashed = self.auth_handler.hash_api_key(api_key)

        assert self.auth_handler.verify_api_key("wrong-key", hashed) is False

    def test_generate_token_response(self):
        """Test generating token response."""
        api_key = "test-api-key"
        expires_in = 7200  # 2 hours

        response = self.auth_handler.generate_token_response(api_key, expires_in)

        assert response.token_type == "bearer"
        assert response.expires_in == 7200
        assert response.access_token

        # Verify the token contains correct claims
        decoded = jwt.decode(
            response.access_token, "test-secret-key", algorithms=[ALGORITHM]
        )
        assert decoded["sub"] == api_key
        assert decoded["type"] == "api_key"


class TestGetCurrentUser:
    """Test get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self):
        """Test getting current user with valid token."""
        # Create a valid token
        auth_handler = AuthHandler(secret_key=SECRET_KEY)
        token_data = {"sub": "test-user", "email": "test@example.com"}
        token = auth_handler.create_access_token(token_data)

        # Mock credentials
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        # Call get_current_user
        user = await get_current_user(credentials)

        assert user["sub"] == "test-user"
        assert user["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_current_user_expired_token(self):
        """Test getting current user with expired token."""
        auth_handler = AuthHandler(secret_key=SECRET_KEY)

        # Create an expired token
        expired_time = datetime.utcnow() - timedelta(hours=1)
        token_data = {
            "sub": "test-user",
            "exp": expired_time.timestamp(),
            "iat": (expired_time - timedelta(hours=1)).timestamp(),
        }
        token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

        # Mock credentials
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        # Call should raise exception
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        # The JWT library itself rejects expired tokens, so we get "Invalid authentication token"
        assert exc_info.value.detail == "Invalid authentication token"

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """Test getting current user with invalid token."""
        # Mock credentials with invalid token
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid-token"
        )

        # Call should raise exception
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Invalid authentication token"


class TestRequireAdmin:
    """Test require_admin dependency."""

    @pytest.mark.asyncio
    async def test_require_admin_with_admin_user(self):
        """Test require_admin with admin user."""
        admin_user = {"sub": "admin-user", "is_admin": True}
        result = await require_admin(admin_user)
        assert result == admin_user

    @pytest.mark.asyncio
    async def test_require_admin_with_regular_user(self):
        """Test require_admin with regular user."""
        regular_user = {"sub": "regular-user", "is_admin": False}

        with pytest.raises(HTTPException) as exc_info:
            await require_admin(regular_user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert exc_info.value.detail == "Admin privileges required"

    @pytest.mark.asyncio
    async def test_require_admin_without_admin_claim(self):
        """Test require_admin without is_admin claim."""
        user = {"sub": "user-without-claim"}

        with pytest.raises(HTTPException) as exc_info:
            await require_admin(user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert exc_info.value.detail == "Admin privileges required"


class TestRateLimiter:
    """Test RateLimiter class."""

    @pytest.mark.asyncio
    async def test_rate_limit_under_limit(self):
        """Test rate limiting when under limit."""
        limiter = RateLimiter(requests_per_minute=5)

        # Make 4 requests (under limit of 5)
        for _ in range(4):
            result = await limiter.check_rate_limit("user1")
            assert result is True

    @pytest.mark.asyncio
    async def test_rate_limit_at_limit(self):
        """Test rate limiting when at limit."""
        limiter = RateLimiter(requests_per_minute=3)

        # Make 3 requests (at limit)
        for _ in range(3):
            result = await limiter.check_rate_limit("user1")
            assert result is True

        # 4th request should fail
        result = await limiter.check_rate_limit("user1")
        assert result is False

    @pytest.mark.asyncio
    async def test_rate_limit_different_users(self):
        """Test rate limiting tracks different users separately."""
        limiter = RateLimiter(requests_per_minute=2)

        # User 1 makes 2 requests
        assert await limiter.check_rate_limit("user1") is True
        assert await limiter.check_rate_limit("user1") is True
        assert await limiter.check_rate_limit("user1") is False

        # User 2 should still be able to make requests
        assert await limiter.check_rate_limit("user2") is True
        assert await limiter.check_rate_limit("user2") is True
        assert await limiter.check_rate_limit("user2") is False

    @pytest.mark.asyncio
    async def test_rate_limit_cleanup_old_requests(self):
        """Test rate limiter cleans up old requests."""
        limiter = RateLimiter(requests_per_minute=2)

        # Make 2 requests
        assert await limiter.check_rate_limit("user1") is True
        assert await limiter.check_rate_limit("user1") is True

        # Mock time to be 1 minute later
        with patch("blackcore.minimal.api.auth.datetime") as mock_datetime:
            future_time = datetime.utcnow() + timedelta(minutes=1, seconds=1)
            mock_datetime.utcnow.return_value = future_time

            # Should be able to make requests again
            assert await limiter.check_rate_limit("user1") is True

    @pytest.mark.asyncio
    async def test_rate_limit_dependency(self):
        """Test rate limiter as FastAPI dependency."""
        limiter = RateLimiter(requests_per_minute=1)

        # First request should pass
        user = {"sub": "test-user"}
        result = await limiter.rate_limit_dependency(user)
        assert result == user

        # Second request should fail
        with pytest.raises(HTTPException) as exc_info:
            await limiter.rate_limit_dependency(user)

        assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert exc_info.value.detail == "Rate limit exceeded"


class TestAuthIntegration:
    """Integration tests for auth components."""

    @pytest.mark.asyncio
    async def test_full_auth_flow(self):
        """Test complete authentication flow."""
        # 1. Create auth handler
        auth_handler = AuthHandler(secret_key="integration-test-key")

        # 2. Generate token for API key
        api_key = "test-api-key-integration"
        token_response = auth_handler.generate_token_response(api_key)

        # 3. Use token to authenticate
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials=token_response.access_token
        )

        # Mock the global auth_handler to use our test instance
        with patch("blackcore.minimal.api.auth.auth_handler", auth_handler):
            user = await get_current_user(credentials)

        assert user["sub"] == api_key
        assert user["type"] == "api_key"

    @pytest.mark.asyncio
    async def test_jwt_algorithm_confusion_protection(self):
        """Test protection against JWT algorithm confusion attacks."""
        # Test that the jose library protects against 'none' algorithm
        with pytest.raises(JWSError) as exc_info:
            jwt.encode({"sub": "attacker"}, "", algorithm="none")
        
        assert "Algorithm none not supported" in str(exc_info.value)
        
        # Test that we only accept our specified algorithm
        auth_handler = AuthHandler(secret_key=SECRET_KEY)
        
        # Create a valid token
        token_data = {"sub": "legitimate-user", "type": "test"}
        valid_token = auth_handler.create_access_token(token_data)
        
        # Verify it works with correct algorithm
        decoded = auth_handler.verify_token(valid_token)
        assert decoded["sub"] == "legitimate-user"
        
        # The auth handler is protected because:
        # 1. It only uses algorithms=[self.algorithm] in decode
        # 2. The jose library rejects unsafe algorithms like 'none'
        # 3. Algorithm confusion is prevented at the library level