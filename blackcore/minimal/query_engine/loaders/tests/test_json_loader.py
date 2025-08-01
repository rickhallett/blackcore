"""Comprehensive tests for JSONDataLoader with performance benchmarks."""

import json
import time
from pathlib import Path
import tempfile
import pytest
from unittest.mock import Mock, patch
import random
import string
from typing import List, Dict, Any

from blackcore.minimal.query_engine.loaders import JSONDataLoader
from blackcore.minimal.query_engine.models import QueryError


class TestJSONDataLoader:
    """Test suite for JSONDataLoader."""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary directory with test data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)
            
            # Create test databases
            self._create_test_database(cache_dir, "test_small", 100)
            self._create_test_database(cache_dir, "test_medium", 1000)
            self._create_test_database(cache_dir, "test_large", 10000)
            self._create_test_database(cache_dir, "test_nested", 50, nested=True)
            
            # Create database with items wrapper
            items_data = {"items": self._generate_records(25)}
            with open(cache_dir / "test_items.json", 'w') as f:
                json.dump(items_data, f)
            
            yield cache_dir
    
    def _create_test_database(self, cache_dir: Path, name: str, record_count: int, nested: bool = False):
        """Create a test database file."""
        records = self._generate_records(record_count, nested)
        with open(cache_dir / f"{name}.json", 'w') as f:
            json.dump(records, f)
    
    def _generate_records(self, count: int, nested: bool = False) -> List[Dict[str, Any]]:
        """Generate test records."""
        records = []
        for i in range(count):
            record = {
                "id": f"id_{i}",
                "name": f"Test Item {i}",
                "value": random.randint(1, 1000),
                "active": random.choice([True, False]),
                "tags": [f"tag_{j}" for j in range(random.randint(1, 5))],
                "created_at": f"2024-01-{(i % 28) + 1:02d}T00:00:00Z"
            }
            
            if nested:
                record["metadata"] = {
                    "category": random.choice(["A", "B", "C"]),
                    "priority": random.randint(1, 5),
                    "details": {
                        "description": f"Description for item {i}",
                        "notes": [f"Note {k}" for k in range(3)]
                    }
                }
            
            records.append(record)
        
        return records
    
    def test_initialization(self, temp_cache_dir):
        """Test loader initialization."""
        loader = JSONDataLoader(str(temp_cache_dir))
        assert loader.cache_dir == temp_cache_dir
        assert loader.enable_mmap is True
        assert loader.max_workers == 4
        
        # Test with non-existent directory
        with pytest.raises(QueryError) as exc_info:
            JSONDataLoader("/non/existent/path")
        assert "Cache directory does not exist" in str(exc_info.value)
    
    def test_load_database(self, temp_cache_dir):
        """Test basic database loading."""
        loader = JSONDataLoader(str(temp_cache_dir))
        
        # Load small database
        data = loader.load_database("test_small")
        assert len(data) == 100
        assert all(isinstance(record, dict) for record in data)
        assert data[0]["id"] == "id_0"
        
        # Test caching - second load should be faster
        start_time = time.time()
        data2 = loader.load_database("test_small")
        cached_time = time.time() - start_time
        assert cached_time < 0.001  # Should be instant from cache
        assert data2 is data  # Should be same object
    
    def test_load_database_with_items_wrapper(self, temp_cache_dir):
        """Test loading database with items wrapper structure."""
        loader = JSONDataLoader(str(temp_cache_dir))
        
        data = loader.load_database("test_items")
        assert len(data) == 25
        assert all(isinstance(record, dict) for record in data)
    
    def test_load_nonexistent_database(self, temp_cache_dir):
        """Test loading non-existent database."""
        loader = JSONDataLoader(str(temp_cache_dir))
        
        with pytest.raises(QueryError) as exc_info:
            loader.load_database("nonexistent")
        assert "Database not found: nonexistent" in str(exc_info.value)
    
    def test_get_available_databases(self, temp_cache_dir):
        """Test getting list of available databases."""
        loader = JSONDataLoader(str(temp_cache_dir))
        
        databases = loader.get_available_databases()
        assert sorted(databases) == [
            "test_items", "test_large", "test_medium", 
            "test_nested", "test_small"
        ]
    
    def test_refresh_cache(self, temp_cache_dir):
        """Test cache refresh functionality."""
        loader = JSONDataLoader(str(temp_cache_dir))
        
        # Load and cache data
        data1 = loader.load_database("test_small")
        assert "test_small" in loader._cache
        
        # Refresh specific database
        loader.refresh_cache("test_small")
        assert "test_small" not in loader._cache
        
        # Load again
        data2 = loader.load_database("test_small")
        assert data2 is not data1  # Different object after refresh
        
        # Refresh all
        loader.load_database("test_medium")
        assert len(loader._cache) == 2
        loader.refresh_cache()
        assert len(loader._cache) == 0
    
    def test_load_multiple_databases(self, temp_cache_dir):
        """Test concurrent loading of multiple databases."""
        loader = JSONDataLoader(str(temp_cache_dir), max_workers=2)
        
        databases = ["test_small", "test_medium", "test_nested"]
        results = loader.load_multiple_databases(databases)
        
        assert len(results) == 3
        assert len(results["test_small"]) == 100
        assert len(results["test_medium"]) == 1000
        assert len(results["test_nested"]) == 50
    
    def test_progress_callback(self, temp_cache_dir):
        """Test progress callback functionality."""
        progress_calls = []
        
        def progress_callback(db_name: str, progress: float):
            progress_calls.append((db_name, progress))
        
        loader = JSONDataLoader(
            str(temp_cache_dir),
            progress_callback=progress_callback
        )
        
        # Create a larger file to trigger progress callbacks
        large_data = self._generate_records(50000)
        with open(temp_cache_dir / "test_huge.json", 'w') as f:
            json.dump(large_data, f)
        
        loader.load_database("test_huge")
        
        # Should have progress calls for large file
        assert any(call[0] == "test_huge" for call in progress_calls)
        assert any(call[1] == 100.0 for call in progress_calls)
    
    def test_memory_mapped_loading(self, temp_cache_dir):
        """Test memory-mapped file loading for large files."""
        # Create a file >10MB to trigger mmap
        huge_data = self._generate_records(100000)  # ~30MB
        with open(temp_cache_dir / "test_mmap.json", 'w') as f:
            json.dump(huge_data, f)
        
        loader = JSONDataLoader(str(temp_cache_dir), enable_mmap=True)
        
        start_time = time.time()
        data = loader.load_database("test_mmap")
        load_time = time.time() - start_time
        
        assert len(data) == 100000
        # Should still be reasonably fast
        assert load_time < 5.0  # 5 seconds max for 100K records
    
    def test_case_insensitive_loading(self, temp_cache_dir):
        """Test case-insensitive database name matching."""
        loader = JSONDataLoader(str(temp_cache_dir))
        
        # Should find test_small even with different case
        data = loader.load_database("TEST_SMALL")
        assert len(data) == 100
    
    def test_get_database_stats(self, temp_cache_dir):
        """Test getting database statistics."""
        loader = JSONDataLoader(str(temp_cache_dir))
        
        stats = loader.get_database_stats("test_medium")
        assert "path" in stats
        assert "size" in stats
        assert "modified" in stats
        assert stats["size"] > 0
        
        # Load data and check record count
        loader.load_database("test_medium")
        stats = loader.get_database_stats("test_medium")
        assert stats["record_count"] == 1000
    
    def test_preload_databases(self, temp_cache_dir):
        """Test preloading databases."""
        loader = JSONDataLoader(str(temp_cache_dir))
        
        # Preload specific databases
        loader.preload_databases(["test_small", "test_medium"])
        assert len(loader._cache) == 2
        assert "test_small" in loader._cache
        assert "test_medium" in loader._cache
        
        # Preload all
        loader.refresh_cache()
        loader.preload_databases()
        assert len(loader._cache) == 5  # All test databases
    
    def test_get_memory_usage(self, temp_cache_dir):
        """Test memory usage estimation."""
        loader = JSONDataLoader(str(temp_cache_dir))
        
        loader.load_database("test_small")
        loader.load_database("test_medium")
        
        memory_usage = loader.get_memory_usage()
        assert "test_small" in memory_usage
        assert "test_medium" in memory_usage
        assert memory_usage["test_small"] > 0
        assert memory_usage["test_medium"] > memory_usage["test_small"]
    
    def test_invalid_json_structure(self, temp_cache_dir):
        """Test handling of invalid JSON structures."""
        # Create invalid structure
        with open(temp_cache_dir / "test_invalid.json", 'w') as f:
            json.dump({"not_items_or_list": "invalid"}, f)
        
        loader = JSONDataLoader(str(temp_cache_dir))
        
        with pytest.raises(QueryError) as exc_info:
            loader.load_database("test_invalid")
        assert "Invalid JSON structure" in str(exc_info.value)
    
    def test_performance_benchmarks(self, temp_cache_dir):
        """Test performance meets requirements."""
        loader = JSONDataLoader(str(temp_cache_dir))
        
        # Test 10K records load time < 100ms requirement
        start_time = time.time()
        data = loader.load_database("test_large")
        load_time = (time.time() - start_time) * 1000  # Convert to ms
        
        assert len(data) == 10000
        assert load_time < 100  # Should load in under 100ms
        
        # Test cached access is near-instant
        start_time = time.time()
        data2 = loader.load_database("test_large")
        cached_time = (time.time() - start_time) * 1000
        
        assert cached_time < 1  # Should be under 1ms from cache


class TestJSONDataLoaderIntegration:
    """Integration tests with other components."""
    
    def test_implements_data_loader_protocol(self, temp_cache_dir):
        """Test that JSONDataLoader implements DataLoader protocol."""
        from blackcore.minimal.query_engine.interfaces import DataLoader
        
        loader = JSONDataLoader(str(temp_cache_dir))
        assert isinstance(loader, DataLoader)
    
    def test_error_handling_in_concurrent_loading(self, temp_cache_dir):
        """Test error handling during concurrent loads."""
        loader = JSONDataLoader(str(temp_cache_dir))
        
        # Mix valid and invalid databases
        databases = ["test_small", "nonexistent", "test_medium"]
        results = loader.load_multiple_databases(databases)
        
        assert len(results["test_small"]) == 100
        assert results["nonexistent"] == []  # Failed loads return empty
        assert len(results["test_medium"]) == 1000