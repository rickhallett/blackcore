"""Authentication and authorization for the API."""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

from .models import TokenResponse


# Security settings
SECRET_KEY = os.getenv("API_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token scheme
bearer_scheme = HTTPBearer()


class AuthHandler:
    """Handle authentication and JWT operations."""

    def __init__(self, secret_key: str = SECRET_KEY):
        self.secret_key = secret_key
        self.algorithm = ALGORITHM

    def create_access_token(
        self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire, "iat": datetime.utcnow()})

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

        return encoded_jwt

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload

        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def hash_api_key(self, api_key: str) -> str:
        """Hash an API key for storage."""
        return pwd_context.hash(api_key)

    def verify_api_key(self, plain_api_key: str, hashed_api_key: str) -> bool:
        """Verify an API key against its hash."""
        return pwd_context.verify(plain_api_key, hashed_api_key)

    def generate_token_response(self, api_key: str, expires_in: int = 3600) -> TokenResponse:
        """Generate a token response for an API key."""
        # In production, verify API key against database
        # For now, we'll create a token with basic claims

        access_token = self.create_access_token(
            data={"sub": api_key, "type": "api_key"}, expires_delta=timedelta(seconds=expires_in)
        )

        return TokenResponse(access_token=access_token, token_type="bearer", expires_in=expires_in)


# Global auth handler instance
auth_handler = AuthHandler()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> Dict[str, Any]:
    """Dependency to get the current authenticated user from JWT."""
    token = credentials.credentials

    try:
        payload = auth_handler.verify_token(token)

        # Check if token is expired
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return payload

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_admin(
    current_user: Dict[str, Any] = Security(get_current_user),
) -> Dict[str, Any]:
    """Dependency to require admin privileges."""
    # In production, check user roles from database
    # For now, we'll check for a specific claim

    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )

    return current_user


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list] = {}

    async def check_rate_limit(self, identifier: str) -> bool:
        """Check if the identifier has exceeded rate limit."""
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)

        if identifier not in self.requests:
            self.requests[identifier] = []

        # Clean old requests
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier] if req_time > minute_ago
        ]

        # Check limit
        if len(self.requests[identifier]) >= self.requests_per_minute:
            return False

        # Add current request
        self.requests[identifier].append(now)
        return True

    async def rate_limit_dependency(
        self, current_user: Dict[str, Any] = Security(get_current_user)
    ) -> Dict[str, Any]:
        """FastAPI dependency for rate limiting."""
        identifier = current_user.get("sub", "unknown")

        if not await self.check_rate_limit(identifier):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded"
            )

        return current_user


# Global rate limiter instance
rate_limiter = RateLimiter()
