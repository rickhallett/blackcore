"""Comprehensive tests for BasicFilterEngine with all 15 operators."""

import pytest
from datetime import datetime
import time

from blackcore.minimal.query_engine.filters import BasicFilterEngine
from blackcore.minimal.query_engine.models import QueryFilter, QueryOperator, QueryValidationError


class TestBasicFilterEngine:
    """Test suite for BasicFilterEngine."""
    
    @pytest.fixture
    def filter_engine(self):
        """Create filter engine instance."""
        return BasicFilterEngine()
    
    @pytest.fixture
    def sample_data(self):
        """Create sample test data."""
        return [
            {
                "id": "1",
                "name": "Alice Johnson",
                "age": 30,
                "active": True,
                "tags": ["admin", "user"],
                "created_at": "2024-01-15T00:00:00Z",
                "metadata": {
                    "category": "A",
                    "priority": 5
                }
            },
            {
                "id": "2", 
                "name": "Bob Smith",
                "age": 25,
                "active": False,
                "tags": ["user"],
                "created_at": "2024-01-20T00:00:00Z",
                "metadata": {
                    "category": "B",
                    "priority": 3
                }
            },
            {
                "id": "3",
                "name": "Charlie Brown",
                "age": 35,
                "active": True,
                "tags": ["admin", "manager", "user"],
                "created_at": "2024-01-10T00:00:00Z",
                "metadata": {
                    "category": "A",
                    "priority": 8
                }
            },
            {
                "id": "4",
                "name": "Diana Prince",
                "age": None,
                "active": True,
                "tags": [],
                "created_at": "2024-01-25T00:00:00Z",
                "metadata": {
                    "category": "C",
                    "priority": None
                }
            }
        ]
    
    def test_filter_equals(self, filter_engine, sample_data):
        """Test EQUALS operator."""
        # Test string equality
        filter_cond = QueryFilter(field="name", operator=QueryOperator.EQUALS, value="Alice Johnson")
        result = filter_engine.apply_filters(sample_data, [filter_cond])
        assert len(result) == 1
        assert result[0]["id"] == "1"
        
        # Test numeric equality
        filter_cond = QueryFilter(field="age", operator=QueryOperator.EQUALS, value=25)
        result = filter_engine.apply_filters(sample_data, [filter_cond])
        assert len(result) == 1
        assert result[0]["id"] == "2"
        
        # Test boolean equality
        filter_cond = QueryFilter(field="active", operator=QueryOperator.EQUALS, value=True)
        result = filter_engine.apply_filters(sample_data, [filter_cond])
        assert len(result) == 3
        
        # Test case-insensitive
        filter_cond = QueryFilter(
            field="name", 
            operator=QueryOperator.EQUALS, 
            value="alice johnson",
            case_sensitive=False
        )
        result = filter_engine.apply_filters(sample_data, [filter_cond])
        assert len(result) == 1
    
    def test_filter_not_equals(self, filter_engine, sample_data):
        """Test NOT_EQUALS operator."""
        filter_cond = QueryFilter(field="active", operator=QueryOperator.NOT_EQUALS, value=True)
        result = filter_engine.apply_filters(sample_data, [filter_cond])
        assert len(result) == 1
        assert result[0]["id"] == "2"
    
    def test_filter_contains(self, filter_engine, sample_data):
        """Test CONTAINS operator."""
        # Test string contains
        filter_cond = QueryFilter(field="name", operator=QueryOperator.CONTAINS, value="Johnson")
        result = filter_engine.apply_filters(sample_data, [filter_cond])
        assert len(result) == 1
        assert result[0]["id"] == "1"
        
        # Test array contains
        filter_cond = QueryFilter(field="tags", operator=QueryOperator.CONTAINS, value="admin")
        result = filter_engine.apply_filters(sample_data, [filter_cond])
        assert len(result) == 2
        
        # Test case-insensitive
        filter_cond = QueryFilter(
            field="name",
            operator=QueryOperator.CONTAINS,
            value="JOHNSON",
            case_sensitive=False
        )
        result = filter_engine.apply_filters(sample_data, [filter_cond])
        assert len(result) == 1
    
    def test_filter_not_contains(self, filter_engine, sample_data):
        """Test NOT_CONTAINS operator."""
        filter_cond = QueryFilter(field="tags", operator=QueryOperator.NOT_CONTAINS, value="admin")
        result = filter_engine.apply_filters(sample_data, [filter_cond])
        assert len(result) == 2
        assert set(r["id"] for r in result) == {"2", "4"}
    
    def test_filter_in(self, filter_engine, sample_data):
        """Test IN operator."""
        filter_cond = QueryFilter(
            field="age",
            operator=QueryOperator.IN,
            value=[25, 30]
        )
        result = filter_engine.apply_filters(sample_data, [filter_cond])
        assert len(result) == 2
        assert set(r["id"] for r in result) == {"1", "2"}
        
        # Test case-insensitive
        filter_cond = QueryFilter(
            field="name",
            operator=QueryOperator.IN,
            value=["alice johnson", "bob smith"],
            case_sensitive=False
        )
        result = filter_engine.apply_filters(sample_data, [filter_cond])
        assert len(result) == 2
    
    def test_filter_not_in(self, filter_engine, sample_data):
        """Test NOT_IN operator."""
        filter_cond = QueryFilter(
            field="age",
            operator=QueryOperator.NOT_IN,
            value=[25, 30]
        )
        result = filter_engine.apply_filters(sample_data, [filter_cond])
        assert len(result) == 2  # Charlie (35) and Diana (None)
        assert set(r["id"] for r in result) == {"3", "4"}
    
    def test_filter_gt(self, filter_engine, sample_data):
        """Test GT (greater than) operator."""
        filter_cond = QueryFilter(field="age", operator=QueryOperator.GT, value=30)
        result = filter_engine.apply_filters(sample_data, [filter_cond])
        assert len(result) == 1
        assert result[0]["id"] == "3"
        
        # Test with dates
        filter_cond = QueryFilter(
            field="created_at",
            operator=QueryOperator.GT,
            value="2024-01-15T00:00:00Z"
        )
        result = filter_engine.apply_filters(sample_data, [filter_cond])
        assert len(result) == 2  # Bob and Diana
    
    def test_filter_gte(self, filter_engine, sample_data):
        """Test GTE (greater than or equal) operator."""
        filter_cond = QueryFilter(field="age", operator=QueryOperator.GTE, value=30)
        result = filter_engine.apply_filters(sample_data, [filter_cond])
        assert len(result) == 2
        assert set(r["id"] for r in result) == {"1", "3"}
    
    def test_filter_lt(self, filter_engine, sample_data):
        """Test LT (less than) operator."""
        filter_cond = QueryFilter(field="age", operator=QueryOperator.LT, value=30)
        result = filter_engine.apply_filters(sample_data, [filter_cond])
        assert len(result) == 1
        assert result[0]["id"] == "2"
    
    def test_filter_lte(self, filter_engine, sample_data):
        """Test LTE (less than or equal) operator."""
        filter_cond = QueryFilter(field="age", operator=QueryOperator.LTE, value=30)
        result = filter_engine.apply_filters(sample_data, [filter_cond])
        assert len(result) == 2
        assert set(r["id"] for r in result) == {"1", "2"}
    
    def test_filter_between(self, filter_engine, sample_data):
        """Test BETWEEN operator."""
        filter_cond = QueryFilter(
            field="age",
            operator=QueryOperator.BETWEEN,
            value=[25, 35]
        )
        result = filter_engine.apply_filters(sample_data, [filter_cond])
        assert len(result) == 3
        assert set(r["id"] for r in result) == {"1", "2", "3"}
        
        # Test validation
        with pytest.raises(QueryValidationError):
            filter_cond = QueryFilter(
                field="age",
                operator=QueryOperator.BETWEEN,
                value=[25]  # Invalid - needs 2 values
            )
            filter_engine.apply_filters(sample_data, [filter_cond])
    
    def test_filter_is_null(self, filter_engine, sample_data):
        """Test IS_NULL operator."""
        filter_cond = QueryFilter(field="age", operator=QueryOperator.IS_NULL, value=None)
        result = filter_engine.apply_filters(sample_data, [filter_cond])
        assert len(result) == 1
        assert result[0]["id"] == "4"
        
        # Test nested field
        filter_cond = QueryFilter(field="metadata.priority", operator=QueryOperator.IS_NULL, value=None)
        result = filter_engine.apply_filters(sample_data, [filter_cond])
        assert len(result) == 1
        assert result[0]["id"] == "4"
    
    def test_filter_is_not_null(self, filter_engine, sample_data):
        """Test IS_NOT_NULL operator."""
        filter_cond = QueryFilter(field="age", operator=QueryOperator.IS_NOT_NULL, value=None)
        result = filter_engine.apply_filters(sample_data, [filter_cond])
        assert len(result) == 3
        assert "4" not in [r["id"] for r in result]
    
    def test_filter_regex(self, filter_engine, sample_data):
        """Test REGEX operator."""
        # Test basic regex
        filter_cond = QueryFilter(
            field="name",
            operator=QueryOperator.REGEX,
            value=r"^[A-C].*"
        )
        result = filter_engine.apply_filters(sample_data, [filter_cond])
        assert len(result) == 3  # Alice, Bob, Charlie
        
        # Test case-insensitive regex
        filter_cond = QueryFilter(
            field="name",
            operator=QueryOperator.REGEX,
            value=r"john.*",
            case_sensitive=False
        )
        result = filter_engine.apply_filters(sample_data, [filter_cond])
        assert len(result) == 1
        assert result[0]["id"] == "1"
    
    def test_filter_fuzzy(self, filter_engine, sample_data):
        """Test FUZZY operator."""
        # Test with simple string
        filter_cond = QueryFilter(
            field="name",
            operator=QueryOperator.FUZZY,
            value="Alise Jonson"  # Misspelled
        )
        result = filter_engine.apply_filters(sample_data, [filter_cond])
        assert len(result) == 1
        assert result[0]["id"] == "1"
        
        # Test with threshold
        filter_cond = QueryFilter(
            field="name",
            operator=QueryOperator.FUZZY,
            value={"text": "Jon", "threshold": 50}
        )
        result = filter_engine.apply_filters(sample_data, [filter_cond])
        assert len(result) > 0
    
    def test_nested_field_access(self, filter_engine, sample_data):
        """Test nested field access with dot notation."""
        filter_cond = QueryFilter(
            field="metadata.category",
            operator=QueryOperator.EQUALS,
            value="A"
        )
        result = filter_engine.apply_filters(sample_data, [filter_cond])
        assert len(result) == 2
        assert set(r["id"] for r in result) == {"1", "3"}
        
        # Test nested numeric
        filter_cond = QueryFilter(
            field="metadata.priority",
            operator=QueryOperator.GT,
            value=4
        )
        result = filter_engine.apply_filters(sample_data, [filter_cond])
        assert len(result) == 2
        assert set(r["id"] for r in result) == {"1", "3"}
    
    def test_multiple_filters(self, filter_engine, sample_data):
        """Test applying multiple filters."""
        filters = [
            QueryFilter(field="active", operator=QueryOperator.EQUALS, value=True),
            QueryFilter(field="age", operator=QueryOperator.GTE, value=30),
            QueryFilter(field="tags", operator=QueryOperator.CONTAINS, value="admin")
        ]
        result = filter_engine.apply_filters(sample_data, filters)
        assert len(result) == 2
        assert set(r["id"] for r in result) == {"1", "3"}
    
    def test_filter_optimization(self, filter_engine, sample_data):
        """Test filter order optimization."""
        # Create filters with different selectivity
        filters = [
            QueryFilter(field="name", operator=QueryOperator.REGEX, value=r".*"),  # Low selectivity
            QueryFilter(field="id", operator=QueryOperator.EQUALS, value="1"),  # High selectivity
            QueryFilter(field="age", operator=QueryOperator.GT, value=20)  # Medium selectivity
        ]
        
        # Apply filters
        result = filter_engine.apply_filters(sample_data, filters)
        assert len(result) == 1
        assert result[0]["id"] == "1"
        
        # The optimizer should execute EQUALS first for better performance
    
    def test_performance_large_dataset(self, filter_engine):
        """Test performance on large dataset."""
        # Generate 10K records
        large_data = []
        for i in range(10000):
            large_data.append({
                "id": str(i),
                "name": f"Person {i}",
                "age": i % 100,
                "active": i % 2 == 0,
                "value": i * 1.5,
                "tags": [f"tag_{j}" for j in range(i % 5)]
            })
        
        # Test filter performance - should complete in <50ms
        filter_cond = QueryFilter(field="age", operator=QueryOperator.GT, value=50)
        
        start_time = time.time()
        result = filter_engine.apply_filters(large_data, [filter_cond])
        execution_time = (time.time() - start_time) * 1000
        
        assert len(result) == 4900  # Records with age 51-99
        assert execution_time < 50  # Should complete in under 50ms
    
    def test_empty_data_handling(self, filter_engine):
        """Test handling of empty data."""
        filter_cond = QueryFilter(field="name", operator=QueryOperator.EQUALS, value="test")
        result = filter_engine.apply_filters([], [filter_cond])
        assert result == []
    
    def test_no_filters(self, filter_engine, sample_data):
        """Test with no filters returns original data."""
        result = filter_engine.apply_filters(sample_data, [])
        assert result == sample_data
    
    def test_validation_error_handling(self, filter_engine, sample_data):
        """Test validation error handling."""
        # Test IN operator with non-list value
        with pytest.raises(QueryValidationError):
            filter_cond = QueryFilter(
                field="age",
                operator=QueryOperator.IN,
                value="not a list"
            )
            filter_engine.apply_filters(sample_data, [filter_cond])


class TestFilterEngineIntegration:
    """Integration tests for BasicFilterEngine."""
    
    def test_implements_filter_engine_protocol(self):
        """Test that BasicFilterEngine implements FilterEngine protocol."""
        from blackcore.minimal.query_engine.interfaces import FilterEngine
        
        engine = BasicFilterEngine()
        assert isinstance(engine, FilterEngine)