"""Comprehensive tests for BasicSortingEngine with performance benchmarks."""

import pytest
from datetime import datetime
import time
import random

from blackcore.minimal.query_engine.sorting import BasicSortingEngine
from blackcore.minimal.query_engine.models import SortField, SortOrder, QueryError


class TestBasicSortingEngine:
    """Test suite for BasicSortingEngine."""
    
    @pytest.fixture
    def sorting_engine(self):
        """Create sorting engine instance."""
        return BasicSortingEngine()
    
    @pytest.fixture
    def sample_data(self):
        """Create sample test data."""
        return [
            {
                "id": "3",
                "name": "Charlie",
                "age": 35,
                "score": 85.5,
                "active": True,
                "created_at": "2024-01-15T10:00:00Z",
                "metadata": {
                    "priority": 5,
                    "category": "B"
                }
            },
            {
                "id": "1",
                "name": "Alice",
                "age": 30,
                "score": 92.0,
                "active": False,
                "created_at": "2024-01-10T08:00:00Z",
                "metadata": {
                    "priority": 3,
                    "category": "A"
                }
            },
            {
                "id": "2",
                "name": "Bob",
                "age": 30,
                "score": 88.5,
                "active": True,
                "created_at": "2024-01-12T14:00:00Z",
                "metadata": {
                    "priority": 3,
                    "category": "A"
                }
            },
            {
                "id": "4",
                "name": "Diana",
                "age": None,
                "score": 95.0,
                "active": True,
                "created_at": "2024-01-20T16:00:00Z",
                "metadata": {
                    "priority": None,
                    "category": "C"
                }
            }
        ]
    
    def test_single_field_sort_ascending(self, sorting_engine, sample_data):
        """Test single field sorting in ascending order."""
        sort_fields = [SortField(field="name", order=SortOrder.ASC)]
        result = sorting_engine.apply_sorting(sample_data, sort_fields)
        
        names = [r["name"] for r in result]
        assert names == ["Alice", "Bob", "Charlie", "Diana"]
    
    def test_single_field_sort_descending(self, sorting_engine, sample_data):
        """Test single field sorting in descending order."""
        sort_fields = [SortField(field="score", order=SortOrder.DESC)]
        result = sorting_engine.apply_sorting(sample_data, sort_fields)
        
        scores = [r["score"] for r in result]
        assert scores == [95.0, 92.0, 88.5, 85.5]
    
    def test_multi_field_sort(self, sorting_engine, sample_data):
        """Test multi-field sorting."""
        sort_fields = [
            SortField(field="age", order=SortOrder.ASC),
            SortField(field="score", order=SortOrder.DESC)
        ]
        result = sorting_engine.apply_sorting(sample_data, sort_fields)
        
        # Expected order: Diana (None), Alice (30, 92.0), Bob (30, 88.5), Charlie (35)
        ids = [r["id"] for r in result]
        assert ids == ["4", "1", "2", "3"]
    
    def test_nested_field_sort(self, sorting_engine, sample_data):
        """Test sorting by nested fields."""
        sort_fields = [SortField(field="metadata.priority", order=SortOrder.ASC)]
        result = sorting_engine.apply_sorting(sample_data, sort_fields)
        
        # None values should sort last
        priorities = [r["metadata"]["priority"] for r in result]
        assert priorities == [3, 3, 5, None]
    
    def test_date_string_sort(self, sorting_engine, sample_data):
        """Test sorting by date strings."""
        sort_fields = [SortField(field="created_at", order=SortOrder.ASC)]
        result = sorting_engine.apply_sorting(sample_data, sort_fields)
        
        dates = [r["created_at"] for r in result]
        assert dates == [
            "2024-01-10T08:00:00Z",
            "2024-01-12T14:00:00Z",
            "2024-01-15T10:00:00Z",
            "2024-01-20T16:00:00Z"
        ]
    
    def test_boolean_sort(self, sorting_engine, sample_data):
        """Test sorting by boolean values."""
        sort_fields = [SortField(field="active", order=SortOrder.ASC)]
        result = sorting_engine.apply_sorting(sample_data, sort_fields)
        
        # False (0) should come before True (1)
        active_values = [r["active"] for r in result]
        assert active_values == [False, True, True, True]
    
    def test_case_insensitive_string_sort(self, sorting_engine):
        """Test case-insensitive string sorting."""
        data = [
            {"name": "zebra"},
            {"name": "Apple"},
            {"name": "banana"},
            {"name": "Cherry"}
        ]
        
        sort_fields = [SortField(field="name", order=SortOrder.ASC)]
        result = sorting_engine.apply_sorting(data, sort_fields)
        
        names = [r["name"] for r in result]
        assert names == ["Apple", "banana", "Cherry", "zebra"]
    
    def test_null_handling(self, sorting_engine, sample_data):
        """Test that null values sort last."""
        sort_fields = [SortField(field="age", order=SortOrder.ASC)]
        result = sorting_engine.apply_sorting(sample_data, sort_fields)
        
        # None should be last
        ages = [r["age"] for r in result]
        assert ages == [30, 30, 35, None]
        
        # Test descending - None should still be last
        sort_fields = [SortField(field="age", order=SortOrder.DESC)]
        result = sorting_engine.apply_sorting(sample_data, sort_fields)
        
        ages = [r["age"] for r in result]
        assert ages == [35, 30, 30, None]
    
    def test_already_sorted_optimization(self, sorting_engine):
        """Test optimization for already sorted data."""
        # Create pre-sorted data
        data = [{"value": i} for i in range(1000)]
        
        sort_fields = [SortField(field="value", order=SortOrder.ASC)]
        
        start_time = time.time()
        result = sorting_engine.apply_sorting(data, sort_fields)
        optimization_time = time.time() - start_time
        
        # Should be very fast for pre-sorted data
        assert optimization_time < 0.001  # Less than 1ms
        assert len(result) == 1000
    
    def test_pagination(self, sorting_engine, sample_data):
        """Test basic pagination."""
        # Page 1
        paginated, total = sorting_engine.apply_pagination(sample_data, page=1, size=2)
        assert len(paginated) == 2
        assert total == 4
        assert paginated[0]["id"] == "3"
        assert paginated[1]["id"] == "1"
        
        # Page 2
        paginated, total = sorting_engine.apply_pagination(sample_data, page=2, size=2)
        assert len(paginated) == 2
        assert total == 4
        assert paginated[0]["id"] == "2"
        assert paginated[1]["id"] == "4"
        
        # Page 3 (empty)
        paginated, total = sorting_engine.apply_pagination(sample_data, page=3, size=2)
        assert len(paginated) == 0
        assert total == 4
    
    def test_pagination_edge_cases(self, sorting_engine, sample_data):
        """Test pagination edge cases."""
        # Invalid page number
        paginated, total = sorting_engine.apply_pagination(sample_data, page=0, size=2)
        assert len(paginated) == 2  # Should default to page 1
        
        # Large page size
        paginated, total = sorting_engine.apply_pagination(sample_data, page=1, size=100)
        assert len(paginated) == 4  # Should return all data
        assert total == 4
    
    def test_cursor_pagination(self, sorting_engine, sample_data):
        """Test cursor-based pagination."""
        # Sort data first
        sort_fields = [SortField(field="name", order=SortOrder.ASC)]
        sorted_data = sorting_engine.apply_sorting(sample_data, sort_fields)
        
        # Get first page
        page1, next_cursor, prev_cursor = sorting_engine.apply_cursor_pagination(
            sorted_data, cursor=None, size=2, sort_fields=sort_fields
        )
        
        assert len(page1) == 2
        assert page1[0]["name"] == "Alice"
        assert page1[1]["name"] == "Bob"
        assert next_cursor is not None
        assert prev_cursor is None
        
        # Get second page using cursor
        page2, next_cursor2, prev_cursor2 = sorting_engine.apply_cursor_pagination(
            sorted_data, cursor=next_cursor, size=2, sort_fields=sort_fields
        )
        
        assert len(page2) == 2
        assert page2[0]["name"] == "Charlie"
        assert page2[1]["name"] == "Diana"
        assert next_cursor2 is None  # Last page
        assert prev_cursor2 is not None
    
    def test_cursor_with_multi_field_sort(self, sorting_engine, sample_data):
        """Test cursor pagination with multi-field sorting."""
        sort_fields = [
            SortField(field="age", order=SortOrder.ASC),
            SortField(field="name", order=SortOrder.ASC)
        ]
        sorted_data = sorting_engine.apply_sorting(sample_data, sort_fields)
        
        # Get pages with cursor
        page1, cursor, _ = sorting_engine.apply_cursor_pagination(
            sorted_data, cursor=None, size=2, sort_fields=sort_fields
        )
        
        page2, _, _ = sorting_engine.apply_cursor_pagination(
            sorted_data, cursor=cursor, size=2, sort_fields=sort_fields
        )
        
        # Verify no overlap
        page1_ids = {r["id"] for r in page1}
        page2_ids = {r["id"] for r in page2}
        assert len(page1_ids & page2_ids) == 0
    
    def test_invalid_cursor(self, sorting_engine, sample_data):
        """Test handling of invalid cursor."""
        sort_fields = [SortField(field="name", order=SortOrder.ASC)]
        
        with pytest.raises(QueryError):
            sorting_engine.apply_cursor_pagination(
                sample_data, cursor="invalid_cursor", size=2, sort_fields=sort_fields
            )
    
    def test_get_top_k(self, sorting_engine):
        """Test efficient top-k selection."""
        # Generate large dataset
        data = [{"value": random.randint(1, 1000)} for _ in range(10000)]
        
        sort_fields = [SortField(field="value", order=SortOrder.DESC)]
        
        # Get top 10
        start_time = time.time()
        top_10 = sorting_engine.get_top_k(data, k=10, sort_fields=sort_fields)
        top_k_time = time.time() - start_time
        
        # Verify results
        assert len(top_10) == 10
        assert all(top_10[i]["value"] >= top_10[i+1]["value"] for i in range(9))
        
        # Should be faster than full sort for large data
        full_sort_start = time.time()
        full_sorted = sorting_engine.apply_sorting(data, sort_fields)[:10]
        full_sort_time = time.time() - full_sort_start
        
        # Top-k should be more efficient
        assert top_k_time < full_sort_time * 0.5  # At least 2x faster
    
    def test_stable_sort(self, sorting_engine):
        """Test that sorting is stable (preserves order of equal elements)."""
        data = [
            {"name": "A", "order": 1},
            {"name": "B", "order": 2},
            {"name": "A", "order": 3},
            {"name": "B", "order": 4},
            {"name": "A", "order": 5}
        ]
        
        sort_fields = [SortField(field="name", order=SortOrder.ASC)]
        result = sorting_engine.apply_sorting(data, sort_fields)
        
        # All A's should come first, preserving original order
        a_orders = [r["order"] for r in result if r["name"] == "A"]
        assert a_orders == [1, 3, 5]
        
        b_orders = [r["order"] for r in result if r["name"] == "B"]
        assert b_orders == [2, 4]
    
    def test_empty_data(self, sorting_engine):
        """Test handling of empty data."""
        sort_fields = [SortField(field="name", order=SortOrder.ASC)]
        result = sorting_engine.apply_sorting([], sort_fields)
        assert result == []
        
        paginated, total = sorting_engine.apply_pagination([], page=1, size=10)
        assert paginated == []
        assert total == 0
    
    def test_no_sort_fields(self, sorting_engine, sample_data):
        """Test with no sort fields returns original data."""
        result = sorting_engine.apply_sorting(sample_data, [])
        assert result == sample_data
    
    def test_performance_large_dataset(self, sorting_engine):
        """Test performance on large dataset meets requirements."""
        # Generate 10K records
        data = []
        for i in range(10000):
            data.append({
                "id": i,
                "name": f"Person {i}",
                "age": random.randint(20, 80),
                "score": random.uniform(0, 100),
                "category": random.choice(["A", "B", "C", "D"])
            })
        
        sort_fields = [
            SortField(field="category", order=SortOrder.ASC),
            SortField(field="score", order=SortOrder.DESC)
        ]
        
        start_time = time.time()
        result = sorting_engine.apply_sorting(data, sort_fields)
        sort_time = time.time() - start_time
        
        # Should complete within reasonable time
        assert len(result) == 10000
        assert sort_time < 0.1  # Less than 100ms for 10K records
        
        # Verify correctness
        for i in range(1, len(result)):
            if result[i-1]["category"] == result[i]["category"]:
                assert result[i-1]["score"] >= result[i]["score"]


class TestSortingEngineIntegration:
    """Integration tests for BasicSortingEngine."""
    
    def test_implements_sorting_engine_protocol(self):
        """Test that BasicSortingEngine implements SortingEngine protocol."""
        from blackcore.minimal.query_engine.interfaces import SortingEngine
        
        engine = BasicSortingEngine()
        assert isinstance(engine, SortingEngine)