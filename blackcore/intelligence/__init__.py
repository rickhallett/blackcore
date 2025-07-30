"""Intelligence system for LLM-powered analysis."""

from .interfaces import (
    # Core models
    Entity,
    Relationship,
    AnalysisType,
    AnalysisRequest,
    AnalysisResult,
    
    # Abstract interfaces
    ILLMProvider,
    IGraphBackend,
    IAnalysisStrategy,
    ICache,
    IInvestigationPipeline,
)

from .engine import AnalysisEngine

from .strategies import (
    EntityExtractionStrategy,
    RelationshipMappingStrategy,
    CommunityDetectionStrategy,
    AnomalyDetectionStrategy,
    PathFindingStrategy,
    CentralityAnalysisStrategy,
)

__all__ = [
    # Core models
    "Entity",
    "Relationship",
    "AnalysisType",
    "AnalysisRequest",
    "AnalysisResult",
    
    # Abstract interfaces
    "ILLMProvider",
    "IGraphBackend",
    "IAnalysisStrategy",
    "ICache",
    "IInvestigationPipeline",
    
    # Engine
    "AnalysisEngine",
    
    # Strategies
    "EntityExtractionStrategy",
    "RelationshipMappingStrategy",
    "CommunityDetectionStrategy",
    "AnomalyDetectionStrategy",
    "PathFindingStrategy",
    "CentralityAnalysisStrategy",
]