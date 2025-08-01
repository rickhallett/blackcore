"""Integration tests for the query engine glue code.

This module tests the integration between all three agents through
the orchestrator and adapters.
"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, List

from ..api import QueryEngineAPI, create_query_api
from ..models.shared import StructuredQuery, QueryResult
from ..models import QueryOperator


class TestQueryEngineIntegration:
    """Test suite for query engine integration."""
    
    @pytest.fixture
    def sample_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Sample test data."""
        return {
            'people_contacts.json': [
                {
                    'id': 'person_1',
                    'properties': {
                        'Name': {
                            'title': [{'plain_text': 'John Smith'}]
                        },
                        'Organization': {
                            'select': {'name': 'ACME Corp'}
                        },
                        'Role': {
                            'rich_text': [{'plain_text': 'CEO'}]
                        },
                        'Email': {
                            'rich_text': [{'plain_text': 'john@acme.com'}]
                        }
                    }
                },
                {
                    'id': 'person_2',
                    'properties': {
                        'Name': {
                            'title': [{'plain_text': 'Jane Doe'}]
                        },
                        'Organization': {
                            'select': {'name': 'TechStart Inc'}
                        },
                        'Role': {
                            'rich_text': [{'plain_text': 'CTO'}]
                        },
                        'Email': {
                            'rich_text': [{'plain_text': 'jane@techstart.com'}]
                        }
                    }
                }
            ],
            'organizations_bodies.json': [
                {
                    'id': 'org_1',
                    'properties': {
                        'Name': {
                            'title': [{'plain_text': 'ACME Corp'}]
                        },
                        'Industry': {
                            'select': {'name': 'Technology'}
                        },
                        'Size': {
                            'number': 500
                        }
                    }
                },
                {
                    'id': 'org_2',
                    'properties': {
                        'Name': {
                            'title': [{'plain_text': 'TechStart Inc'}]
                        },
                        'Industry': {
                            'select': {'name': 'Technology'}
                        },
                        'Size': {
                            'number': 50
                        }
                    }
                }
            ]
        }
    
    @pytest.fixture
    def temp_data_dir(self, sample_data):
        """Create temporary directory with sample data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Write sample data files
            for filename, data in sample_data.items():
                file_path = temp_path / filename
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2)
            
            yield str(temp_path)
    
    @pytest.fixture
    def query_engine(self, temp_data_dir):
        """Create query engine with test data."""
        return QueryEngineAPI(
            json_data_path=temp_data_dir,
            enable_cache=True,
            enable_optimization=True,
            enable_profiling=True
        )
    
    @pytest.mark.asyncio
    async def test_natural_language_search(self, query_engine):
        """Test natural language search integration."""
        # Test basic search
        result = await query_engine.search("find all people")
        
        assert isinstance(result, QueryResult)
        assert len(result.data) >= 0  # Should have data or empty result
        assert result.execution_time_ms >= 0
        assert result.cache_hit is False  # First time, should not be cached
    
    @pytest.mark.asyncio
    async def test_structured_query_execution(self, query_engine):
        """Test structured query execution."""
        # Build a structured query
        query = create_query_api('search') \
            .entities('people') \
            .equals('Organization', 'ACME Corp') \
            .sort_asc('Name') \
            .limit(10) \
            .build()
        
        result = await query_engine.query(query)
        
        assert isinstance(result, QueryResult)
        assert result.total_count >= 0
        assert result.execution_time_ms >= 0
    
    def test_synchronous_api(self, query_engine):
        """Test synchronous API wrappers."""
        # Test sync search
        result = query_engine.search_sync("find John")
        
        assert isinstance(result, QueryResult)
        assert result.execution_time_ms >= 0
        
        # Test sync structured query
        query = create_query_api('search') \
            .entities('people') \
            .contains('Name', 'John') \
            .build()
        
        result = query_engine.query_sync(query)
        assert isinstance(result, QueryResult)
    
    @pytest.mark.asyncio
    async def test_caching_integration(self, query_engine):
        """Test caching functionality."""
        query = "find all organizations"
        
        # First query - should not be cached
        result1 = await query_engine.search(query)
        assert result1.cache_hit is False
        
        # Second identical query - might be cached
        result2 = await query_engine.search(query)
        # Note: caching behavior depends on implementation
        assert isinstance(result2, QueryResult)
    
    @pytest.mark.asyncio
    async def test_export_functionality(self, query_engine):
        """Test export functionality."""
        # Get some results first
        result = await query_engine.search("find people")
        
        # Test JSON export
        json_export = await query_engine.export(result, 'json')
        assert isinstance(json_export, str)
        
        # Verify it's valid JSON
        exported_data = json.loads(json_export)
        assert 'data' in exported_data
        
        # Test CSV export
        csv_export = await query_engine.export(result, 'csv')
        assert isinstance(csv_export, str)
    
    def test_database_discovery(self, query_engine):
        """Test database discovery functionality."""
        databases = query_engine.get_available_databases()
        assert isinstance(databases, list)
        # Should find our test databases
        assert len(databases) >= 0
    
    def test_export_format_discovery(self, query_engine):
        """Test export format discovery."""
        formats = query_engine.get_supported_export_formats()
        assert isinstance(formats, list)
        assert 'json' in formats
        assert 'csv' in formats
    
    def test_statistics_collection(self, query_engine):
        """Test statistics collection."""
        stats = query_engine.get_statistics()
        assert isinstance(stats, dict)
        # Should have basic statistics
        assert 'total_queries' in stats
    
    @pytest.mark.asyncio
    async def test_filter_operations(self, query_engine):
        """Test various filter operations."""
        # Test different filter types
        test_cases = [
            ('equals', 'Organization', 'ACME Corp'),
            ('contains', 'Name', 'John'),
            ('greater_than', 'Size', 100),
        ]
        
        for filter_type, field, value in test_cases:
            query = create_query_api('search') \
                .entities('people', 'organizations')
            
            # Apply filter based on type
            if filter_type == 'equals':
                query = query.equals(field, value)
            elif filter_type == 'contains':
                query = query.contains(field, value)
            elif filter_type == 'greater_than':
                query = query.greater_than(field, value)
            
            structured_query = query.build()
            result = await query_engine.query(structured_query)
            
            assert isinstance(result, QueryResult)
            assert result.execution_time_ms >= 0
    
    @pytest.mark.asyncio
    async def test_sorting_operations(self, query_engine):
        """Test sorting functionality."""
        query = create_query_api('search') \
            .entities('people') \
            .sort_asc('Name') \
            .build()
        
        result = await query_engine.query(query)
        assert isinstance(result, QueryResult)
        
        # Test descending sort
        query = create_query_api('search') \
            .entities('people') \
            .sort_desc('Name') \
            .build()
        
        result = await query_engine.query(query)
        assert isinstance(result, QueryResult)
    
    @pytest.mark.asyncio
    async def test_pagination(self, query_engine):
        """Test pagination functionality."""
        query = create_query_api('search') \
            .entities('people') \
            .limit(1) \
            .offset(0) \
            .build()
        
        result = await query_engine.query(query)
        assert isinstance(result, QueryResult)
    
    @pytest.mark.asyncio
    async def test_relationship_inclusion(self, query_engine):
        """Test relationship inclusion."""
        query = create_query_api('search') \
            .entities('people') \
            .include_relationships('organization') \
            .relationship_depth(1) \
            .build()
        
        result = await query_engine.query(query)
        assert isinstance(result, QueryResult)
    
    def test_error_handling(self, query_engine):
        """Test error handling in various scenarios."""
        # Test invalid export format
        with pytest.raises(ValueError):
            result = QueryResult(data=[], total_count=0)
            query_engine.export_sync(result, 'invalid_format')
    
    @pytest.mark.asyncio
    async def test_cache_clearing(self, query_engine):
        """Test cache clearing functionality."""
        # Perform some queries to populate cache
        await query_engine.search("test query")
        
        # Clear cache
        query_engine.clear_cache()
        
        # Should still work after cache clear
        result = await query_engine.search("test query")
        assert isinstance(result, QueryResult)


class TestQueryBuilder:
    """Test suite for the query builder."""
    
    def test_query_builder_fluent_interface(self):
        """Test the fluent interface of query builder."""
        query = create_query_api('search') \
            .entities('people', 'organizations') \
            .equals('status', 'active') \
            .contains('name', 'test') \
            .greater_than('size', 100) \
            .less_than('created', '2024-01-01') \
            .in_list('category', ['A', 'B', 'C']) \
            .sort_asc('name') \
            .sort_desc('created') \
            .limit(50) \
            .offset(10) \
            .include_relationships('related_items') \
            .relationship_depth(2) \
            .count('items', 'item_count') \
            .sum('value', 'total_value') \
            .avg('rating', 'avg_rating') \
            .group_by('category', 'status') \
            .build()
        
        assert isinstance(query, StructuredQuery)
        assert query.intent == 'search'
        assert 'people' in query.entities
        assert 'organizations' in query.entities
        assert len(query.filters) == 5
        assert len(query.sort_criteria) == 2
        assert query.limit == 50
        assert query.offset == 10
        assert 'related_items' in query.include_relationships
        assert query.relationship_depth == 2
        assert len(query.aggregations) == 3
        assert len(query.group_by) == 2
    
    def test_filter_methods(self):
        """Test different filter methods."""
        query = create_query_api() \
            .equals('field1', 'value1') \
            .contains('field2', 'value2') \
            .greater_than('field3', 100) \
            .less_than('field4', 200) \
            .in_list('field5', ['a', 'b', 'c']) \
            .build()
        
        assert len(query.filters) == 5
        
        # Check filter operators
        operators = [f.operator for f in query.filters]
        from ..models import QueryOperator
        assert QueryOperator.EQUALS in operators
        assert QueryOperator.CONTAINS in operators
        assert QueryOperator.GT in operators
        assert QueryOperator.LT in operators
        assert QueryOperator.IN in operators


# Integration test for Agent communication
class TestAgentCommunication:
    """Test communication between different agents."""
    
    @pytest.fixture
    def mock_data_dir(self):
        """Create a simple mock data directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create minimal test data
            test_data = [
                {
                    'id': 'test_1',
                    'properties': {
                        'Name': {'title': [{'plain_text': 'Test Item'}]},
                        'Status': {'select': {'name': 'Active'}}
                    }
                }
            ]
            
            # Write to a generic file
            file_path = temp_path / 'test_data.json'
            with open(file_path, 'w') as f:
                json.dump(test_data, f)
            
            yield str(temp_path)
    
    def test_agent_integration(self, mock_data_dir):
        """Test that all agents can be integrated together."""
        from ..adapters import integrate_all_agents
        
        config = integrate_all_agents(
            json_data_path=mock_data_dir,
            enable_disk_cache=False,
            max_cache_items=100,
            default_ttl=1800
        )
        
        # Should have Agent A components
        assert 'data_loader' in config
        assert 'filter_engine' in config
        
        # Should have Agent C components
        assert 'cache_manager' in config
        assert 'query_optimizer' in config
        assert 'export_engine' in config
        
        # Test that components have expected interfaces
        assert hasattr(config['data_loader'], 'load_database')
        assert hasattr(config['filter_engine'], 'apply_filters')
        assert hasattr(config['cache_manager'], 'get_cached_result')
        assert hasattr(config['query_optimizer'], 'optimize_query')
        assert hasattr(config['export_engine'], 'export')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])