"""Tests for cache module."""

import pytest
import time
from pathlib import Path
import tempfile
import shutil
from datetime import datetime

from ..cache import SimpleCache


class TestSimpleCache:
    """Test simple file-based cache."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def cache(self, temp_cache_dir):
        """Create cache instance with temp directory."""
        return SimpleCache(cache_dir=temp_cache_dir, ttl=3600)

    def test_cache_init(self, temp_cache_dir):
        """Test cache initialization."""
        cache = SimpleCache(cache_dir=temp_cache_dir, ttl=7200)

        assert cache.ttl == 7200
        assert cache.cache_dir == Path(temp_cache_dir)
        assert cache.cache_dir.exists()

    def test_set_and_get(self, cache):
        """Test setting and getting values."""
        # Set value
        cache.set("test_key", {"data": "test_value", "number": 42})

        # Get value
        value = cache.get("test_key")
        assert value is not None
        assert value["data"] == "test_value"
        assert value["number"] == 42

    def test_get_nonexistent(self, cache):
        """Test getting non-existent key."""
        value = cache.get("nonexistent_key")
        assert value is None

    def test_ttl_expiration(self, cache):
        """Test TTL expiration."""
        # Create cache with short TTL
        short_cache = SimpleCache(cache_dir=cache.cache_dir, ttl=1)

        # Set value
        short_cache.set("expire_test", "value")

        # Should exist immediately
        assert short_cache.get("expire_test") == "value"

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired
        assert short_cache.get("expire_test") is None

    def test_delete(self, cache):
        """Test deleting cache entries."""
        # Set value
        cache.set("delete_test", "value")
        assert cache.get("delete_test") == "value"

        # Delete
        cache.delete("delete_test")
        assert cache.get("delete_test") is None

        # Delete non-existent (should not raise)
        cache.delete("nonexistent")

    def test_clear(self, cache):
        """Test clearing all cache."""
        # Set multiple values
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Verify they exist
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"

        # Clear all
        cache.clear()

        # Verify all gone
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None

    def test_cleanup_expired(self, cache):
        """Test cleanup of expired entries."""
        # Create mix of expired and valid entries
        short_cache = SimpleCache(cache_dir=cache.cache_dir, ttl=1)

        short_cache.set("expired1", "value1")
        short_cache.set("expired2", "value2")

        # Wait for expiration
        time.sleep(1.1)

        # Add fresh entries
        short_cache.set("fresh1", "value3")
        short_cache.set("fresh2", "value4")

        # Cleanup
        removed = short_cache.cleanup_expired()

        assert removed == 2
        assert short_cache.get("fresh1") == "value3"
        assert short_cache.get("fresh2") == "value4"

    def test_cache_file_corruption(self, cache):
        """Test handling of corrupted cache files."""
        # Set valid value
        cache.set("corrupt_test", "value")

        # Corrupt the cache file
        cache_file = cache._get_cache_file("corrupt_test")
        with open(cache_file, "w") as f:
            f.write("not valid json")

        # Should return None and remove corrupted file
        assert cache.get("corrupt_test") is None
        assert not cache_file.exists()

    def test_get_stats(self, cache):
        """Test cache statistics."""
        # Add some entries
        cache.set("key1", "value1")
        cache.set("key2", {"data": "value2"})
        cache.set("key3", [1, 2, 3])

        stats = cache.get_stats()

        assert stats["total_entries"] == 3
        assert stats["active_entries"] == 3
        assert stats["expired_entries"] == 0
        assert stats["total_size_bytes"] > 0
        assert str(cache.cache_dir.absolute()) in stats["cache_directory"]

    def test_complex_data_types(self, cache):
        """Test caching various data types."""
        test_data = {
            "string": "test",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "list": [1, 2, 3],
            "nested": {"key": "value", "list": ["a", "b", "c"]},
            "datetime": datetime(2025, 1, 9, 12, 0, 0),  # Will be converted to string
        }

        cache.set("complex", test_data)
        retrieved = cache.get("complex")

        assert retrieved["string"] == "test"
        assert retrieved["number"] == 42
        assert retrieved["float"] == 3.14
        assert retrieved["boolean"] is True
        assert retrieved["null"] is None
        assert retrieved["list"] == [1, 2, 3]
        assert retrieved["nested"]["key"] == "value"
        # Datetime converted to string
        assert "2025-01-09" in retrieved["datetime"]

    def test_cache_key_hashing(self, cache):
        """Test that cache keys are hashed consistently."""
        # Same key should produce same file
        file1 = cache._get_cache_file("test_key")
        file2 = cache._get_cache_file("test_key")
        assert file1 == file2

        # Different keys should produce different files
        file3 = cache._get_cache_file("different_key")
        assert file1 != file3

        # Long keys should work
        long_key = "a" * 1000
        file4 = cache._get_cache_file(long_key)
        assert file4.name.endswith(".json")
