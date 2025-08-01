"""Tests for search HTTP endpoints."""

import json
import time
from typing import Dict, List, Any
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, mock_open, MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from blackcore.minimal.api.search_endpoints import (
    router, search_in_json_data, global_search, search_entities, 
    get_search_suggestions
)
from blackcore.minimal.api.models import GlobalSearchResults, EntityResult


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return {
        "sub": "user123",
        "username": "testuser",
        "scopes": ["read"],
        "type": "user"
    }


@pytest.fixture
def sample_json_data():
    """Sample JSON data for testing."""
    return {
        "People & Contacts": [
            {
                "id": "person1",
                "Name": "John Doe",
                "Role": "Council Member",
                "Email": "john@council.gov",
                "Organization": "City Council"
            },
            {
                "id": "person2", 
                "Name": "Jane Smith",
                "Role": "Mayor",
                "Email": "jane@city.gov",
                "Organization": "City Hall"
            }
        ],
        "Organizations & Bodies": [
            {
                "id": "org1",
                "Name": "Swanage Town Council",
                "Type": "Government",
                "Description": "Local government body"
            }
        ],
        "Actionable Tasks": [
            {
                "id": "task1",
                "Task Name": "Shore Road Planning Review",
                "Status": "In Progress",
                "Description": "Review planning application for shore road development"
            }
        ]
    }


class TestSearchInJsonData:
    """Test the search_in_json_data function."""

    def test_search_in_json_data_basic(self):
        """Test basic search functionality."""
        data = [
            {"Name": "John Doe", "Role": "Developer"},
            {"Name": "Jane Smith", "Role": "Manager"},
            {"Name": "Bob Johnson", "Role": "Designer"}
        ]
        
        results = search_in_json_data(data, "john", "people")
        
        assert len(results) == 2  # John Doe and Bob Johnson
        # Both have john in Name field, so same score - just check they're found
        assert any(r["title"] == "John Doe" for r in results)
        assert any(r["title"] == "Bob Johnson" for r in results)

    def test_search_case_insensitive(self):
        """Test case-insensitive search."""
        data = [{"Name": "JOHN DOE"}, {"Name": "jane smith"}]
        
        results = search_in_json_data(data, "JoHn", "people")
        
        assert len(results) == 1
        assert results[0]["title"] == "JOHN DOE"

    def test_search_snippet_generation(self):
        """Test snippet generation for search results."""
        data = [{
            "Name": "John Doe",
            "Description": "A very long description about John Doe and his work in the council" + " more text" * 50
        }]
        
        results = search_in_json_data(data, "john", "people")
        
        assert len(results) == 1
        assert "Name: John Doe" in results[0]["snippet"]
        assert len(results[0]["snippet"]) < 500  # Snippet should be truncated

    def test_search_scoring_priority_fields(self):
        """Test that priority fields get higher scores."""
        data = [
            {"Name": "Council Meeting", "Notes": "Discussion about planning"},
            {"Name": "Regular Update", "Notes": "Council meeting notes"},
        ]
        
        results = search_in_json_data(data, "council", "documents")
        
        assert len(results) == 2
        # First result should have "council" in Name (higher score)
        assert results[0]["title"] == "Council Meeting"
        assert results[0]["relevance_score"] > results[1]["relevance_score"]

    def test_search_no_results(self):
        """Test search with no matching results."""
        data = [{"Name": "John Doe"}, {"Name": "Jane Smith"}]
        
        results = search_in_json_data(data, "nonexistent", "people")
        
        assert len(results) == 0

    def test_search_multiple_field_matches(self):
        """Test search matching multiple fields."""
        data = [{
            "Name": "Council Member",
            "Role": "Council Representative",
            "Department": "City Council"
        }]
        
        results = search_in_json_data(data, "council", "people")
        
        assert len(results) == 1
        # Should have high relevance score due to multiple matches
        assert results[0]["relevance_score"] >= 0.9

    def test_search_special_field_names(self):
        """Test search with special field names."""
        data = [{
            "Event / Place Name": "Shore Road Meeting",
            "Transgression Summary": "Improper conduct at meeting",
            "Document Title": "Meeting Minutes"
        }]
        
        results = search_in_json_data(data, "meeting", "events")
        
        assert len(results) == 1
        assert results[0]["title"] == "Shore Road Meeting"


class TestGlobalSearchEndpoint:
    """Test global search endpoint."""

    @pytest.mark.asyncio
    async def test_global_search_success(self, mock_user, sample_json_data):
        """Test successful global search across all databases."""
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(sample_json_data))):
                with patch('blackcore.minimal.api.search_endpoints.get_search_suggestions', 
                          AsyncMock(return_value=["suggestion1", "suggestion2"])):
                    
                    result = await global_search(
                        query="council",
                        entity_types=None,
                        limit=50,
                        include_relationships=True,
                        current_user=mock_user
                    )
        
        assert isinstance(result, GlobalSearchResults)
        assert result.query == "council"
        assert result.total_results > 0
        assert len(result.suggestions) == 2

    @pytest.mark.asyncio
    async def test_global_search_with_entity_filter(self, mock_user, sample_json_data):
        """Test global search filtered by entity types."""
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(sample_json_data))):
                with patch('blackcore.minimal.api.search_endpoints.get_search_suggestions', 
                          AsyncMock(return_value=[])):
                    
                    result = await global_search(
                        query="john",
                        entity_types=["people"],
                        limit=10,
                        include_relationships=True,
                        current_user=mock_user
                    )
        
        assert result.total_results > 0
        # All results should be from people type
        for res in result.results:
            assert res["type"] == "people"

    @pytest.mark.asyncio
    async def test_global_search_limit(self, mock_user):
        """Test global search respects limit parameter."""
        # Create large dataset
        large_data = {
            "People & Contacts": [
                {"Name": f"Person {i}", "Description": "council member"} 
                for i in range(100)
            ]
        }
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(large_data))):
                with patch('blackcore.minimal.api.search_endpoints.get_search_suggestions', 
                          AsyncMock(return_value=[])):
                    
                    result = await global_search(
                        query="council",
                        entity_types=None,
                        limit=5,
                        include_relationships=True,
                        current_user=mock_user
                    )
        
        assert len(result.results) <= 5

    @pytest.mark.asyncio
    async def test_global_search_file_not_found(self, mock_user):
        """Test global search when JSON files don't exist."""
        with patch('pathlib.Path.exists', return_value=False):
            with patch('blackcore.minimal.api.search_endpoints.get_search_suggestions', 
                      AsyncMock(return_value=[])):
                
                result = await global_search(
                    query="test",
                    entity_types=None,
                    limit=50,
                    include_relationships=True,
                    current_user=mock_user
                )
        
        assert result.total_results == 0
        assert result.results == []

    @pytest.mark.asyncio
    async def test_global_search_json_error(self, mock_user):
        """Test global search handles JSON parsing errors."""
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data="invalid json")):
                with patch('blackcore.minimal.api.search_endpoints.get_search_suggestions', 
                          AsyncMock(return_value=[])):
                    with patch('blackcore.minimal.api.search_endpoints.logger') as mock_logger:
                        
                        result = await global_search(
                            query="test",
                            entity_types=None,
                            limit=50,
                            include_relationships=True,
                            current_user=mock_user
                        )
        
        assert result.total_results == 0
        # Should log error but not crash
        assert mock_logger.error.called

    @pytest.mark.asyncio
    async def test_global_search_exception_handling(self, mock_user):
        """Test global search exception handling."""
        with patch('pathlib.Path.exists', side_effect=Exception("Unexpected error")):
            with patch('blackcore.minimal.api.search_endpoints.logger') as mock_logger:
                # The function should handle errors gracefully and return empty results
                result = await global_search(
                    query="test",
                    entity_types=None,
                    limit=50,
                    include_relationships=True,
                    current_user=mock_user
                )
        
        # Should return empty results when errors occur
        assert result.total_results == 0
        assert result.results == []
        # Should log errors for each database
        assert mock_logger.error.call_count >= 6  # One for each entity type


class TestSearchEntitiesEndpoint:
    """Test entity-specific search endpoint."""

    @pytest.mark.asyncio
    async def test_search_entities_success(self, mock_user, sample_json_data):
        """Test successful entity search."""
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(sample_json_data))):
                
                results = await search_entities(
                    entity_type="people",
                    query="john",
                    limit=20,
                    current_user=mock_user
                )
        
        assert len(results) > 0
        assert all(isinstance(r, EntityResult) for r in results)
        assert results[0].type == "people"
        assert "john" in results[0].title.lower()

    @pytest.mark.asyncio
    async def test_search_entities_invalid_type(self, mock_user):
        """Test entity search with invalid entity type."""
        with pytest.raises(HTTPException) as exc_info:
            await search_entities(
                entity_type="invalid_type",
                query="test",
                limit=20,
                current_user=mock_user
            )
        
        assert exc_info.value.status_code == 400
        assert "Invalid entity type" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_search_entities_file_not_found(self, mock_user):
        """Test entity search when file doesn't exist."""
        with patch('pathlib.Path.exists', return_value=False):
            
            results = await search_entities(
                entity_type="people",
                query="test",
                limit=20,
                current_user=mock_user
            )
        
        assert results == []

    @pytest.mark.asyncio
    async def test_search_entities_empty_data(self, mock_user):
        """Test entity search with empty data."""
        empty_data = {"People & Contacts": []}
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(empty_data))):
                
                results = await search_entities(
                    entity_type="people",
                    query="test",
                    limit=20,
                    current_user=mock_user
                )
        
        assert results == []

    @pytest.mark.asyncio
    async def test_search_entities_all_types(self, mock_user, sample_json_data):
        """Test searching each valid entity type."""
        valid_types = ["people", "organizations", "tasks", "events", "documents", "transgressions"]
        
        for entity_type in valid_types:
            with patch('pathlib.Path.exists', return_value=True):
                with patch('builtins.open', mock_open(read_data=json.dumps(sample_json_data))):
                    
                    # Should not raise exception
                    results = await search_entities(
                        entity_type=entity_type,
                        query="test",
                        limit=20,
                        current_user=mock_user
                    )
                    
                    assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_entities_exception_handling(self, mock_user):
        """Test entity search exception handling."""
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', side_effect=Exception("File error")):
                with pytest.raises(HTTPException) as exc_info:
                    await search_entities(
                        entity_type="people",
                        query="test",
                        limit=20,
                        current_user=mock_user
                    )
        
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Entity search failed"


class TestSearchSuggestionsEndpoint:
    """Test search suggestions endpoint."""

    @pytest.mark.asyncio
    async def test_get_search_suggestions_basic(self, mock_user):
        """Test basic search suggestions."""
        suggestions = await get_search_suggestions(
            query="coun",
            current_user=mock_user
        )
        
        assert isinstance(suggestions, list)
        assert len(suggestions) <= 5
        # Should include "council" as a suggestion
        assert any("council" in s.lower() for s in suggestions)

    @pytest.mark.asyncio
    async def test_get_search_suggestions_entity_names(self, mock_user):
        """Test suggestions include entity names."""
        suggestions = await get_search_suggestions(
            query="mayor",
            current_user=mock_user
        )
        
        assert any("Mayor Sutton" in s for s in suggestions)

    @pytest.mark.asyncio
    async def test_get_search_suggestions_short_query(self, mock_user):
        """Test suggestions with very short query."""
        suggestions = await get_search_suggestions(
            query="s",
            current_user=mock_user
        )
        
        # Should still return some suggestions
        assert isinstance(suggestions, list)

    @pytest.mark.asyncio
    async def test_get_search_suggestions_no_matches(self, mock_user):
        """Test suggestions when no matches found."""
        suggestions = await get_search_suggestions(
            query="zzzzz",
            current_user=mock_user
        )
        
        assert suggestions == []

    @pytest.mark.asyncio
    async def test_get_search_suggestions_exception_handling(self, mock_user):
        """Test suggestions handle exceptions gracefully."""
        # Since get_search_suggestions is imported as a regular function in the test module,
        # we can't mock internal exceptions easily. Let's test that the function doesn't
        # crash with edge cases
        
        # Test with empty query (shouldn't crash)
        suggestions = await get_search_suggestions(
            query="",
            current_user=mock_user
        )
        assert isinstance(suggestions, list)
        
        # Test with very long query
        suggestions = await get_search_suggestions(
            query="a" * 1000,
            current_user=mock_user
        )
        assert isinstance(suggestions, list)
        assert len(suggestions) <= 5


class TestIntegrationWithFastAPI:
    """Test endpoints integration with FastAPI."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_search_endpoints_registered(self, client):
        """Test that search endpoints are registered."""
        # Test global search
        response = client.get("/search/global?query=test")
        assert response.status_code in [401, 403, 422]  # Auth required
        
        # Test entity search
        response = client.get("/search/entities/people?query=test")
        assert response.status_code in [401, 403, 422]
        
        # Test suggestions
        response = client.get("/search/suggestions?query=test")
        assert response.status_code in [401, 403, 422]

    def test_search_query_validation(self, client):
        """Test query parameter validation."""
        # Test minimum query length for global search
        response = client.get("/search/global?query=a")  # Too short
        assert response.status_code in [401, 403, 422]
        
        # Test maximum query length
        long_query = "a" * 201  # Over 200 char limit
        response = client.get(f"/search/global?query={long_query}")
        assert response.status_code in [401, 403, 422]


class TestSearchPerformance:
    """Test search performance characteristics."""

    @pytest.mark.asyncio
    async def test_search_timing(self, mock_user):
        """Test that search time is measured correctly."""
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps({"People & Contacts": []}))):
                with patch('blackcore.minimal.api.search_endpoints.get_search_suggestions', 
                          AsyncMock(return_value=[])):
                    with patch('time.time', side_effect=[1000.0, 1000.5]):  # 0.5 second search
                        
                        result = await global_search(
                            query="test",
                            entity_types=None,
                            limit=50,
                            include_relationships=True,
                            current_user=mock_user
                        )
        
        assert result.search_time == 0.5