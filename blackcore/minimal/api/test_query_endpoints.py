"""Tests for query HTTP endpoints."""

import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, AsyncIterator
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import asyncio

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from fastapi.responses import StreamingResponse

from blackcore.minimal.api.query_endpoints import (
    router, query_service, 
    execute_structured_query, text_search, create_export,
    get_export_status, download_export, estimate_query,
    get_query_statistics, list_databases, get_database_fields
)
from blackcore.minimal.api.query_models import (
    QueryRequest, QueryResponse, QueryFilter,
    TextSearchRequest, TextSearchResponse,
    ExportRequest, ExportJob,
    QueryEstimateRequest, QueryEstimateResponse,
    QueryStatsResponse
)
from blackcore.minimal.query_engine.models import QueryOperator, ExportFormat


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return {
        "sub": "user123",
        "username": "testuser",
        "scopes": ["read", "write"],
        "type": "user"
    }


@pytest.fixture
def mock_admin_user():
    """Mock admin user."""
    return {
        "sub": "admin123",
        "username": "admin",
        "scopes": ["admin", "read", "write"],
        "type": "admin"
    }


class TestStructuredQueryEndpoint:
    """Test structured query endpoint."""

    @pytest.mark.asyncio
    async def test_execute_structured_query_success(self, mock_user):
        """Test successful structured query execution."""
        # Setup request
        request = QueryRequest(
            database="People & Contacts",
            filters=[
                QueryFilter(field="City", operator=QueryOperator.EQUALS, value="London")
            ]
        )
        
        # Mock response
        mock_response = QueryResponse(
            data=[{"id": "1", "name": "John Doe"}],
            total_count=1,
            page=1,
            page_size=100,
            execution_time_ms=25.5,
            from_cache=False
        )
        
        # Mock service
        with patch.object(query_service, 'execute_query', AsyncMock(return_value=mock_response)) as mock_execute:
            response = await execute_structured_query(request, mock_user)
        
        assert response == mock_response
        mock_execute.assert_called_once_with(request, mock_user)

    @pytest.mark.asyncio
    async def test_execute_structured_query_http_exception(self, mock_user):
        """Test structured query with HTTP exception."""
        request = QueryRequest(database="Invalid DB")
        
        # Mock service to raise HTTPException
        with patch.object(query_service, 'execute_query', AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Database not found")
        )):
            with pytest.raises(HTTPException) as exc_info:
                await execute_structured_query(request, mock_user)
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Database not found"

    @pytest.mark.asyncio
    async def test_execute_structured_query_generic_exception(self, mock_user):
        """Test structured query with generic exception."""
        request = QueryRequest(database="Test DB")
        
        # Mock service to raise generic exception
        with patch.object(query_service, 'execute_query', AsyncMock(
            side_effect=Exception("Unexpected error")
        )):
            with pytest.raises(HTTPException) as exc_info:
                await execute_structured_query(request, mock_user)
        
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Query execution failed"


class TestTextSearchEndpoint:
    """Test text search endpoint."""

    @pytest.mark.asyncio
    async def test_text_search_success(self, mock_user):
        """Test successful text search."""
        request = TextSearchRequest(
            query_text="beach council meeting",
            databases=["Intelligence & Transcripts"],
            max_results=10
        )
        
        mock_response = TextSearchResponse(
            matches=[
                {"entity_id": "1", "similarity_score": 0.95, "matched_content": "beach council..."}
            ],
            query_text="beach council meeting",
            execution_time_ms=50.0,
            total_matches=1
        )
        
        with patch.object(query_service, 'text_search', AsyncMock(return_value=mock_response)) as mock_search:
            response = await text_search(request, mock_user)
        
        assert response == mock_response
        assert len(response.matches) == 1
        mock_search.assert_called_once_with(request, mock_user)

    @pytest.mark.asyncio
    async def test_text_search_exception_handling(self, mock_user):
        """Test text search exception handling."""
        request = TextSearchRequest(query_text="test")
        
        with patch.object(query_service, 'text_search', AsyncMock(
            side_effect=Exception("Search failed")
        )):
            with pytest.raises(HTTPException) as exc_info:
                await text_search(request, mock_user)
        
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Text search failed"


class TestExportEndpoints:
    """Test export-related endpoints."""

    @pytest.mark.asyncio
    async def test_create_export_success(self, mock_user):
        """Test successful export job creation."""
        query_req = QueryRequest(database="Actionable Tasks")
        request = ExportRequest(
            query=query_req,
            format=ExportFormat.CSV
        )
        
        mock_job = ExportJob(
            job_id="export-123",
            status="pending",
            created_at=datetime.now(timezone.utc),
            format=ExportFormat.CSV,
            progress=0
        )
        
        with patch.object(query_service, 'create_export', AsyncMock(return_value=mock_job)) as mock_create:
            response = await create_export(request, mock_user)
        
        assert response.job_id == "export-123"
        assert response.download_url == "/api/v1/query/export/export-123/download"
        mock_create.assert_called_once_with(request, mock_user)

    @pytest.mark.asyncio
    async def test_get_export_status_success(self, mock_user):
        """Test getting export job status."""
        job_id = "export-123"
        
        mock_job = ExportJob(
            job_id=job_id,
            status="completed",
            created_at=datetime.now(timezone.utc),
            format=ExportFormat.CSV,
            progress=100,
            rows_exported=1500
        )
        
        with patch.object(query_service, 'get_export_status', AsyncMock(return_value=mock_job)):
            response = await get_export_status(job_id, mock_user)
        
        assert response.job_id == job_id
        assert response.status == "completed"

    @pytest.mark.asyncio
    async def test_get_export_status_not_found(self, mock_user):
        """Test export status when job not found."""
        job_id = "nonexistent"
        
        with patch.object(query_service, 'get_export_status', AsyncMock(return_value=None)):
            with pytest.raises(HTTPException) as exc_info:
                await get_export_status(job_id, mock_user)
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Export job not found"

    @pytest.mark.asyncio
    async def test_download_export_success(self, mock_user):
        """Test successful export download."""
        job_id = "export-123"
        
        # Mock completed job
        mock_job = ExportJob(
            job_id=job_id,
            status="completed",
            created_at=datetime.now(timezone.utc),
            format=ExportFormat.CSV,
            progress=100
        )
        
        # Mock file stream
        async def mock_stream():
            yield b"header1,header2\n"
            yield b"value1,value2\n"
        
        with patch.object(query_service, 'get_export_status', AsyncMock(return_value=mock_job)):
            with patch.object(query_service, 'download_export', AsyncMock(return_value=mock_stream())):
                response = await download_export(job_id, mock_user)
        
        assert isinstance(response, StreamingResponse)
        assert response.media_type == "text/csv"
        assert response.headers["Content-Disposition"] == f'attachment; filename="export_{job_id}.csv"'

    @pytest.mark.asyncio
    async def test_download_export_not_ready(self, mock_user):
        """Test download when export not ready."""
        job_id = "export-123"
        
        # Mock pending job
        mock_job = ExportJob(
            job_id=job_id,
            status="processing",
            created_at=datetime.now(timezone.utc),
            format=ExportFormat.CSV,
            progress=50
        )
        
        with patch.object(query_service, 'get_export_status', AsyncMock(return_value=mock_job)):
            with pytest.raises(HTTPException) as exc_info:
                await download_export(job_id, mock_user)
        
        assert exc_info.value.status_code == 400
        assert "Export not ready" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_download_export_various_formats(self, mock_user):
        """Test download with various export formats."""
        formats_and_types = [
            (ExportFormat.CSV, "text/csv"),
            (ExportFormat.JSON, "application/json"),
            (ExportFormat.EXCEL, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            (ExportFormat.PARQUET, "application/octet-stream"),
        ]
        
        for export_format, expected_type in formats_and_types:
            job_id = f"export-{export_format}"
            
            mock_job = ExportJob(
                job_id=job_id,
                status="completed",
                created_at=datetime.now(timezone.utc),
                format=export_format,
                progress=100
            )
            
            async def mock_stream():
                yield b"test data"
            
            with patch.object(query_service, 'get_export_status', AsyncMock(return_value=mock_job)):
                with patch.object(query_service, 'download_export', AsyncMock(return_value=mock_stream())):
                    response = await download_export(job_id, mock_user)
            
            assert response.media_type == expected_type


class TestEstimateEndpoint:
    """Test query estimation endpoint."""

    @pytest.mark.asyncio
    async def test_estimate_query_success(self, mock_user):
        """Test successful query estimation."""
        request = QueryEstimateRequest(
            database="People & Contacts",
            filters=[
                QueryFilter(field="City", operator=QueryOperator.EQUALS, value="London")
            ]
        )
        
        mock_response = QueryEstimateResponse(
            estimated_rows=1500,
            estimated_cost=0.025,
            estimated_time_ms=150.0,
            optimization_hints=["Consider adding index on City"],
            suggested_indexes=["idx_people_city"]
        )
        
        with patch.object(query_service, 'estimate_query', AsyncMock(return_value=mock_response)):
            response = await estimate_query(request, mock_user)
        
        assert response.estimated_rows == 1500
        assert response.estimated_cost == 0.025
        assert len(response.suggested_indexes) == 1

    @pytest.mark.asyncio
    async def test_estimate_query_exception(self, mock_user):
        """Test query estimation with exception."""
        request = QueryEstimateRequest(database="Test DB")
        
        with patch.object(query_service, 'estimate_query', AsyncMock(
            side_effect=Exception("Estimation failed")
        )):
            with pytest.raises(HTTPException) as exc_info:
                await estimate_query(request, mock_user)
        
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Query estimation failed"


class TestStatisticsEndpoint:
    """Test statistics endpoint."""

    @pytest.mark.asyncio
    async def test_get_query_statistics_success(self, mock_user):
        """Test getting query statistics."""
        mock_stats = QueryStatsResponse(
            total_queries=5000,
            cache_hit_rate=0.85,
            average_execution_time_ms=42.3,
            popular_databases={
                "People & Contacts": 1500,
                "Actionable Tasks": 1200
            },
            popular_filters={
                "Status": 800,
                "City": 600
            }
        )
        
        with patch.object(query_service, 'get_statistics', AsyncMock(return_value=mock_stats)):
            response = await get_query_statistics(mock_user)
        
        assert response.total_queries == 5000
        assert response.cache_hit_rate == 0.85
        assert len(response.popular_databases) == 2

    @pytest.mark.asyncio
    async def test_get_query_statistics_exception(self, mock_user):
        """Test statistics with exception."""
        with patch.object(query_service, 'get_statistics', AsyncMock(
            side_effect=Exception("Stats failed")
        )):
            with pytest.raises(HTTPException) as exc_info:
                await get_query_statistics(mock_user)
        
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to get statistics"


class TestDatabaseEndpoints:
    """Test database listing endpoints."""

    @pytest.mark.asyncio
    async def test_list_databases_success(self, mock_user):
        """Test listing available databases."""
        mock_databases = [
            {"name": "People & Contacts", "record_count": 1500},
            {"name": "Actionable Tasks", "record_count": 800}
        ]
        
        with patch.object(query_service, 'get_available_databases', AsyncMock(return_value=mock_databases)):
            response = await list_databases(mock_user)
        
        assert response["total"] == 2
        assert len(response["databases"]) == 2
        assert response["databases"][0]["name"] == "People & Contacts"

    @pytest.mark.asyncio
    async def test_list_databases_exception(self, mock_user):
        """Test database listing with exception."""
        with patch.object(query_service, 'get_available_databases', AsyncMock(
            side_effect=Exception("Failed to list")
        )):
            with pytest.raises(HTTPException) as exc_info:
                await list_databases(mock_user)
        
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to get database list"

    @pytest.mark.asyncio
    async def test_get_database_fields_success(self, mock_user):
        """Test getting database fields."""
        database = "People & Contacts"
        
        response = await get_database_fields(database, mock_user)
        
        assert response["database"] == database
        assert response["total"] == 5
        assert any(field["name"] == "Full Name" for field in response["fields"])

    @pytest.mark.asyncio
    async def test_get_database_fields_not_found(self, mock_user):
        """Test getting fields for unknown database."""
        database = "Unknown Database"
        
        with pytest.raises(HTTPException) as exc_info:
            await get_database_fields(database, mock_user)
        
        assert exc_info.value.status_code == 404
        assert f"Database '{database}' not found" in exc_info.value.detail


class TestIntegrationWithFastAPI:
    """Test endpoints integration with FastAPI."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_structured_query_endpoint_exists(self, client):
        """Test that structured query endpoint is registered."""
        # This will fail with 401 since we don't provide auth
        response = client.post("/api/v1/query/structured", json={
            "database": "Test",
            "filters": []
        })
        # Should get 401 Unauthorized, not 404
        assert response.status_code in [401, 403, 422]  # 401 Unauthorized, 403 Forbidden (rate limit), 422 Validation

    def test_export_endpoints_exist(self, client):
        """Test that export endpoints are registered."""
        # Test create export
        response = client.post("/api/v1/query/export", json={
            "query": {"database": "Test"},
            "format": "csv"
        })
        assert response.status_code in [401, 403, 422]
        
        # Test get status
        response = client.get("/api/v1/query/export/test-id")
        assert response.status_code in [401, 403, 422]
        
        # Test download
        response = client.get("/api/v1/query/export/test-id/download")
        assert response.status_code in [401, 403, 422]

    def test_utility_endpoints_exist(self, client):
        """Test that utility endpoints are registered."""
        # Test statistics
        response = client.get("/api/v1/query/stats")
        assert response.status_code in [401, 403, 422]
        
        # Test databases list
        response = client.get("/api/v1/query/databases")
        assert response.status_code in [401, 403, 422]
        
        # Test database fields
        response = client.get("/api/v1/query/fields/TestDB")
        assert response.status_code in [401, 403, 422]


class TestEndpointLogging:
    """Test endpoint logging behavior."""

    @pytest.mark.asyncio
    async def test_structured_query_logging(self, mock_user):
        """Test that structured query logs properly."""
        request = QueryRequest(database="Test DB")
        
        with patch('blackcore.minimal.api.query_endpoints.logger') as mock_logger:
            with patch.object(query_service, 'execute_query', AsyncMock(
                return_value=QueryResponse(
                    data=[], total_count=0, page=1, page_size=100, execution_time_ms=10.0
                )
            )):
                await execute_structured_query(request, mock_user)
        
        mock_logger.info.assert_called_with(
            "Structured query request",
            database="Test DB",
            user_id="user123"
        )

    @pytest.mark.asyncio
    async def test_text_search_query_truncation(self, mock_user):
        """Test that long search queries are truncated in logs."""
        long_query = "a" * 100
        request = TextSearchRequest(query_text=long_query)
        
        with patch('blackcore.minimal.api.query_endpoints.logger') as mock_logger:
            with patch.object(query_service, 'text_search', AsyncMock(
                return_value=TextSearchResponse(
                    matches=[], query_text=long_query, execution_time_ms=10.0, total_matches=0
                )
            )):
                await text_search(request, mock_user)
        
        # Should only log first 50 characters
        mock_logger.info.assert_called_with(
            "Text search request",
            query="a" * 50,
            user_id="user123"
        )

    @pytest.mark.asyncio
    async def test_error_logging(self, mock_user):
        """Test that errors are logged properly."""
        request = QueryRequest(database="Test DB")
        error_msg = "Database connection failed"
        
        with patch('blackcore.minimal.api.query_endpoints.logger') as mock_logger:
            with patch.object(query_service, 'execute_query', AsyncMock(
                side_effect=Exception(error_msg)
            )):
                with pytest.raises(HTTPException):
                    await execute_structured_query(request, mock_user)
        
        mock_logger.error.assert_called_with(f"Query execution failed: {error_msg}")