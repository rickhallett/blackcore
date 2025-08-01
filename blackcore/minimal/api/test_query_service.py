"""Tests for query service layer."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch, MagicMock, mock_open

import pytest
import pytest_asyncio
from fastapi import HTTPException

from blackcore.minimal.api.query_service import QueryService
from blackcore.minimal.api.query_models import (
    QueryRequest, QueryResponse, QueryFilter, SortField, PaginationParams,
    TextSearchRequest, TextSearchResponse,
    ExportRequest, ExportJob, 
    QueryEstimateRequest, QueryEstimateResponse,
    QueryStatsResponse
)
from blackcore.minimal.query_engine.models import QueryOperator, ExportFormat


class TestQueryServiceInitialization:
    """Test QueryService initialization."""

    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """Test service initializes correctly."""
        config = {"query_engine": {"cache": True}}
        service = QueryService(config)
        
        assert service.config == config
        assert service._initialized is False
        
        # Mock the factory and components
        with patch("blackcore.minimal.api.query_service.QueryEngineFactory") as mock_factory:
            with patch("blackcore.minimal.api.query_service.ExportManager"):
                with patch("blackcore.minimal.api.query_service.ExportJobManager") as mock_job_mgr:
                    mock_job_mgr.return_value.start = AsyncMock()
                    
                    await service.initialize()
        
        assert service._initialized is True
        assert service.engine is not None
        assert service.export_manager is not None

    @pytest.mark.asyncio
    async def test_service_initializes_once(self):
        """Test service only initializes once."""
        service = QueryService()
        
        with patch("blackcore.minimal.api.query_service.QueryEngineFactory") as mock_factory:
            with patch("blackcore.minimal.api.query_service.ExportManager"):
                with patch("blackcore.minimal.api.query_service.ExportJobManager") as mock_job_mgr:
                    mock_job_mgr.return_value.start = AsyncMock()
                    
                    await service.initialize()
                    await service.initialize()  # Second call
        
        # Factory should only be called once
        assert mock_factory.create_structured_executor.call_count == 1


class TestQueryExecution:
    """Test query execution functionality."""

    @pytest_asyncio.fixture
    async def service(self):
        """Create initialized query service."""
        service = QueryService()
        
        # Mock all components
        service.engine = Mock()
        service.engine.execute_structured_query_async = AsyncMock()
        service.export_manager = Mock()
        service.export_job_manager = Mock()
        service.stats_collector = Mock()
        service.optimizer = Mock()
        service._initialized = True
        
        return service

    @pytest.mark.asyncio
    async def test_execute_query_success(self, service):
        """Test successful query execution."""
        # Setup request
        request = QueryRequest(
            database="People & Contacts",
            filters=[
                QueryFilter(field="City", operator=QueryOperator.EQUALS, value="London")
            ],
            pagination=PaginationParams(page=1, size=50)
        )
        
        user = {"sub": "user123", "scopes": ["read"]}
        
        # Mock engine response
        mock_result = Mock()
        mock_result.data = [{"id": 1, "name": "John"}]
        mock_result.total_count = 1
        mock_result.page = 1
        mock_result.page_size = 50
        mock_result.execution_time_ms = 25.5
        mock_result.from_cache = False
        
        service.engine.execute_structured_query_async.return_value = mock_result
        
        # Mock database validation
        with patch.object(service, "get_available_databases", AsyncMock(return_value=[
            {"name": "People & Contacts"}
        ])):
            response = await service.execute_query(request, user)
        
        assert isinstance(response, QueryResponse)
        assert response.data == [{"id": 1, "name": "John"}]
        assert response.total_count == 1
        assert response.execution_time_ms == 25.5
        assert response.from_cache is False

    @pytest.mark.asyncio
    async def test_execute_query_database_not_found(self, service):
        """Test query execution with invalid database."""
        request = QueryRequest(
            database="Invalid Database",
            pagination=PaginationParams()
        )
        user = {"sub": "user123", "scopes": ["read"]}
        
        # Mock database validation to fail
        with patch.object(service, "get_available_databases", AsyncMock(return_value=[])):
            with pytest.raises(HTTPException) as exc_info:
                await service.execute_query(request, user)
        
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_execute_query_expensive_check(self, service):
        """Test expensive query detection."""
        # Create query with too many filters
        request = QueryRequest(
            database="People & Contacts",
            filters=[
                QueryFilter(field=f"field{i}", operator=QueryOperator.EQUALS, value=i)
                for i in range(25)  # More than 20 filters
            ]
        )
        user = {"sub": "user123", "scopes": ["read"]}
        
        with patch.object(service, "get_available_databases", AsyncMock(return_value=[
            {"name": "People & Contacts"}
        ])):
            with pytest.raises(HTTPException) as exc_info:
                await service.execute_query(request, user)
        
        assert exc_info.value.status_code == 400
        assert "too complex" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_execute_query_with_statistics(self, service):
        """Test query execution records statistics."""
        request = QueryRequest(
            database="People & Contacts",
            filters=[QueryFilter(field="City", operator=QueryOperator.EQUALS, value="NYC")]
        )
        user = {"sub": "user123", "scopes": ["read"]}
        
        # Mock response with cache tier
        mock_result = Mock()
        mock_result.data = []
        mock_result.total_count = 0
        mock_result.page = 1
        mock_result.page_size = 100
        mock_result.execution_time_ms = 10.0
        mock_result.from_cache = True
        mock_result.cache_tier = "memory"
        
        service.engine.execute_structured_query_async.return_value = mock_result
        
        with patch.object(service, "get_available_databases", AsyncMock(return_value=[
            {"name": "People & Contacts"}
        ])):
            await service.execute_query(request, user)
        
        # Verify statistics were recorded
        service.stats_collector.record_query.assert_called_once()
        service.stats_collector.update_cache_tier_hit.assert_called_with("memory")


class TestTextSearch:
    """Test text search functionality."""

    @pytest_asyncio.fixture
    async def service(self):
        """Create initialized query service."""
        service = QueryService()
        service.engine = Mock()
        service.engine.text_search_async = AsyncMock()
        service.stats_collector = Mock()
        service._initialized = True
        return service

    @pytest.mark.asyncio
    async def test_text_search_success(self, service):
        """Test successful text search."""
        request = TextSearchRequest(
            query_text="beach council",
            databases=["Intelligence & Transcripts"],
            max_results=10,
            similarity_threshold=0.8
        )
        user = {"sub": "user123", "scopes": ["read"]}
        
        # Mock search results
        mock_results = [
            {
                "id": "doc1",
                "_database": "Intelligence & Transcripts",
                "_score": 0.95,
                "properties": {
                    "title": {"title": [{"plain_text": "Beach Council Meeting"}]}
                }
            },
            {
                "id": "doc2",
                "_database": "Intelligence & Transcripts", 
                "_score": 0.75,  # Below threshold
                "properties": {}
            }
        ]
        
        service.engine.text_search_async.return_value = mock_results
        
        with patch.object(service, "_validate_access"):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop.return_value.time.side_effect = [1000.0, 1000.1]  # 100ms
                
                response = await service.text_search(request, user)
        
        assert isinstance(response, TextSearchResponse)
        assert len(response.matches) == 1  # Only one above threshold
        assert response.matches[0]["similarity_score"] == 0.95
        assert response.total_matches == 1
        assert abs(response.execution_time_ms - 100.0) < 0.1

    @pytest.mark.asyncio 
    async def test_text_search_all_databases(self, service):
        """Test text search across all databases."""
        request = TextSearchRequest(
            query_text="important",
            databases=None,  # Search all
            max_results=5
        )
        user = {"sub": "user123", "scopes": ["read"]}
        
        service.engine.text_search_async.return_value = []
        
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.time.side_effect = [1000.0, 1000.05]
            
            response = await service.text_search(request, user)
        
        # Should search all databases
        service.engine.text_search_async.assert_called_with("important", None)
        assert response.matches == []

    @pytest.mark.asyncio
    async def test_text_search_extract_snippet(self, service):
        """Test snippet extraction from search results."""
        request = TextSearchRequest(query_text="meeting agenda")
        user = {"sub": "user123", "scopes": ["read"]}
        
        # Mock result with matching text
        mock_results = [{
            "id": "doc1",
            "_database": "Intelligence & Transcripts",
            "_score": 0.9,
            "properties": {
                "content": {
                    "rich_text": [
                        {"plain_text": "The council discussed the "},
                        {"plain_text": "meeting agenda"},
                        {"plain_text": " for next month's session."}
                    ]
                }
            }
        }]
        
        service.engine.text_search_async.return_value = mock_results
        
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.time.side_effect = [1000.0, 1000.05]
            
            response = await service.text_search(request, user)
        
        assert len(response.matches) == 1
        match = response.matches[0]
        assert "meeting agenda" in match["matched_content"]


class TestExportFunctionality:
    """Test export functionality."""

    @pytest_asyncio.fixture
    async def service(self):
        """Create initialized query service."""
        service = QueryService()
        service.engine = Mock()
        service.export_job_manager = Mock()
        service.optimizer = Mock()
        service._initialized = True
        return service

    @pytest.mark.asyncio
    async def test_create_export_success(self, service):
        """Test successful export creation."""
        query = QueryRequest(database="Actionable Tasks")
        request = ExportRequest(
            query=query,
            format=ExportFormat.CSV
        )
        user = {"sub": "user123", "scopes": ["read"]}
        
        # Mock job creation
        mock_job = ExportJob(
            job_id="export-123",
            status="pending",
            created_at=datetime.now(),
            format=ExportFormat.CSV,
            progress=0
        )
        service.export_job_manager.create_export_job.return_value = mock_job
        
        # Mock size estimation
        service.optimizer.estimate_cost.return_value = 1000
        
        with patch.object(service, "_validate_access"):
            job = await service.create_export(request, user)
        
        assert job.job_id == "export-123"
        assert job.status == "pending"

    @pytest.mark.asyncio
    async def test_create_export_quota_exceeded(self, service):
        """Test export creation with quota exceeded."""
        query = QueryRequest(database="Large Database")
        request = ExportRequest(query=query, format=ExportFormat.JSON)
        user = {"sub": "user123", "scopes": ["read"], "rate_limit": 60}
        
        # Mock large size estimation
        service.optimizer.estimate_cost.return_value = 1000000  # Very large
        
        with patch.object(service, "_validate_access"):
            with pytest.raises(HTTPException) as exc_info:
                await service.create_export(request, user)
        
        assert exc_info.value.status_code == 400
        assert "quota" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_export_status(self, service):
        """Test getting export job status."""
        job_id = "export-123"
        user = {"sub": "user123"}
        
        mock_job = ExportJob(
            job_id=job_id,
            status="completed",
            created_at=datetime.now(),
            format=ExportFormat.CSV,
            progress=100
        )
        service.export_job_manager.get_job_status.return_value = mock_job
        
        job = await service.get_export_status(job_id, user)
        
        assert job.job_id == job_id
        assert job.status == "completed"

    @pytest.mark.asyncio
    async def test_download_export(self, service):
        """Test downloading export file."""
        job_id = "export-123"
        user = {"sub": "user123"}
        
        # Mock file stream
        async def mock_stream():
            yield b"data"
        
        service.export_job_manager.get_file_stream = AsyncMock(
            return_value=(mock_stream(), 1024)
        )
        
        stream = await service.download_export(job_id, user)
        
        assert stream is not None


class TestQueryEstimation:
    """Test query estimation functionality."""

    @pytest_asyncio.fixture
    async def service(self):
        """Create initialized query service."""
        service = QueryService()
        service.optimizer = Mock()
        service._initialized = True
        return service

    @pytest.mark.asyncio
    async def test_estimate_query(self, service):
        """Test query cost estimation."""
        request = QueryEstimateRequest(
            database="People & Contacts",
            filters=[
                QueryFilter(field="City", operator=QueryOperator.EQUALS, value="London")
            ]
        )
        user = {"sub": "user123"}
        
        # Mock optimizer responses
        service.optimizer.estimate_cost.return_value = 250.5
        service.optimizer.generate_execution_plan.return_value = {
            "estimated_rows": 1500
        }
        service.optimizer.suggest_indexes.return_value = [
            "idx_people_city",
            "idx_people_name"
        ]
        
        response = await service.estimate_query(request, user)
        
        assert isinstance(response, QueryEstimateResponse)
        assert response.estimated_rows == 1500
        assert response.estimated_cost == 250.5
        assert response.estimated_time_ms >= 25.05  # cost * 0.1
        assert len(response.suggested_indexes) == 2

    @pytest.mark.asyncio
    async def test_estimate_query_no_filters_hint(self, service):
        """Test estimation provides hints for queries without filters."""
        request = QueryEstimateRequest(
            database="Large Database",
            filters=[]
        )
        user = {"sub": "user123"}
        
        service.optimizer.estimate_cost.return_value = 1000
        service.optimizer.generate_execution_plan.return_value = {"estimated_rows": 10000}
        service.optimizer.suggest_indexes.return_value = []
        
        response = await service.estimate_query(request, user)
        
        assert any("Consider adding filters" in hint for hint in response.optimization_hints)


class TestStatistics:
    """Test statistics functionality."""

    @pytest_asyncio.fixture
    async def service(self):
        """Create initialized query service."""
        service = QueryService()
        service.stats_collector = Mock()
        service._initialized = True
        return service

    @pytest.mark.asyncio
    async def test_get_statistics(self, service):
        """Test getting query statistics."""
        # Mock statistics
        mock_stats = {
            "total_queries": 5000,
            "cache_hit_rate": 0.85,
            "average_execution_time_ms": 42.3,
            "popular_databases": {
                "People & Contacts": 1500,
                "Actionable Tasks": 1200
            },
            "popular_filters": {
                "Status": 800,
                "City": 600
            },
            "cache_statistics": {
                "memory_hit_rate": 0.7,
                "redis_hit_rate": 0.2,
                "disk_hit_rate": 0.1
            }
        }
        
        service.stats_collector.get_query_statistics.return_value = mock_stats
        
        response = await service.get_statistics()
        
        assert isinstance(response, QueryStatsResponse)
        assert response.total_queries == 5000
        assert response.cache_hit_rate == 0.85
        assert response.average_execution_time_ms == 42.3
        assert len(response.popular_databases) == 2
        assert response.cache_statistics["memory_hit_rate"] == 0.7


class TestHelperMethods:
    """Test helper methods."""

    def test_validate_access_admin(self):
        """Test access validation for admin users."""
        service = QueryService()
        service._initialized = True
        
        user = {"sub": "admin123", "scopes": ["admin"]}
        
        # Should not raise for admin accessing standard database
        service._validate_access("People & Contacts", user)

    def test_validate_access_regular_user(self):
        """Test access validation for regular users."""
        service = QueryService()
        service._initialized = True
        
        user = {"sub": "user123", "scopes": ["read"]}
        
        # Should not raise for allowed database
        service._validate_access("Actionable Tasks", user)

    def test_validate_access_no_permissions(self):
        """Test access validation with no permissions."""
        service = QueryService()
        service._initialized = True
        
        user = {"sub": "user123", "scopes": []}  # No scopes
        
        with pytest.raises(HTTPException) as exc_info:
            service._validate_access("Documents & Evidence", user)
        
        assert exc_info.value.status_code == 403

    def test_validate_access_unknown_database(self):
        """Test access validation with unknown database."""
        service = QueryService()
        service._initialized = True
        
        user = {"sub": "admin123", "scopes": ["admin"]}
        
        with pytest.raises(HTTPException) as exc_info:
            service._validate_access("Unknown Database", user)
        
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail

    def test_is_expensive_query_checks(self):
        """Test expensive query detection logic."""
        service = QueryService()
        
        # Too many filters
        request = QueryRequest(
            database="DB",
            filters=[QueryFilter(field=f"f{i}", operator="eq", value=i) for i in range(25)]
        )
        assert service._is_expensive_query(request) is True
        
        # Too many includes
        request = QueryRequest(
            database="DB",
            includes=["rel1", "rel2", "rel3", "rel4", "rel5", "rel6"]
        )
        assert service._is_expensive_query(request) is True
        
        # No filters with large page size
        request = QueryRequest(
            database="DB",
            filters=[],
            pagination=PaginationParams(size=200)
        )
        assert service._is_expensive_query(request) is True
        
        # Normal query
        request = QueryRequest(
            database="DB",
            filters=[QueryFilter(field="name", operator="eq", value="test")],
            pagination=PaginationParams(size=50)
        )
        assert service._is_expensive_query(request) is False

    def test_build_pagination_links(self):
        """Test pagination link building."""
        service = QueryService()
        
        request = QueryRequest(
            database="DB",
            pagination=PaginationParams(page=3, size=50)
        )
        
        links = service._build_pagination_links(request, total_count=500)
        
        assert "self" in links
        assert "first" in links
        assert "prev" in links
        assert "next" in links
        assert "last" in links
        
        assert "page=3" in links["self"]
        assert "page=1" in links["first"]
        assert "page=2" in links["prev"]
        assert "page=4" in links["next"]
        assert "page=10" in links["last"]

    def test_extract_match_snippet(self):
        """Test match snippet extraction."""
        service = QueryService()
        
        result = {
            "properties": {
                "content": {
                    "rich_text": [{
                        "plain_text": "This is a long text about beach council meetings and other topics that might be relevant for the discussion."
                    }]
                }
            }
        }
        
        snippet = service._extract_match_snippet(result, "council meetings")
        
        assert "council meetings" in snippet
        # Check that we have context around the match
        assert "beach" in snippet or "topics" in snippet

    def test_filename_to_database_name(self):
        """Test filename to database name conversion."""
        service = QueryService()
        
        # Test various conversions
        assert service._filename_to_database_name("people_and_contacts") == "People & Contacts"
        assert service._filename_to_database_name("actionable_tasks") == "Actionable Tasks"
        assert service._filename_to_database_name("intelligence_and_transcripts") == "Intelligence & Transcripts"

    def test_detect_field_type(self):
        """Test field type detection."""
        service = QueryService()
        
        # Test various field types
        assert service._detect_field_type({"title": []}) == "text"
        assert service._detect_field_type({"number": 123}) == "number"
        assert service._detect_field_type({"select": {"name": "Option"}}) == "select"
        assert service._detect_field_type({"date": {"start": "2024-01-01"}}) == "date"
        assert service._detect_field_type({"checkbox": True}) == "checkbox"
        assert service._detect_field_type({"relation": []}) == "relation"
        assert service._detect_field_type({}) == "text"  # Default


class TestDatabaseDiscovery:
    """Test database discovery functionality."""

    @pytest.mark.asyncio
    async def test_get_available_databases(self):
        """Test getting available databases from JSON files."""
        service = QueryService()
        
        # Mock file system
        mock_path = MagicMock()
        mock_json_file = MagicMock()
        mock_json_file.stem = "people_and_contacts"
        mock_json_file.name = "people_and_contacts.json"
        mock_json_file.stat.return_value.st_size = 1024
        mock_json_file.stat.return_value.st_mtime = 1234567890
        
        with patch("blackcore.minimal.api.query_service.Path") as mock_path_cls:
            mock_path_cls.return_value = mock_path
            mock_path.exists.return_value = True
            mock_path.glob.return_value = [mock_json_file]
            
            with patch("builtins.open", mock_open(read_data='[{"properties": {"name": {"title": []}}}]')):
                with patch("json.load", return_value=[{"properties": {"name": {"title": []}}}]):
                    databases = await service.get_available_databases()
        
        assert len(databases) == 1
        assert databases[0]["name"] == "People & Contacts"
        assert databases[0]["record_count"] == 1

    @pytest.mark.asyncio
    async def test_get_available_databases_no_cache_dir(self):
        """Test database discovery when cache dir doesn't exist."""
        service = QueryService()
        
        with patch("blackcore.minimal.api.query_service.Path") as mock_path_cls:
            mock_path = MagicMock()
            mock_path.exists.return_value = False
            mock_path_cls.return_value = mock_path
            
            databases = await service.get_available_databases()
        
        assert databases == []


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest_asyncio.fixture
    async def service(self):
        """Create initialized query service."""
        service = QueryService()
        service.engine = Mock()
        service._initialized = True
        return service

    @pytest.mark.asyncio
    async def test_query_execution_error_handling(self, service):
        """Test various error scenarios in query execution."""
        request = QueryRequest(database="Test DB")
        user = {"sub": "user123", "scopes": ["read"]}
        
        # Test "not found" error
        service.engine.execute_structured_query_async = AsyncMock(
            side_effect=Exception("Database 'Test DB' not found")
        )
        
        with patch.object(service, "_validate_access"):
            with pytest.raises(HTTPException) as exc_info:
                await service.execute_query(request, user)
        
        assert exc_info.value.status_code == 404
        
        # Test validation error
        service.engine.execute_structured_query_async = AsyncMock(
            side_effect=Exception("Query validation failed: invalid field")
        )
        
        with patch.object(service, "_validate_access"):
            with pytest.raises(HTTPException) as exc_info:
                await service.execute_query(request, user)
        
        assert exc_info.value.status_code == 400
        
        # Test generic error
        service.engine.execute_structured_query_async = AsyncMock(
            side_effect=Exception("Unknown error")
        )
        
        with patch.object(service, "_validate_access"):
            with pytest.raises(HTTPException) as exc_info:
                await service.execute_query(request, user)
        
        assert exc_info.value.status_code == 500


def mock_open(read_data=""):
    """Helper to create a mock for builtins.open."""
    import builtins
    from unittest.mock import mock_open as _mock_open
    
    return _mock_open(read_data=read_data)