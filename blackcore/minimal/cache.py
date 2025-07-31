"""Simple file-based cache for transcript processing."""

import json
import time
import os
import platform
from pathlib import Path
from typing import Any, Optional, Dict
import hashlib

from . import constants
from .logging_config import get_logger, log_event, log_error
from .error_handling import ErrorHandler, ProcessingError, handle_errors

logger = get_logger(__name__)


class SimpleCache:
    """Simple file-based cache with TTL support."""

    def __init__(self, cache_dir: Optional[str] = None, ttl: int = constants.DEFAULT_CACHE_TTL):
        """Initialize cache.

        Args:
            cache_dir: Directory to store cache files (default: ~/.blackcore_cache)
            ttl: Time to live in seconds (default 1 hour)
        """
        if cache_dir is None:
            # Use default directory in user home
            self.cache_dir = Path.home() / ".blackcore_cache"
        else:
            self.cache_dir = Path(cache_dir)
        
        self.ttl = ttl

        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(exist_ok=True)
        
        # Set restricted permissions on cache directory
        self._set_directory_permissions(str(self.cache_dir))

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        cache_file = self._get_cache_file(key)

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "r") as f:
                cache_data = json.load(f)

            # Check if expired
            if time.time() - cache_data["timestamp"] > self.ttl:
                # Expired - remove file
                cache_file.unlink()
                return None

            log_event(
                __name__,
                "cache_hit",
                key=key,
                cache_file=str(cache_file),
                age_seconds=time.time() - cache_data["timestamp"]
            )
            return cache_data["value"]

        except (json.JSONDecodeError, KeyError, IOError) as e:
            # Corrupted cache file - remove it
            cache_error = ProcessingError(
                f"Cache file corrupted for key '{key}'",
                context={
                    "key": key,
                    "cache_file": str(cache_file),
                    "original_error": type(e).__name__
                }
            )
            log_error(
                __name__,
                "cache_corrupted",
                cache_error,
                key=key,
                cache_file=str(cache_file)
            )
            cache_file.unlink(missing_ok=True)
            return None

    def set(self, key: str, value: Any) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
        """
        cache_file = self._get_cache_file(key)

        cache_data = {"timestamp": time.time(), "value": value}

        try:
            with open(cache_file, "w") as f:
                json.dump(cache_data, f, indent=2, default=str)
            
            # Set restricted permissions on the cache file
            self._set_file_permissions(str(cache_file))
            
            log_event(
                __name__,
                "cache_set",
                key=key,
                cache_file=str(cache_file),
                value_size=len(json.dumps(value, default=str))
            )
        except (TypeError, IOError) as e:
            cache_error = ProcessingError(
                f"Failed to write cache for key '{key}'",
                context={
                    "key": key,
                    "cache_file": str(cache_file),
                    "original_error": type(e).__name__
                }
            )
            log_error(
                __name__,
                "cache_write_failed",
                cache_error,
                key=key,
                cache_file=str(cache_file)
            )

    def delete(self, key: str) -> None:
        """Delete value from cache.

        Args:
            key: Cache key
        """
        cache_file = self._get_cache_file(key)
        cache_file.unlink(missing_ok=True)

    def clear(self) -> None:
        """Clear all cache files."""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()

    def cleanup_expired(self) -> int:
        """Remove expired cache entries.

        Returns:
            Number of entries removed
        """
        removed = 0
        current_time = time.time()

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, "r") as f:
                    cache_data = json.load(f)

                if current_time - cache_data["timestamp"] > self.ttl:
                    cache_file.unlink()
                    removed += 1

            except (json.JSONDecodeError, KeyError, IOError):
                # Corrupted file - remove it
                cache_file.unlink(missing_ok=True)
                removed += 1

        return removed

    def _get_cache_file(self, key: str) -> Path:
        """Get cache file path for a key.

        Args:
            key: Cache key

        Returns:
            Path to cache file
        """
        # Hash the key to create a valid filename
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with cache stats
        """
        total_files = 0
        total_size = 0
        expired_count = 0
        current_time = time.time()

        for cache_file in self.cache_dir.glob("*.json"):
            total_files += 1
            total_size += cache_file.stat().st_size

            try:
                with open(cache_file, "r") as f:
                    cache_data = json.load(f)

                if current_time - cache_data["timestamp"] > self.ttl:
                    expired_count += 1

            except (json.JSONDecodeError, KeyError, IOError):
                expired_count += 1

        return {
            "total_entries": total_files,
            "total_size_bytes": total_size,
            "expired_entries": expired_count,
            "active_entries": total_files - expired_count,
            "cache_directory": str(self.cache_dir.absolute()),
        }
    
    def _set_directory_permissions(self, directory: str) -> None:
        """Set restrictive permissions on directory.
        
        Args:
            directory: Directory path to secure
        """
        # Skip on Windows as it handles permissions differently
        if platform.system() == 'Windows':
            return
        
        try:
            # Set directory permissions to 0o700 (rwx------)
            # Only owner can read, write, and execute
            os.chmod(directory, constants.CACHE_DIR_PERMISSIONS)
        except (OSError, PermissionError) as e:
            logger.warning(f"Failed to set cache directory permissions: {e}")
    
    def _set_file_permissions(self, filepath: str) -> None:
        """Set restrictive permissions on file.
        
        Args:
            filepath: File path to secure
        """
        # Skip on Windows as it handles permissions differently
        if platform.system() == 'Windows':
            return
        
        try:
            # Set file permissions to 0o600 (rw-------)
            # Only owner can read and write
            os.chmod(filepath, constants.CACHE_FILE_PERMISSIONS)
        except (OSError, PermissionError) as e:
            logger.warning(f"Failed to set cache file permissions: {e}")
