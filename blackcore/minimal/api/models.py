"""API request and response models."""

from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict

from ..models import TranscriptInput, ProcessingResult, EntityType
from ..property_validation import ValidationLevel


class JobStatus(str, Enum):
    """Status of an async processing job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcessingOptions(BaseModel):
    """Options for transcript processing."""

    dry_run: bool = False
    enable_deduplication: bool = True
    deduplication_threshold: float = Field(
        default=90.0, ge=0.0, le=100.0, description="Similarity threshold for deduplication (0-100)"
    )
    validation_level: ValidationLevel = ValidationLevel.STANDARD
    cache_enabled: bool = True
    verbose: bool = False


class TranscriptProcessRequest(BaseModel):
    """Request model for processing a single transcript."""

    transcript: TranscriptInput
    options: ProcessingOptions = Field(default_factory=ProcessingOptions)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "transcript": {
                    "title": "Q4 Planning Meeting",
                    "content": "Discussion about Q4 objectives...",
                    "date": "2024-01-15T10:00:00Z",
                    "source": "google_meet",
                },
                "options": {"dry_run": False, "enable_deduplication": True},
            }
        }
    )


class BatchProcessRequest(BaseModel):
    """Request model for processing multiple transcripts."""

    transcripts: List[TranscriptInput] = Field(
        ..., min_length=1, max_length=100, description="List of transcripts to process (max 100)"
    )
    options: ProcessingOptions = Field(default_factory=ProcessingOptions)
    batch_size: int = Field(
        default=10, ge=1, le=50, description="Number of transcripts to process concurrently"
    )


class ProcessingJob(BaseModel):
    """Represents an async processing job."""

    job_id: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: int = Field(default=0, ge=0, le=100, description="Progress percentage (0-100)")
    result_url: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def duration(self) -> Optional[float]:
        """Calculate processing duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class ProcessingResponse(BaseModel):
    """Response model for transcript processing."""

    request_id: str
    job: ProcessingJob
    result: Optional[ProcessingResult] = None
    links: Dict[str, str] = Field(
        default_factory=dict, description="HATEOAS links for related resources"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "request_id": "req_123456",
                "job": {
                    "job_id": "job_789",
                    "status": "completed",
                    "created_at": "2024-01-15T10:00:00Z",
                    "updated_at": "2024-01-15T10:05:00Z",
                    "progress": 100,
                },
                "links": {"self": "/jobs/job_789", "result": "/jobs/job_789/result"},
            }
        }
    )


class APIError(BaseModel):
    """Standardized error response."""

    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error_code": "VALIDATION_ERROR",
                "message": "Invalid transcript content",
                "details": {"field": "transcript.content", "reason": "Content cannot be empty"},
                "request_id": "req_123456",
                "timestamp": "2024-01-15T10:00:00Z",
            }
        }
    )


class EntityFilter(BaseModel):
    """Filter criteria for entity search."""

    entity_types: Optional[List[EntityType]] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    confidence_min: Optional[float] = Field(None, ge=0.0, le=1.0)
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Health status (healthy/unhealthy)")
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    checks: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict, description="Individual component health checks"
    )


class TokenRequest(BaseModel):
    """Request model for token generation."""

    api_key: str = Field(..., description="API key for authentication")
    expires_in: int = Field(
        default=3600, ge=300, le=86400, description="Token expiration time in seconds"
    )


class TokenResponse(BaseModel):
    """Response model for token generation."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIs...",
                "token_type": "bearer",
                "expires_in": 3600,
            }
        }
    )


class DatabaseInfo(BaseModel):
    """Information about a configured Notion database."""

    id: str
    name: str
    entity_type: str
    property_count: int
    is_configured: bool


class ConfigResponse(BaseModel):
    """Response model for configuration endpoints."""

    databases: List[DatabaseInfo]
    validation_level: ValidationLevel
    deduplication_enabled: bool
    deduplication_threshold: float
    cache_enabled: bool


class ValidationRuleUpdate(BaseModel):
    """Request model for updating validation rules."""

    validation_level: ValidationLevel
    custom_rules: Optional[Dict[str, Any]] = None


# New models for Streamlit GUI integration
class DashboardStats(BaseModel):
    """Dashboard statistics response."""
    
    transcripts: Dict[str, int]
    entities: Dict[str, int] 
    processing: Dict[str, Any]
    recent_activity: List[Dict[str, Any]]
    last_updated: datetime


class TimelineEvent(BaseModel):
    """Timeline event for dashboard."""
    
    id: str
    timestamp: datetime
    event_type: str
    title: str
    description: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None


class ProcessingMetrics(BaseModel):
    """Processing performance metrics."""
    
    avg_processing_time: float
    success_rate: float
    entities_per_transcript: float
    relationships_per_transcript: float
    cache_hit_rate: float


class GlobalSearchResults(BaseModel):
    """Global search results response."""
    
    query: str
    total_results: int
    results: List[Dict[str, Any]]
    search_time: float
    suggestions: List[str]


class EntityResult(BaseModel):
    """Individual entity search result."""
    
    id: str
    type: str
    title: str
    properties: Dict[str, Any]
    relevance_score: float
    snippet: Optional[str] = None


class NetworkGraph(BaseModel):
    """Network graph data for visualization."""
    
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    center_node: Optional[str] = None


class EntityRelationships(BaseModel):
    """Entity relationships response."""
    
    entity_id: str
    relationships: List[Dict[str, Any]]
    relationship_count: int


class RelationshipPath(BaseModel):
    """Relationship path between entities."""
    
    from_entity: str
    to_entity: str
    path: List[str]
    path_length: int


class QueueStatus(BaseModel):
    """Processing queue status."""
    
    pending_jobs: int
    running_jobs: int
    completed_jobs: int
    failed_jobs: int
    total_jobs: int
    worker_status: str


class JobSummary(BaseModel):
    """Job summary for queue display."""
    
    job_id: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    transcript_title: str
    entities_extracted: int
    processing_time: Optional[float]
    
    @classmethod
    def from_job(cls, job):
        """Create JobSummary from job object."""
        return cls(
            job_id=job.job_id,
            status=job.status,
            created_at=job.created_at,
            completed_at=job.completed_at,
            transcript_title=job.metadata.get("title", "Unknown"),
            entities_extracted=job.result.get("entities_count", 0) if job.result else 0,
            processing_time=job.processing_time
        )
