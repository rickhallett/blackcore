"""Tests for query API models."""

from datetime import datetime, timezone
from typing import Dict, Any

import pytest
from pydantic import ValidationError

from blackcore.minimal.api.query_models import (
    QueryFilter,
    SortField,
    PaginationParams,
    QueryRequest,
    QueryResponse,
    TextSearchRequest,
    TextSearchResponse,
    ExportRequest,
    ExportJob,
    QueryEstimateRequest,
    QueryEstimateResponse,
    QueryStatsResponse,
)
from blackcore.minimal.query_engine.models import QueryOperator, ExportFormat


class TestQueryFilter:
    """Test QueryFilter model."""

    def test_query_filter_valid(self):
        """Test creating valid query filter."""
        filter_data = {
            "field": "Name",
            "operator": QueryOperator.EQUALS,
            "value": "John Doe"
        }
        qf = QueryFilter(**filter_data)
        
        assert qf.field == "Name"
        assert qf.operator == QueryOperator.EQUALS
        assert qf.value == "John Doe"
        assert qf.case_sensitive is True  # Default

    def test_query_filter_case_insensitive(self):
        """Test query filter with case sensitivity."""
        filter_data = {
            "field": "Email",
            "operator": QueryOperator.CONTAINS,
            "value": "example.com",
            "case_sensitive": False
        }
        qf = QueryFilter(**filter_data)
        
        assert qf.case_sensitive is False

    def test_query_filter_various_operators(self):
        """Test query filter with various operators."""
        operators = [
            QueryOperator.EQUALS,
            QueryOperator.NOT_EQUALS,
            QueryOperator.CONTAINS,
            QueryOperator.IN,
            QueryOperator.NOT_IN,
            QueryOperator.GT,
            QueryOperator.LT,
            QueryOperator.BETWEEN,
            QueryOperator.IS_NULL,
        ]
        
        for op in operators:
            qf = QueryFilter(field="test", operator=op, value="value")
            assert qf.operator == op

    def test_query_filter_missing_required_fields(self):
        """Test query filter validation with missing fields."""
        with pytest.raises(ValidationError) as exc_info:
            QueryFilter(field="Name")  # Missing operator and value
        
        errors = exc_info.value.errors()
        assert len(errors) == 2
        assert any(e["loc"] == ("operator",) for e in errors)
        assert any(e["loc"] == ("value",) for e in errors)


class TestSortField:
    """Test SortField model."""

    def test_sort_field_default_order(self):
        """Test sort field with default order."""
        sf = SortField(field="created_at")
        
        assert sf.field == "created_at"
        assert sf.order == "asc"  # Default

    def test_sort_field_desc_order(self):
        """Test sort field with descending order."""
        sf = SortField(field="priority", order="desc")
        
        assert sf.field == "priority"
        assert sf.order == "desc"

    def test_sort_field_invalid_order(self):
        """Test sort field with invalid order."""
        with pytest.raises(ValidationError) as exc_info:
            SortField(field="test", order="invalid")
        
        errors = exc_info.value.errors()
        assert any("order" in str(e) for e in errors)


class TestPaginationParams:
    """Test PaginationParams model."""

    def test_pagination_defaults(self):
        """Test pagination with default values."""
        pp = PaginationParams()
        
        assert pp.page == 1
        assert pp.size == 100

    def test_pagination_custom_values(self):
        """Test pagination with custom values."""
        pp = PaginationParams(page=5, size=50)
        
        assert pp.page == 5
        assert pp.size == 50

    def test_pagination_validation(self):
        """Test pagination validation."""
        # Page must be >= 1
        with pytest.raises(ValidationError):
            PaginationParams(page=0)
        
        # Size must be between 1 and 1000
        with pytest.raises(ValidationError):
            PaginationParams(size=0)
        
        with pytest.raises(ValidationError):
            PaginationParams(size=1001)

    def test_pagination_edge_cases(self):
        """Test pagination edge cases."""
        # Minimum valid values
        pp = PaginationParams(page=1, size=1)
        assert pp.page == 1
        assert pp.size == 1
        
        # Maximum size
        pp = PaginationParams(page=1000, size=1000)
        assert pp.page == 1000
        assert pp.size == 1000


class TestQueryRequest:
    """Test QueryRequest model."""

    def test_query_request_minimal(self):
        """Test minimal query request."""
        qr = QueryRequest(database="People & Contacts")
        
        assert qr.database == "People & Contacts"
        assert qr.filters == []
        assert qr.sort_fields == []
        assert qr.includes == []
        assert qr.distinct is False
        assert isinstance(qr.pagination, PaginationParams)

    def test_query_request_full(self):
        """Test full query request."""
        qr = QueryRequest(
            database="Actionable Tasks",
            filters=[
                QueryFilter(
                    field="Status",
                    operator=QueryOperator.IN,
                    value=["Pending", "In Progress"]
                )
            ],
            sort_fields=[
                SortField(field="Priority", order="desc"),
                SortField(field="Created", order="asc")
            ],
            includes=["assignee", "project"],
            pagination=PaginationParams(page=2, size=25),
            distinct=True
        )
        
        assert qr.database == "Actionable Tasks"
        assert len(qr.filters) == 1
        assert qr.filters[0].field == "Status"
        assert len(qr.sort_fields) == 2
        assert qr.includes == ["assignee", "project"]
        assert qr.pagination.page == 2
        assert qr.pagination.size == 25
        assert qr.distinct is True

    def test_query_request_json_schema_example(self):
        """Test that the JSON schema example is valid."""
        example = QueryRequest.model_config["json_schema_extra"]["example"]
        qr = QueryRequest(**example)
        
        assert qr.database == "People & Contacts"
        assert qr.filters[0].field == "Organization"
        assert qr.filters[0].operator == "contains"
        assert qr.sort_fields[0].field == "Full Name"


class TestQueryResponse:
    """Test QueryResponse model."""

    def test_query_response_minimal(self):
        """Test minimal query response."""
        qr = QueryResponse(
            data=[{"id": 1, "name": "Test"}],
            total_count=1,
            page=1,
            page_size=100,
            execution_time_ms=12.5
        )
        
        assert len(qr.data) == 1
        assert qr.total_count == 1
        assert qr.from_cache is False  # Default
        assert qr.links == {}  # Default

    def test_query_response_cached(self):
        """Test cached query response."""
        qr = QueryResponse(
            data=[],
            total_count=0,
            page=1,
            page_size=50,
            execution_time_ms=0.5,
            from_cache=True,
            links={
                "self": "/api/query?page=1",
                "next": "/api/query?page=2"
            }
        )
        
        assert qr.from_cache is True
        assert qr.execution_time_ms == 0.5
        assert "self" in qr.links
        assert "next" in qr.links


class TestTextSearchRequest:
    """Test TextSearchRequest model."""

    def test_text_search_minimal(self):
        """Test minimal text search request."""
        tsr = TextSearchRequest(query_text="beach huts")
        
        assert tsr.query_text == "beach huts"
        assert tsr.databases is None  # Search all
        assert tsr.max_results == 100  # Default
        assert tsr.similarity_threshold == 0.7  # Default

    def test_text_search_full(self):
        """Test full text search request."""
        tsr = TextSearchRequest(
            query_text="council meeting",
            databases=["Intelligence & Transcripts", "Documents & Evidence"],
            max_results=50,
            similarity_threshold=0.85
        )
        
        assert tsr.query_text == "council meeting"
        assert len(tsr.databases) == 2
        assert tsr.max_results == 50
        assert tsr.similarity_threshold == 0.85

    def test_text_search_validation(self):
        """Test text search validation."""
        # Max results must be between 1 and 1000
        with pytest.raises(ValidationError):
            TextSearchRequest(query_text="test", max_results=0)
        
        with pytest.raises(ValidationError):
            TextSearchRequest(query_text="test", max_results=1001)
        
        # Similarity threshold must be between 0 and 1
        with pytest.raises(ValidationError):
            TextSearchRequest(query_text="test", similarity_threshold=-0.1)
        
        with pytest.raises(ValidationError):
            TextSearchRequest(query_text="test", similarity_threshold=1.1)


class TestTextSearchResponse:
    """Test TextSearchResponse model."""

    def test_text_search_response(self):
        """Test text search response."""
        tsr = TextSearchResponse(
            matches=[
                {"id": "1", "title": "Beach Meeting", "score": 0.92},
                {"id": "2", "title": "Council Notes", "score": 0.85}
            ],
            query_text="beach council",
            execution_time_ms=45.2,
            total_matches=2
        )
        
        assert len(tsr.matches) == 2
        assert tsr.query_text == "beach council"
        assert tsr.execution_time_ms == 45.2
        assert tsr.total_matches == 2


class TestExportRequest:
    """Test ExportRequest model."""

    def test_export_request_minimal(self):
        """Test minimal export request."""
        query = QueryRequest(database="People & Contacts")
        er = ExportRequest(
            query=query,
            format=ExportFormat.CSV
        )
        
        assert er.query.database == "People & Contacts"
        assert er.format == ExportFormat.CSV
        assert er.options == {}
        assert er.template_name is None

    def test_export_request_with_options(self):
        """Test export request with options."""
        query = QueryRequest(database="Actionable Tasks")
        er = ExportRequest(
            query=query,
            format=ExportFormat.EXCEL,
            options={
                "include_headers": True,
                "sheet_name": "Tasks",
                "date_format": "YYYY-MM-DD"
            },
            template_name="task_report"
        )
        
        assert er.format == ExportFormat.EXCEL
        assert er.options["include_headers"] is True
        assert er.options["sheet_name"] == "Tasks"
        assert er.template_name == "task_report"

    def test_export_request_json_schema_example(self):
        """Test that the JSON schema example is valid."""
        example = ExportRequest.model_config["json_schema_extra"]["example"]
        er = ExportRequest(**example)
        
        assert er.format == "excel"
        assert er.query.filters[0].field == "Status"


class TestExportJob:
    """Test ExportJob model."""

    def test_export_job_pending(self):
        """Test pending export job."""
        now = datetime.now(timezone.utc)
        job = ExportJob(
            job_id="export-123",
            status="pending",
            created_at=now,
            format=ExportFormat.CSV,
            progress=0
        )
        
        assert job.job_id == "export-123"
        assert job.status == "pending"
        assert job.started_at is None
        assert job.completed_at is None
        assert job.rows_exported is None
        assert job.download_url is None

    def test_export_job_completed(self):
        """Test completed export job."""
        created = datetime.now(timezone.utc)
        started = created.replace(microsecond=0)
        completed = started.replace(microsecond=0)
        from datetime import timedelta
        expires = completed + timedelta(hours=24)
        
        job = ExportJob(
            job_id="export-456",
            status="completed",
            created_at=created,
            started_at=started,
            completed_at=completed,
            format=ExportFormat.EXCEL,
            rows_exported=1500,
            file_size_bytes=2048000,
            download_url="/downloads/export-456.xlsx",
            expires_at=expires,
            progress=100
        )
        
        assert job.status == "completed"
        assert job.rows_exported == 1500
        assert job.file_size_bytes == 2048000
        assert job.download_url == "/downloads/export-456.xlsx"
        assert job.progress == 100

    def test_export_job_failed(self):
        """Test failed export job."""
        now = datetime.now(timezone.utc)
        job = ExportJob(
            job_id="export-789",
            status="failed",
            created_at=now,
            started_at=now,
            format=ExportFormat.JSON,
            error_message="Database connection timeout",
            progress=25
        )
        
        assert job.status == "failed"
        assert job.error_message == "Database connection timeout"
        assert job.progress == 25
        assert job.download_url is None

    def test_export_job_progress_validation(self):
        """Test export job progress validation."""
        now = datetime.now(timezone.utc)
        
        # Progress must be between 0 and 100
        with pytest.raises(ValidationError):
            ExportJob(
                job_id="test",
                status="running",
                created_at=now,
                format=ExportFormat.CSV,
                progress=-1
            )
        
        with pytest.raises(ValidationError):
            ExportJob(
                job_id="test",
                status="running",
                created_at=now,
                format=ExportFormat.CSV,
                progress=101
            )


class TestQueryEstimateRequest:
    """Test QueryEstimateRequest model."""

    def test_query_estimate_minimal(self):
        """Test minimal query estimate request."""
        qer = QueryEstimateRequest(database="Organizations & Bodies")
        
        assert qer.database == "Organizations & Bodies"
        assert qer.filters == []
        assert qer.includes == []

    def test_query_estimate_with_filters(self):
        """Test query estimate with filters."""
        qer = QueryEstimateRequest(
            database="People & Contacts",
            filters=[
                QueryFilter(field="City", operator=QueryOperator.EQUALS, value="London"),
                QueryFilter(field="Active", operator=QueryOperator.EQUALS, value=True)
            ],
            includes=["organization", "tasks"]
        )
        
        assert len(qer.filters) == 2
        assert qer.filters[0].field == "City"
        assert qer.includes == ["organization", "tasks"]


class TestQueryEstimateResponse:
    """Test QueryEstimateResponse model."""

    def test_query_estimate_response(self):
        """Test query estimate response."""
        qer = QueryEstimateResponse(
            estimated_rows=1250,
            estimated_cost=0.025,
            estimated_time_ms=150.5,
            optimization_hints=["Consider adding index on 'City' field"],
            suggested_indexes=["idx_people_city", "idx_people_active"]
        )
        
        assert qer.estimated_rows == 1250
        assert qer.estimated_cost == 0.025
        assert qer.estimated_time_ms == 150.5
        assert len(qer.optimization_hints) == 1
        assert len(qer.suggested_indexes) == 2


class TestQueryStatsResponse:
    """Test QueryStatsResponse model."""

    def test_query_stats_minimal(self):
        """Test minimal query stats response."""
        qsr = QueryStatsResponse(
            total_queries=1000,
            cache_hit_rate=0.75,
            average_execution_time_ms=45.3
        )
        
        assert qsr.total_queries == 1000
        assert qsr.cache_hit_rate == 0.75
        assert qsr.average_execution_time_ms == 45.3
        assert qsr.popular_databases == {}
        assert qsr.popular_filters == {}
        assert qsr.cache_statistics == {}

    def test_query_stats_full(self):
        """Test full query stats response."""
        qsr = QueryStatsResponse(
            total_queries=15234,
            cache_hit_rate=0.82,
            average_execution_time_ms=34.2,
            popular_databases={
                "People & Contacts": 4521,
                "Actionable Tasks": 3876,
                "Organizations & Bodies": 2341
            },
            popular_filters={
                "Status": 8234,
                "Organization": 5123,
                "Priority": 3456
            },
            cache_statistics={
                "memory_hit_rate": 0.75,
                "redis_hit_rate": 0.15,
                "disk_hit_rate": 0.05,
                "miss_rate": 0.05
            }
        )
        
        assert qsr.total_queries == 15234
        assert len(qsr.popular_databases) == 3
        assert qsr.popular_databases["People & Contacts"] == 4521
        assert len(qsr.popular_filters) == 3
        assert qsr.cache_statistics["memory_hit_rate"] == 0.75

    def test_query_stats_json_schema_example(self):
        """Test that the JSON schema example is valid."""
        example = QueryStatsResponse.model_config["json_schema_extra"]["example"]
        qsr = QueryStatsResponse(**example)
        
        assert qsr.total_queries == 15234
        assert qsr.cache_hit_rate == 0.82


class TestModelSerialization:
    """Test model serialization and deserialization."""

    def test_query_request_json_round_trip(self):
        """Test QueryRequest JSON serialization round trip."""
        original = QueryRequest(
            database="Test DB",
            filters=[
                QueryFilter(field="name", operator=QueryOperator.CONTAINS, value="test")
            ],
            distinct=True
        )
        
        # Serialize to JSON
        json_str = original.model_dump_json()
        
        # Deserialize back
        restored = QueryRequest.model_validate_json(json_str)
        
        assert restored.database == original.database
        assert len(restored.filters) == len(original.filters)
        assert restored.filters[0].field == original.filters[0].field
        assert restored.distinct == original.distinct

    def test_export_job_datetime_serialization(self):
        """Test ExportJob datetime serialization."""
        now = datetime.now(timezone.utc)
        job = ExportJob(
            job_id="test-123",
            status="completed",
            created_at=now,
            started_at=now,
            completed_at=now,
            format=ExportFormat.CSV,
            progress=100
        )
        
        # Serialize to dict
        job_dict = job.model_dump()
        
        # Verify datetimes are serialized
        assert isinstance(job_dict["created_at"], datetime)
        
        # Serialize to JSON
        json_str = job.model_dump_json()
        
        # Deserialize back
        restored = ExportJob.model_validate_json(json_str)
        
        # Compare timestamps (allowing small difference due to serialization)
        assert abs((restored.created_at - job.created_at).total_seconds()) < 1