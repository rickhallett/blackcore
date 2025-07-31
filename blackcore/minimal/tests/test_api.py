"""Comprehensive tests for the HTTP API."""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from blackcore.minimal.api.app import create_app
from blackcore.minimal.api.auth import auth_handler
from blackcore.minimal.api.models import (
    JobStatus,
    ProcessingJob,
    TranscriptProcessRequest,
    ProcessingOptions,
)
from blackcore.minimal.models import (
    TranscriptInput,
    ProcessingResult,
    Entity,
    EntityType,
)


@pytest.fixture
def test_app():
    """Create test FastAPI app."""
    # Reset rate limiter before each test
    from blackcore.minimal.api.auth import rate_limiter
    rate_limiter.requests.clear()
    
    app = create_app(title="Test API", version="test")
    return app


@pytest.fixture
def client(test_app):
    """Create test client."""
    return TestClient(test_app)


@pytest.fixture
def auth_token():
    """Generate test auth token."""
    token = auth_handler.create_access_token(
        data={"sub": "test_user", "type": "api_key"},
        expires_delta=timedelta(hours=1)
    )
    return token


@pytest.fixture
def admin_token():
    """Generate admin auth token."""
    token = auth_handler.create_access_token(
        data={"sub": "admin_user", "type": "api_key", "is_admin": True},
        expires_delta=timedelta(hours=1)
    )
    return token


@pytest.fixture
def headers(auth_token):
    """Auth headers for requests."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def admin_headers(admin_token):
    """Admin auth headers for requests."""
    return {"Authorization": f"Bearer {admin_token}"}


class TestHealthEndpoints:
    """Test health and status endpoints."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "version" in data
        assert "timestamp" in data
        assert "checks" in data
        
        # Check individual components
        assert "api" in data["checks"]
        assert data["checks"]["api"]["status"] == "healthy"


class TestAuthentication:
    """Test authentication endpoints and flows."""
    
    def test_generate_token(self, client):
        """Test token generation."""
        response = client.post(
            "/auth/token",
            json={"api_key": "test_api_key", "expires_in": 3600}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 3600
    
    def test_generate_token_invalid_key(self, client):
        """Test token generation with invalid key."""
        response = client.post(
            "/auth/token",
            json={"api_key": "", "expires_in": 3600}
        )
        
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["message"]
    
    def test_protected_endpoint_without_token(self, client):
        """Test accessing protected endpoint without token."""
        response = client.post(
            "/transcripts/process",
            json={"transcript": {"title": "Test", "content": "Content"}}
        )
        
        assert response.status_code == 403
        assert "Not authenticated" in response.json()["message"]
    
    def test_protected_endpoint_with_invalid_token(self, client):
        """Test accessing protected endpoint with invalid token."""
        headers = {"Authorization": "Bearer invalid_token"}
        
        response = client.post(
            "/transcripts/process",
            headers=headers,
            json={"transcript": {"title": "Test", "content": "Content"}}
        )
        
        assert response.status_code == 401
        assert "Invalid authentication token" in response.json()["message"]
    
    def test_expired_token(self, client):
        """Test expired token handling."""
        # Create expired token
        expired_token = auth_handler.create_access_token(
            data={"sub": "test_user"},
            expires_delta=timedelta(seconds=-1)
        )
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        
        response = client.post(
            "/transcripts/process",
            headers=headers,
            json={"transcript": {"title": "Test", "content": "Content"}}
        )
        
        assert response.status_code == 401


class TestTranscriptProcessing:
    """Test transcript processing endpoints."""
    
    @pytest.mark.asyncio
    @patch('blackcore.minimal.api.app.job_queue')
    async def test_process_single_transcript(self, mock_queue, client, headers):
        """Test single transcript processing."""
        # Mock job queue
        mock_job = ProcessingJob(
            job_id="test-job-123",
            status=JobStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        mock_queue.enqueue_job = AsyncMock(return_value=mock_job)
        
        request_data = {
            "transcript": {
                "title": "Test Meeting",
                "content": "This is a test transcript about important topics.",
                "date": "2024-01-15T10:00:00Z",
                "source": "voice_memo"
            },
            "options": {
                "dry_run": False,
                "enable_deduplication": True,
                "deduplication_threshold": 85.0
            }
        }
        
        response = client.post(
            "/transcripts/process",
            headers=headers,
            json=request_data
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "request_id" in data
        assert "job" in data
        assert data["job"]["job_id"] == "test-job-123"
        assert data["job"]["status"] == "pending"
        
        assert "links" in data
        assert "self" in data["links"]
        assert "result" in data["links"]
    
    @pytest.mark.asyncio
    @patch('blackcore.minimal.api.app.job_queue')
    async def test_process_batch_transcripts(self, mock_queue, client, headers):
        """Test batch transcript processing."""
        # Mock job queue
        mock_jobs = []
        for i in range(3):
            mock_job = ProcessingJob(
                job_id=f"test-job-{i}",
                status=JobStatus.PENDING,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            mock_jobs.append(mock_job)
        
        mock_queue.enqueue_job = AsyncMock(side_effect=mock_jobs)
        
        request_data = {
            "transcripts": [
                {
                    "title": f"Transcript {i}",
                    "content": f"Content for transcript {i}",
                    "date": "2024-01-15T10:00:00Z"
                }
                for i in range(3)
            ],
            "options": {
                "dry_run": False
            },
            "batch_size": 5
        }
        
        response = client.post(
            "/transcripts/batch",
            headers=headers,
            json=request_data
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == 3
        
        for i, item in enumerate(data):
            assert item["job"]["job_id"] == f"test-job-{i}"
            assert "links" in item
    
    def test_invalid_transcript_data(self, client, headers):
        """Test invalid transcript data handling."""
        invalid_requests = [
            # Missing title
            {
                "transcript": {
                    "content": "Content without title"
                }
            },
            # Missing content
            {
                "transcript": {
                    "title": "Title without content"
                }
            },
            # Invalid date format
            {
                "transcript": {
                    "title": "Test",
                    "content": "Content",
                    "date": "invalid-date"
                }
            }
        ]
        
        for request_data in invalid_requests:
            response = client.post(
                "/transcripts/process",
                headers=headers,
                json=request_data
            )
            
            assert response.status_code == 422  # Validation error


class TestJobManagement:
    """Test job management endpoints."""
    
    @pytest.mark.asyncio
    @patch('blackcore.minimal.api.app.job_queue')
    async def test_get_job_status(self, mock_queue, client, headers):
        """Test getting job status."""
        mock_job = ProcessingJob(
            job_id="test-job-123",
            status=JobStatus.PROCESSING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            progress=50,
            metadata={"user": "test_user"}
        )
        
        mock_queue.get_job = AsyncMock(return_value=mock_job)
        
        response = client.get("/jobs/test-job-123", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["job_id"] == "test-job-123"
        assert data["status"] == "processing"
        assert data["progress"] == 50
    
    @pytest.mark.asyncio
    @patch('blackcore.minimal.api.app.job_queue')
    async def test_get_job_result(self, mock_queue, client, headers):
        """Test getting job result."""
        mock_job = ProcessingJob(
            job_id="test-job-123",
            status=JobStatus.COMPLETED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            progress=100,
            metadata={"user": "test_user"}
        )
        
        mock_result = ProcessingResult(
            success=True,
            created=[],
            updated=[],
            relationships_created=5
        )
        
        mock_queue.get_job = AsyncMock(return_value=mock_job)
        mock_queue.get_result = AsyncMock(return_value=mock_result)
        
        response = client.get("/jobs/test-job-123/result", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["relationships_created"] == 5
    
    @pytest.mark.asyncio
    @patch('blackcore.minimal.api.app.job_queue')
    async def test_cancel_job(self, mock_queue, client, headers):
        """Test cancelling a job."""
        mock_job = ProcessingJob(
            job_id="test-job-123",
            status=JobStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            metadata={"user": "test_user"}
        )
        
        mock_queue.get_job = AsyncMock(return_value=mock_job)
        mock_queue.cancel_job = AsyncMock(return_value=True)
        
        response = client.post("/jobs/test-job-123/cancel", headers=headers)
        
        assert response.status_code == 200
        assert "cancelled successfully" in response.json()["message"]
    
    @pytest.mark.asyncio
    @patch('blackcore.minimal.api.app.job_queue')
    async def test_job_not_found(self, mock_queue, client, headers):
        """Test accessing non-existent job."""
        mock_queue.get_job = AsyncMock(return_value=None)
        
        response = client.get("/jobs/non-existent-job", headers=headers)
        
        assert response.status_code == 404
        assert "Job not found" in response.json()["message"]
    
    @pytest.mark.asyncio
    @patch('blackcore.minimal.api.app.job_queue')
    async def test_job_access_denied(self, mock_queue, client, headers):
        """Test accessing job owned by another user."""
        mock_job = ProcessingJob(
            job_id="test-job-123",
            status=JobStatus.PROCESSING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            metadata={"user": "other_user"}
        )
        
        mock_queue.get_job = AsyncMock(return_value=mock_job)
        
        response = client.get("/jobs/test-job-123", headers=headers)
        
        assert response.status_code == 403
        assert "Access denied" in response.json()["message"]


class TestConfiguration:
    """Test configuration endpoints."""
    
    @patch('blackcore.minimal.api.app.config_manager')
    def test_get_config(self, mock_config_manager, client, headers):
        """Test getting configuration."""
        # Mock config with proper structure
        from blackcore.minimal.property_validation import ValidationLevel
        
        mock_config = Mock()
        
        # Create mock database configs
        people_db = Mock()
        people_db.id = "db-123"
        people_db.name = "People & Contacts"
        people_db.mappings = {"name": "Full Name", "email": "Email"}
        
        org_db = Mock()
        org_db.id = "db-456"
        org_db.name = "Organizations"
        org_db.mappings = {"name": "Organization Name"}
        
        mock_config.notion.databases = {
            "people": people_db,
            "organizations": org_db
        }
        
        # Mock processing config
        mock_processing = Mock()
        mock_processing.validation_level = ValidationLevel.STANDARD
        mock_processing.enable_deduplication = True
        mock_processing.deduplication_threshold = 90.0
        mock_processing.cache_enabled = True
        
        mock_config.processing = mock_processing
        
        mock_config_manager.load.return_value = mock_config
        
        response = client.get("/config/databases", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["databases"]) == 2
        assert data["validation_level"] == "standard"
        assert data["deduplication_enabled"] is True
        assert data["deduplication_threshold"] == 90.0
        assert data["cache_enabled"] is True
    
    @patch('blackcore.minimal.api.app.config_manager')
    def test_update_validation_admin_only(
        self,
        mock_config_manager,
        client,
        headers,
        admin_headers
    ):
        """Test updating validation settings requires admin."""
        update_data = {
            "validation_level": "strict",
            "custom_rules": {}
        }
        
        # Non-admin should fail
        response = client.put(
            "/config/validation",
            headers=headers,
            json=update_data
        )
        assert response.status_code == 403
        
        # Admin should succeed
        mock_config = Mock()
        mock_config.processing.validation_level = "standard"
        mock_config_manager.load.return_value = mock_config
        
        response = client.put(
            "/config/validation",
            headers=admin_headers,
            json=update_data
        )
        assert response.status_code == 200


class TestRateLimiting:
    """Test rate limiting functionality."""
    
    @pytest.mark.asyncio
    @patch('blackcore.minimal.api.app.job_queue')
    async def test_rate_limiting(self, mock_queue, client, headers):
        """Test rate limiting enforcement."""
        # Mock job queue
        mock_job = ProcessingJob(
            job_id="test-job",
            status=JobStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        mock_queue.enqueue_job = AsyncMock(return_value=mock_job)
        
        # Make many requests quickly
        request_data = {
            "transcript": {
                "title": "Test",
                "content": "Content",
                "date": "2024-01-15T10:00:00Z"
            }
        }
        
        # Should eventually hit rate limit
        # (Exact behavior depends on rate limiter configuration)
        responses = []
        for _ in range(100):
            response = client.post(
                "/transcripts/process",
                headers=headers,
                json=request_data
            )
            responses.append(response.status_code)
            
            if response.status_code == 429:
                break
        
        # Should have hit rate limit at some point
        # Note: This test might need adjustment based on actual rate limit config
        assert any(status == 429 for status in responses)


class TestErrorHandling:
    """Test API error handling."""
    
    def test_404_error(self, client, headers):
        """Test 404 error response."""
        response = client.get("/non-existent-endpoint", headers=headers)
        
        assert response.status_code == 404
        
        # FastAPI returns default format for true 404s (non-existent routes)
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "Not Found"
    
    @patch('blackcore.minimal.api.app.job_queue', None)
    def test_service_unavailable(self, client, headers):
        """Test service unavailable error."""
        request_data = {
            "transcript": {
                "title": "Test",
                "content": "Content",
                "date": "2024-01-15T10:00:00Z"
            }
        }
        
        response = client.post(
            "/transcripts/process",
            headers=headers,
            json=request_data
        )
        
        assert response.status_code == 503
        assert "Job queue not available" in response.json()["message"]


class TestAsyncProcessing:
    """Test async job processing flow."""
    
    @pytest.mark.asyncio
    @patch('blackcore.minimal.api.app.job_queue')
    async def test_full_async_flow(self, mock_queue, client, headers):
        """Test complete async processing flow."""
        job_id = "test-job-full-flow"
        
        # Step 1: Submit job
        pending_job = ProcessingJob(
            job_id=job_id,
            status=JobStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            metadata={"user": "test_user"}
        )
        
        mock_queue.enqueue_job = AsyncMock(return_value=pending_job)
        
        request_data = {
            "transcript": {
                "title": "Full Flow Test",
                "content": "Testing the complete async flow.",
                "date": "2024-01-15T10:00:00Z"
            }
        }
        
        response = client.post(
            "/transcripts/process",
            headers=headers,
            json=request_data
        )
        
        assert response.status_code == 200
        assert response.json()["job"]["status"] == "pending"
        
        # Step 2: Check processing status
        processing_job = ProcessingJob(
            job_id=job_id,
            status=JobStatus.PROCESSING,
            created_at=pending_job.created_at,
            updated_at=datetime.utcnow(),
            started_at=datetime.utcnow(),
            progress=50,
            metadata={"user": "test_user"}
        )
        
        mock_queue.get_job = AsyncMock(return_value=processing_job)
        
        response = client.get(f"/jobs/{job_id}", headers=headers)
        
        assert response.status_code == 200
        assert response.json()["status"] == "processing"
        assert response.json()["progress"] == 50
        
        # Step 3: Get completed result
        completed_job = ProcessingJob(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            created_at=pending_job.created_at,
            updated_at=datetime.utcnow(),
            started_at=processing_job.started_at,
            completed_at=datetime.utcnow(),
            progress=100,
            metadata={"user": "test_user"},
            result_url=f"/jobs/{job_id}/result"
        )
        
        result = ProcessingResult(
            success=True,
            created=[],
            updated=[],
            relationships_created=3,
            processing_time=5.2
        )
        
        mock_queue.get_job = AsyncMock(return_value=completed_job)
        mock_queue.get_result = AsyncMock(return_value=result)
        
        response = client.get(f"/jobs/{job_id}/result", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["relationships_created"] == 3
        assert data["processing_time"] == 5.2