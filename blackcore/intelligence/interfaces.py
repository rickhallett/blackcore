"""Core interfaces and models for the intelligence system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
import json


class AnalysisType(Enum):
    """Types of analysis supported by the system."""
    ENTITY_EXTRACTION = "entity_extraction"
    RELATIONSHIP_MAPPING = "relationship_mapping"
    COMMUNITY_DETECTION = "community_detection"
    ANOMALY_DETECTION = "anomaly_detection"
    PATH_FINDING = "path_finding"
    CENTRALITY_ANALYSIS = "centrality_analysis"
    PATTERN_RECOGNITION = "pattern_recognition"
    RISK_SCORING = "risk_scoring"
    TEMPORAL_ANALYSIS = "temporal_analysis"
    FINANCIAL_ANALYSIS = "financial_analysis"


@dataclass
class Entity:
    """Represents an entity in the intelligence system."""
    id: str
    name: str
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    source: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "properties": self.properties,
            "confidence": self.confidence,
            "source": self.source,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class Relationship:
    """Represents a relationship between entities."""
    id: str
    source_id: str
    target_id: str
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert relationship to dictionary representation."""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "type": self.type,
            "properties": self.properties,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class AnalysisRequest:
    """Request for analysis."""
    type: AnalysisType
    parameters: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    
    def to_prompt_context(self) -> str:
        """Convert request to JSON context for LLM prompts."""
        return json.dumps({
            "analysis_type": self.type.value,
            "parameters": self.parameters,
            "context": self.context,
            "constraints": self.constraints
        }, indent=2)


@dataclass
class AnalysisResult:
    """Result of an analysis operation."""
    request: AnalysisRequest
    success: bool
    data: Optional[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    duration_ms: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            "request": {
                "type": self.request.type.value,
                "parameters": self.request.parameters,
                "context": self.request.context,
                "constraints": self.request.constraints
            },
            "success": self.success,
            "data": self.data,
            "metadata": self.metadata,
            "errors": self.errors,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalysisResult":
        """Create AnalysisResult from dictionary representation."""
        # Reconstruct the request
        request = AnalysisRequest(
            type=AnalysisType(data["request"]["type"]),
            parameters=data["request"]["parameters"],
            context=data["request"]["context"],
            constraints=data["request"]["constraints"]
        )
        
        # Parse timestamp
        timestamp = datetime.fromisoformat(data["timestamp"])
        
        return cls(
            request=request,
            success=data["success"],
            data=data["data"],
            metadata=data.get("metadata", {}),
            errors=data.get("errors", []),
            duration_ms=data.get("duration_ms"),
            timestamp=timestamp
        )


class ILLMProvider(ABC):
    """Interface for LLM providers."""
    
    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None
    ) -> str:
        """Complete a prompt."""
        pass
    
    @abstractmethod
    async def complete_with_functions(
        self,
        prompt: str,
        functions: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """Complete with function calling."""
        pass
    
    @abstractmethod
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count."""
        pass


class IGraphBackend(ABC):
    """Interface for graph storage backends."""
    
    @abstractmethod
    async def add_entity(self, entity: Entity) -> bool:
        """Add entity to graph."""
        pass
    
    @abstractmethod
    async def add_relationship(self, relationship: Relationship) -> bool:
        """Add relationship to graph."""
        pass
    
    @abstractmethod
    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID."""
        pass
    
    @abstractmethod
    async def get_entities(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> List[Entity]:
        """Get entities with optional filters."""
        pass
    
    @abstractmethod
    async def get_relationships(
        self,
        entity_id: Optional[str] = None,
        relationship_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Relationship]:
        """Get relationships with optional filters."""
        pass
    
    @abstractmethod
    async def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute graph query."""
        pass
    
    @abstractmethod
    async def get_subgraph(
        self,
        entity_ids: List[str],
        max_depth: int = 1
    ) -> Dict[str, List[Any]]:
        """Get subgraph around entities."""
        pass


class IAnalysisStrategy(ABC):
    """Interface for analysis strategies."""
    
    @abstractmethod
    async def analyze(
        self,
        request: AnalysisRequest,
        llm: ILLMProvider,
        graph: IGraphBackend
    ) -> AnalysisResult:
        """Execute analysis."""
        pass
    
    @abstractmethod
    def can_handle(self, analysis_type: AnalysisType) -> bool:
        """Check if strategy can handle analysis type."""
        pass


class ICache(ABC):
    """Interface for caching."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cache entries."""
        pass


class IInvestigationPipeline(ABC):
    """Interface for investigation pipeline."""
    
    @abstractmethod
    async def investigate(
        self,
        initial_context: Dict[str, Any],
        objectives: List[str]
    ) -> Dict[str, Any]:
        """Run investigation."""
        pass
    
    @abstractmethod
    async def add_evidence(
        self,
        investigation_id: str,
        evidence: Dict[str, Any]
    ) -> bool:
        """Add evidence to investigation."""
        pass
    
    @abstractmethod
    async def get_investigation(
        self,
        investigation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get investigation details."""
        pass