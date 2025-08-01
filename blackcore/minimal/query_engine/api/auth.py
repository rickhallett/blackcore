"""Authentication and authorization for the Query Engine API."""

from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
import time
import asyncio
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()


class RateLimiter:
    """Simple in-memory rate limiter for API keys."""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def check_limit(self, api_key: str) -> bool:
        """Check if API key has exceeded rate limit.
        
        Returns:
            True if request is allowed, False if rate limited
        """
        async with self._lock:
            now = time.time()
            minute_ago = now - 60
            
            # Clean old requests
            self.requests[api_key] = [
                req_time for req_time in self.requests[api_key]
                if req_time > minute_ago
            ]
            
            # Check limit
            if len(self.requests[api_key]) >= self.requests_per_minute:
                return False
            
            # Record request
            self.requests[api_key].append(now)
            return True
    
    def get_usage(self, api_key: str) -> Dict[str, Any]:
        """Get current usage statistics for an API key."""
        now = time.time()
        minute_ago = now - 60
        
        recent_requests = [
            req_time for req_time in self.requests[api_key]
            if req_time > minute_ago
        ]
        
        return {
            "requests_used": len(recent_requests),
            "requests_limit": self.requests_per_minute,
            "reset_time": now + 60
        }


class APIKeyValidator:
    """Validates API keys for authentication."""
    
    def __init__(self):
        # In production, this would check against a database
        # For now, using a simple in-memory store
        self.valid_keys = {
            "test-api-key": {
                "name": "Test User",
                "scopes": ["read", "write"],
                "rate_limit": 60
            },
            "admin-api-key": {
                "name": "Admin User",
                "scopes": ["read", "write", "admin"],
                "rate_limit": 600
            }
        }
    
    async def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Validate an API key and return user info if valid."""
        return self.valid_keys.get(api_key)
    
    def has_scope(self, api_key_info: Dict[str, Any], required_scope: str) -> bool:
        """Check if API key has required scope."""
        return required_scope in api_key_info.get("scopes", [])


# Global instances
api_key_validator = APIKeyValidator()
rate_limiter = RateLimiter()


async def get_current_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> str:
    """Extract and validate API key from Bearer token."""
    api_key = credentials.credentials
    
    # Validate API key
    key_info = await api_key_validator.validate_api_key(api_key)
    if not key_info:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return api_key


async def require_scope(required_scope: str):
    """Dependency to require a specific scope."""
    async def scope_checker(api_key: str = Depends(get_current_api_key)):
        key_info = await api_key_validator.validate_api_key(api_key)
        if not api_key_validator.has_scope(key_info, required_scope):
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required scope: {required_scope}"
            )
        return api_key
    
    return scope_checker


# Convenience dependencies
require_read = Depends(require_scope("read"))
require_write = Depends(require_scope("write"))
require_admin = Depends(require_scope("admin"))