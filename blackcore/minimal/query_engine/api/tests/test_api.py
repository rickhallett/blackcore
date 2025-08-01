"""Comprehensive tests for the Query Engine API."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import json
import tempfile
from pathlib import Path
from datetime import datetime

from blackcore.minimal.query_engine.api.app import create_app
from blackcore.minimal.query_engine.api.models import (
    QueryRequest, FilterRequest, SortRequest, PaginationRequest,
    TextSearchRequest
)
from blackcore.minimal.query_engine.models import QueryOperator, SortOrder


class TestQueryEngineAPI:
    """Test suite for Query Engine API."""
    
    @pytest.fixture
    def temp_data_dir(self):
        """Create temporary directory with test data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            
            # Create test database files
            people_data = [
                {
                    "id": "person1",
                    "properties": {
                        "Name": "Alice Johnson",
                        "Department": "Engineering",
                        "Age": 30
                    },
                    "created_time": "2024-01-15T10:00:00Z",
                    "last_edited_time": "2024-01-20T15:00:00Z"
                },
                {
                    "id": "person2",
                    "properties": {
                        "Name": "Bob Smith",
                        "Department": "Sales",
                        "Age": 35
                    },
                    "created_time": "2024-01-10T09:00:00Z",
                    "last_edited_time": "2024-01-18T14:00:00Z"
                }
            ]
            
            tasks_data = [
                {
                    "id": "task1",
                    "properties": {
                        "Title": "Complete API Documentation",
                        "Status": "In Progress",
                        "Priority": 5
                    },
                    "created_time": "2024-01-20T11:00:00Z",
                    "last_edited_time": "2024-01-25T16:00:00Z"
                }
            ]
            
            # Write test data
            with open(data_dir / "People & Contacts.json", "w") as f:
                json.dump(people_data, f)
            
            with open(data_dir / "Actionable Tasks.json", "w") as f:
                json.dump(tasks_data, f)
            
            yield data_dir
    
    @pytest.fixture
    def test_client(self, temp_data_dir):
        """Create test client with temporary data."""
        app = create_app(
            cache_dir=str(temp_data_dir),
            enable_caching=False,
            enable_auth=False  # Disable auth for most tests
        )
        return TestClient(app)
    
    @pytest.fixture
    def auth_client(self, temp_data_dir):
        """Create test client with authentication enabled."""
        app = create_app(
            cache_dir=str(temp_data_dir),
            enable_caching=False,
            enable_auth=True
        )
        return TestClient(app)
    
    def test_health_check(self, test_client):
        """Test health check endpoint."""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_system_status(self, test_client):
        """Test system status endpoint."""
        response = test_client.get("/status")
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert len(data["databases"]) == 2
        
        # Check database info
        db_names = [db["name"] for db in data["databases"]]
        assert "People & Contacts" in db_names
        assert "Actionable Tasks" in db_names
    
    def test_list_databases(self, test_client):
        """Test list databases endpoint."""
        response = test_client.get("/databases")
        assert response.status_code == 200
        databases = response.json()
        
        assert len(databases) == 2
        assert any(db["name"] == "People & Contacts" for db in databases)
        assert any(db["name"] == "Actionable Tasks" for db in databases)
    
    def test_get_database_schema(self, test_client):
        """Test get database schema endpoint."""
        response = test_client.get("/databases/People & Contacts/schema")
        assert response.status_code == 200
        schema = response.json()
        
        assert schema["database"] == "People & Contacts"
        assert schema["record_count"] == 2
        assert "fields" in schema
        assert "id" in schema["fields"]
        assert "properties" in schema["fields"]
    
    def test_basic_query(self, test_client):
        """Test basic query execution."""
        query = QueryRequest(
            database="People & Contacts",
            filters=[],
            sort=[],
            pagination=PaginationRequest(page=1, size=10)
        )
        
        response = test_client.post("/query", json=query.dict())
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["data"]) == 2
        assert data["total_count"] == 2
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert data["total_pages"] == 1
        assert "execution_time_ms" in data
    
    def test_query_with_filters(self, test_client):
        """Test query with filter conditions."""
        query = QueryRequest(
            database="People & Contacts",
            filters=[
                FilterRequest(
                    field="properties.Department",
                    operator=QueryOperator.EQUALS,
                    value="Engineering"
                )
            ]
        )
        
        response = test_client.post("/query", json=query.dict())
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["data"]) == 1
        assert data["data"][0]["properties"]["Name"] == "Alice Johnson"
    
    def test_query_with_sorting(self, test_client):
        """Test query with sorting."""
        query = QueryRequest(
            database="People & Contacts",
            sort=[
                SortRequest(
                    field="properties.Age",
                    order=SortOrder.DESC
                )
            ]
        )
        
        response = test_client.post("/query", json=query.dict())
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["data"]) == 2
        assert data["data"][0]["properties"]["Name"] == "Bob Smith"  # Age 35
        assert data["data"][1]["properties"]["Name"] == "Alice Johnson"  # Age 30
    
    def test_query_with_pagination(self, test_client):
        """Test query with pagination."""
        query = QueryRequest(
            database="People & Contacts",
            pagination=PaginationRequest(page=1, size=1)
        )
        
        response = test_client.post("/query", json=query.dict())
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["data"]) == 1
        assert data["total_count"] == 2
        assert data["page"] == 1
        assert data["page_size"] == 1
        assert data["total_pages"] == 2
    
    def test_text_search(self, test_client):
        """Test text search functionality."""
        search_request = TextSearchRequest(
            query="Alice",
            databases=["People & Contacts"]
        )
        
        response = test_client.post("/search", json=search_request.dict())
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["results"]) == 1
        assert data["results"][0]["entity"]["properties"]["Name"] == "Alice Johnson"
        assert data["query"] == "Alice"
        assert "execution_time_ms" in data
    
    def test_batch_queries(self, test_client):
        """Test batch query execution."""
        queries = [
            QueryRequest(database="People & Contacts"),
            QueryRequest(database="Actionable Tasks")
        ]
        
        response = test_client.post("/query/batch", json=[q.dict() for q in queries])
        assert response.status_code == 200
        results = response.json()
        
        assert len(results) == 2
        assert results[0]["total_count"] == 2  # People
        assert results[1]["total_count"] == 1  # Tasks
    
    def test_invalid_database(self, test_client):
        """Test query with invalid database name."""
        query = QueryRequest(database="NonexistentDB")
        
        response = test_client.post("/query", json=query.dict())
        assert response.status_code == 500
    
    def test_invalid_filter_operator(self, test_client):
        """Test query with invalid filter operator."""
        query_data = {
            "database": "People & Contacts",
            "filters": [{
                "field": "properties.Name",
                "operator": "invalid_op",
                "value": "test"
            }]
        }
        
        response = test_client.post("/query", json=query_data)
        assert response.status_code == 422  # Validation error
    
    def test_authentication_required(self, auth_client):
        """Test that authentication is required when enabled."""
        query = QueryRequest(database="People & Contacts")
        
        # Without auth header
        response = auth_client.post("/query", json=query.dict())
        assert response.status_code == 403  # Forbidden
        
        # With invalid auth
        response = auth_client.post(
            "/query",
            json=query.dict(),
            headers={"Authorization": "Bearer invalid-key"}
        )
        assert response.status_code == 401  # Unauthorized
        
        # With valid auth
        response = auth_client.post(
            "/query",
            json=query.dict(),
            headers={"Authorization": "Bearer test-api-key"}
        )
        assert response.status_code == 200
    
    def test_rate_limiting(self, auth_client):
        """Test rate limiting functionality."""
        query = QueryRequest(database="People & Contacts")
        headers = {"Authorization": "Bearer test-api-key"}
        
        # Make requests up to the limit
        for _ in range(60):  # Default rate limit
            response = auth_client.post("/query", json=query.dict(), headers=headers)
            assert response.status_code == 200
        
        # Next request should be rate limited
        response = auth_client.post("/query", json=query.dict(), headers=headers)
        assert response.status_code == 429  # Too Many Requests
        assert "Rate limit exceeded" in response.json()["detail"]
    
    def test_complex_query(self, test_client):
        """Test complex query with multiple filters and sorting."""
        query = QueryRequest(
            database="People & Contacts",
            filters=[
                FilterRequest(
                    field="properties.Age",
                    operator=QueryOperator.GTE,
                    value=30
                ),
                FilterRequest(
                    field="properties.Department",
                    operator=QueryOperator.NOT_EQUALS,
                    value="HR"
                )
            ],
            sort=[
                SortRequest(field="properties.Department", order=SortOrder.ASC),
                SortRequest(field="properties.Name", order=SortOrder.ASC)
            ],
            pagination=PaginationRequest(page=1, size=50)
        )
        
        response = test_client.post("/query", json=query.dict())
        assert response.status_code == 200
        data = response.json()
        
        # Verify results match filters
        for entity in data["data"]:
            assert entity["properties"]["Age"] >= 30
            assert entity["properties"]["Department"] != "HR"
    
    def test_openapi_schema(self, test_client):
        """Test OpenAPI schema generation."""
        response = test_client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        
        assert schema["info"]["title"] == "BlackCore Query Engine API"
        assert "paths" in schema
        assert "/query" in schema["paths"]
        assert "/search" in schema["paths"]
        assert "components" in schema
        assert "schemas" in schema["components"]


class TestQueryEngineAPIPerformance:
    """Performance tests for the Query Engine API."""
    
    @pytest.fixture
    def large_dataset_dir(self):
        """Create large test dataset."""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            
            # Create 10k records
            large_data = []
            for i in range(10000):
                large_data.append({
                    "id": f"record{i}",
                    "properties": {
                        "Name": f"Person {i}",
                        "Department": ["Engineering", "Sales", "HR", "Marketing"][i % 4],
                        "Age": 20 + (i % 50),
                        "Score": i * 0.1
                    },
                    "created_time": f"2024-01-{(i % 28) + 1:02d}T10:00:00Z",
                    "last_edited_time": f"2024-01-{(i % 28) + 1:02d}T15:00:00Z"
                })
            
            with open(data_dir / "LargeDataset.json", "w") as f:
                json.dump(large_data, f)
            
            yield data_dir
    
    @pytest.fixture
    def perf_client(self, large_dataset_dir):
        """Create test client for performance testing."""
        app = create_app(
            cache_dir=str(large_dataset_dir),
            enable_caching=True,
            enable_auth=False
        )
        return TestClient(app)
    
    def test_large_dataset_query_performance(self, perf_client):
        """Test query performance on large dataset."""
        import time
        
        query = QueryRequest(
            database="LargeDataset",
            filters=[
                FilterRequest(
                    field="properties.Department",
                    operator=QueryOperator.EQUALS,
                    value="Engineering"
                )
            ],
            sort=[
                SortRequest(field="properties.Score", order=SortOrder.DESC)
            ],
            pagination=PaginationRequest(page=1, size=100)
        )
        
        start_time = time.time()
        response = perf_client.post("/query", json=query.dict())
        execution_time = time.time() - start_time
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return ~2500 engineering records
        assert data["total_count"] == 2500
        assert len(data["data"]) == 100  # First page
        
        # Performance assertions
        assert execution_time < 1.0  # Should complete in under 1 second
        assert data["execution_time_ms"] < 1000  # API reported time
    
    def test_caching_performance(self, perf_client):
        """Test that caching improves performance."""
        query = QueryRequest(
            database="LargeDataset",
            filters=[
                FilterRequest(
                    field="properties.Age",
                    operator=QueryOperator.GT,
                    value=40
                )
            ]
        )
        
        # First query (cache miss)
        response1 = perf_client.post("/query", json=query.dict())
        assert response1.status_code == 200
        data1 = response1.json()
        assert not data1["from_cache"]
        first_time = data1["execution_time_ms"]
        
        # Second query (cache hit)
        response2 = perf_client.post("/query", json=query.dict())
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["from_cache"]
        cached_time = data2["execution_time_ms"]
        
        # Cached query should be much faster
        assert cached_time < first_time * 0.1  # At least 10x faster