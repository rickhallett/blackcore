"""Validators for API keys and other security-sensitive inputs."""

import re
from typing import Optional


def validate_api_key(key: Optional[str], provider: str) -> bool:
    """Validate API key format for different providers.
    
    Args:
        key: The API key to validate
        provider: The provider name (notion, anthropic, openai, etc.)
        
    Returns:
        True if the key is valid for the provider, False otherwise
    """
    if not key or not isinstance(key, str):
        return False
    
    # Normalize provider name to lowercase
    provider = provider.lower()
    
    # Define validation patterns for each provider
    patterns = {
        "notion": r"^secret_[a-zA-Z0-9]{43}$",
        "anthropic": r"^sk-ant-[a-zA-Z0-9-]{95}$",
        "openai": r"^sk-[a-zA-Z0-9]{48}$",
    }
    
    # Get pattern for provider
    pattern = patterns.get(provider)
    
    if pattern:
        # Use regex to validate
        return bool(re.match(pattern, key))
    else:
        # For unknown providers, just check that key is non-empty
        return len(key) > 0


def validate_database_id(database_id: str) -> bool:
    """Validate Notion database ID format.
    
    Args:
        database_id: The database ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not database_id or not isinstance(database_id, str):
        return False
    
    # Remove hyphens for validation
    clean_id = database_id.replace("-", "")
    
    # Should be 32 hex characters
    if len(clean_id) != 32:
        return False
    
    # Check if all characters are hex
    try:
        int(clean_id, 16)
        return True
    except ValueError:
        return False


def validate_page_id(page_id: str) -> bool:
    """Validate Notion page ID format.
    
    Args:
        page_id: The page ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    # Page IDs have the same format as database IDs
    return validate_database_id(page_id)


def sanitize_property_name(name: str) -> str:
    """Sanitize property name for safe use.
    
    Args:
        name: The property name to sanitize
        
    Returns:
        Sanitized property name
    """
    if not name:
        return ""
    
    # Remove any control characters
    sanitized = "".join(char for char in name if ord(char) >= 32)
    
    # Limit length
    max_length = 100
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized


def validate_url(url: str) -> bool:
    """Validate URL format.
    
    Args:
        url: The URL to validate
        
    Returns:
        True if valid URL, False otherwise
    """
    if not url or not isinstance(url, str):
        return False
    
    # Basic URL pattern
    url_pattern = r"^https?://[^\s<>\"{}|\\^`\[\]]+$"
    
    return bool(re.match(url_pattern, url))