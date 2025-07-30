"""Data models for minimal transcript processor."""

from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum


class EntityType(str, Enum):
    """Types of entities we can extract."""

    PERSON = "person"
    ORGANIZATION = "organization"
    EVENT = "event"
    TASK = "task"
    TRANSGRESSION = "transgression"
    DOCUMENT = "document"
    PLACE = "place"


class TranscriptSource(str, Enum):
    """Source types for transcripts."""

    VOICE_MEMO = "voice_memo"
    GOOGLE_MEET = "google_meet"
    PERSONAL_NOTE = "personal_note"
    EXTERNAL_SOURCE = "external_source"


class Entity(BaseModel):
    """Represents an extracted entity."""

    name: str
    type: EntityType
    properties: Dict[str, Any] = Field(default_factory=dict)
    context: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)

    class Config:
        use_enum_values = True


class Relationship(BaseModel):
    """Represents a relationship between entities."""

    source_entity: str
    source_type: EntityType
    target_entity: str
    target_type: EntityType
    relationship_type: str
    context: Optional[str] = None

    class Config:
        use_enum_values = True


class ExtractedEntities(BaseModel):
    """Container for all extracted entities and relationships."""

    entities: List[Entity] = Field(default_factory=list)
    relationships: List[Relationship] = Field(default_factory=list)
    summary: Optional[str] = None
    key_points: List[str] = Field(default_factory=list)

    def get_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        """Get all entities of a specific type."""
        return [e for e in self.entities if e.type == entity_type]


class TranscriptInput(BaseModel):
    """Input transcript model."""

    title: str
    content: str
    date: Optional[datetime] = None
    source: Optional[TranscriptSource] = TranscriptSource.PERSONAL_NOTE
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator("date", pre=True)
    def parse_date(cls, v):
        """Parse date from string if needed."""
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v

    class Config:
        use_enum_values = True


class NotionPage(BaseModel):
    """Simplified Notion page model."""

    id: str
    database_id: str
    properties: Dict[str, Any]
    created_time: datetime
    last_edited_time: datetime
    url: Optional[str] = None


class ProcessingError(BaseModel):
    """Represents an error during processing."""

    stage: str
    entity: Optional[str] = None
    error_type: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ProcessingResult(BaseModel):
    """Result of processing a single transcript."""

    transcript_id: Optional[str] = None
    success: bool = True
    created: List[NotionPage] = Field(default_factory=list)
    updated: List[NotionPage] = Field(default_factory=list)
    relationships_created: int = 0
    errors: List[ProcessingError] = Field(default_factory=list)
    processing_time: Optional[float] = None

    @property
    def total_changes(self) -> int:
        """Total number of changes made."""
        return len(self.created) + len(self.updated) + self.relationships_created

    def add_error(
        self, stage: str, error_type: str, message: str, entity: Optional[str] = None
    ):
        """Add an error to the result."""
        self.errors.append(
            ProcessingError(
                stage=stage, entity=entity, error_type=error_type, message=message
            )
        )
        self.success = False


class BatchResult(BaseModel):
    """Result of processing multiple transcripts."""

    total_transcripts: int
    successful: int
    failed: int
    results: List[ProcessingResult] = Field(default_factory=list)
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_transcripts == 0:
            return 0.0
        return self.successful / self.total_transcripts

    @property
    def processing_time(self) -> Optional[float]:
        """Total processing time in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


class DatabaseConfig(BaseModel):
    """Configuration for a Notion database."""

    id: str
    name: str
    mappings: Dict[str, str] = Field(default_factory=dict)
    property_types: Dict[str, str] = Field(default_factory=dict)


class NotionConfig(BaseModel):
    """Notion configuration."""

    api_key: str
    databases: Dict[str, DatabaseConfig]
    rate_limit: float = 3.0
    retry_attempts: int = 3


class AIConfig(BaseModel):
    """AI provider configuration."""

    provider: str = "claude"
    api_key: str
    model: str = "claude-3-sonnet-20240229"
    extraction_prompt: Optional[str] = None
    max_tokens: int = 4000
    temperature: float = 0.3


class ProcessingConfig(BaseModel):
    """Processing configuration."""

    batch_size: int = 10
    cache_ttl: int = 3600
    cache_dir: Optional[str] = ".cache"
    dry_run: bool = False
    verbose: bool = False
    enable_deduplication: bool = True
    deduplication_threshold: float = 90.0
    deduplication_scorer: str = "simple"  # "simple" or "llm"
    llm_scorer_config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "model": "claude-3-5-haiku-20241022",
            "temperature": 0.1,
            "cache_ttl": 3600,
            "batch_size": 5,
        }
    )


class Config(BaseModel):
    """Complete configuration model."""

    notion: NotionConfig
    ai: AIConfig
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
