"""
Sophisticated Deduplication System for Intelligence Data

This module provides AI-enhanced entity resolution and deduplication capabilities
designed specifically for intelligence and surveillance data with high accuracy
requirements and complete audit trails.

Components:
- Core Engine: Orchestrates the entire deduplication pipeline
- Similarity Scoring: Advanced fuzzy matching with multiple algorithms
- Entity Processors: Domain-specific logic for different entity types
- LLM Analyzer: AI-powered entity resolution using Claude/GPT
- Graph Analyzer: Relationship-based disambiguation
- Merge Proposals: Safe merge execution with rollback capabilities
- Audit System: Comprehensive tracking and quality assurance
- Review Interface: Human validation workflows

Usage:
    from blackcore.deduplication import DeduplicationEngine

    engine = DeduplicationEngine()
    results = engine.analyze_database("People & Contacts", records)
"""

from .core_engine import DeduplicationEngine, DeduplicationResult, EntityPair
from .similarity_scoring import SimilarityScorer, ConfidenceThresholds
from .entity_processors import (
    PersonProcessor,
    OrganizationProcessor,
    EventProcessor,
    DocumentProcessor,
)
from .llm_analyzer import LLMEntityAnalyzer, LLMAnalysisResult
from .graph_analyzer import GraphRelationshipAnalyzer, GraphAnalysisResult
from .merge_proposals import MergeProposal, MergeExecutor, MergeResult
from .audit_system import DeduplicationAudit, ReviewTask, AuditRecord
from .review_interface import HumanReviewInterface, ReviewContext, ReviewDecision

__all__ = [
    # Core engine
    "DeduplicationEngine",
    "DeduplicationResult",
    "EntityPair",
    # Similarity scoring
    "SimilarityScorer",
    "ConfidenceThresholds",
    # Entity processors
    "PersonProcessor",
    "OrganizationProcessor",
    "EventProcessor",
    "DocumentProcessor",
    # AI analysis
    "LLMEntityAnalyzer",
    "LLMAnalysisResult",
    # Graph analysis
    "GraphRelationshipAnalyzer",
    "GraphAnalysisResult",
    # Merge execution
    "MergeProposal",
    "MergeExecutor",
    "MergeResult",
    # Audit system
    "DeduplicationAudit",
    "ReviewTask",
    "AuditRecord",
    # Human review
    "HumanReviewInterface",
    "ReviewContext",
    "ReviewDecision",
]

__version__ = "1.0.0"
