"""
Core Deduplication Engine

Orchestrates the sophisticated deduplication pipeline with AI/LLM integration,
confidence-based decision making, and comprehensive audit trails.
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from pathlib import Path
import json

from .similarity_scoring import SimilarityScorer, ConfidenceThresholds
from .entity_processors import PersonProcessor, OrganizationProcessor, EventProcessor, DocumentProcessor
from .llm_analyzer import LLMEntityAnalyzer
from .audit_system import DeduplicationAudit
from .merge_proposals import MergeProposal, MergeExecutor

logger = logging.getLogger(__name__)


@dataclass
class DeduplicationResult:
    """Results of a deduplication analysis."""
    total_entities: int
    potential_duplicates: int = 0
    high_confidence_matches: List[Dict[str, Any]] = field(default_factory=list)
    medium_confidence_matches: List[Dict[str, Any]] = field(default_factory=list)
    low_confidence_matches: List[Dict[str, Any]] = field(default_factory=list)
    auto_merged: int = 0
    flagged_for_review: int = 0
    processing_time: float = 0.0
    confidence_distribution: Dict[str, int] = field(default_factory=dict)


@dataclass
class EntityPair:
    """A pair of entities being compared for potential duplication."""
    entity_a: Dict[str, Any]
    entity_b: Dict[str, Any] 
    entity_type: str
    similarity_scores: Dict[str, float] = field(default_factory=dict)
    confidence_score: float = 0.0
    ai_analysis: Optional[Dict[str, Any]] = None
    recommended_action: str = "unknown"
    human_review_required: bool = False
    risk_assessment: str = "unknown"


class DeduplicationEngine:
    """
    Sophisticated deduplication engine with multi-layer analysis.
    
    Combines fuzzy matching, AI/LLM analysis, and human-in-the-loop validation
    for high-accuracy entity resolution in intelligence data.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the deduplication engine."""
        self.config = self._load_config(config_path)
        
        # Initialize components
        self.similarity_scorer = SimilarityScorer()
        self.confidence_thresholds = ConfidenceThresholds()
        self.llm_analyzer = LLMEntityAnalyzer()
        self.audit_system = DeduplicationAudit()
        self.merge_executor = MergeExecutor()
        
        # Entity-specific processors
        self.processors = {
            "People & Contacts": PersonProcessor(),
            "Organizations & Bodies": OrganizationProcessor(), 
            "Key Places & Events": EventProcessor(),
            "Documents & Evidence": DocumentProcessor(),
            "Intelligence & Transcripts": DocumentProcessor(),  # Treat as documents
            "Identified Transgressions": DocumentProcessor(),
            "Actionable Tasks": DocumentProcessor()
        }
        
        # Statistics
        self.stats = {
            "total_comparisons": 0,
            "ai_analyses_performed": 0,
            "auto_merges": 0,
            "human_reviews_created": 0
        }
        
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load deduplication configuration."""
        default_config = {
            "auto_merge_threshold": 90.0,
            "human_review_threshold": 70.0,
            "batch_size": 100,
            "enable_ai_analysis": True,
            "safety_mode": True,
            "max_ai_requests_per_minute": 10
        }
        
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
                
        return default_config
        
    def analyze_database(self, database_name: str, records: List[Dict[str, Any]], 
                        enable_ai: bool = True) -> DeduplicationResult:
        """
        Analyze a database for potential duplicates.
        
        Args:
            database_name: Name of the database being analyzed
            records: List of records to analyze
            enable_ai: Whether to use AI/LLM analysis
            
        Returns:
            DeduplicationResult with findings and recommendations
        """
        start_time = time.time()
        
        logger.info(f"🔍 Starting deduplication analysis for {database_name}")
        logger.info(f"   📊 Analyzing {len(records)} records")
        
        result = DeduplicationResult(total_entities=len(records))
        
        # Get appropriate processor for this entity type
        processor = self.processors.get(database_name, self.processors["Documents & Evidence"])
        
        # Generate candidate pairs for comparison
        candidate_pairs = self._generate_candidate_pairs(records, processor)
        logger.info(f"   🔍 Generated {len(candidate_pairs)} candidate pairs for analysis")
        
        # Analyze each pair
        for pair in candidate_pairs:
            self._analyze_entity_pair(pair, processor, enable_ai)
            self.stats["total_comparisons"] += 1
            
            # Categorize based on confidence
            if pair.confidence_score >= self.config["auto_merge_threshold"]:
                result.high_confidence_matches.append(self._pair_to_dict(pair))
            elif pair.confidence_score >= self.config["human_review_threshold"]:
                result.medium_confidence_matches.append(self._pair_to_dict(pair))
            else:
                result.low_confidence_matches.append(self._pair_to_dict(pair))
                
        # Calculate statistics
        result.potential_duplicates = len(candidate_pairs)
        result.processing_time = time.time() - start_time
        result.confidence_distribution = self._calculate_confidence_distribution(candidate_pairs)
        
        # Execute automatic merges if in production mode
        if not self.config["safety_mode"]:
            result.auto_merged = self._execute_automatic_merges(result.high_confidence_matches)
            
        # Create human review tasks
        result.flagged_for_review = self._create_review_tasks(
            result.medium_confidence_matches, database_name
        )
        
        logger.info(f"✅ Deduplication analysis complete for {database_name}")
        logger.info(f"   ⏱️  Processing time: {result.processing_time:.2f} seconds")
        logger.info(f"   🎯 High confidence matches: {len(result.high_confidence_matches)}")
        logger.info(f"   🤔 Medium confidence matches: {len(result.medium_confidence_matches)}")
        logger.info(f"   ❓ Low confidence matches: {len(result.low_confidence_matches)}")
        
        return result
        
    def _generate_candidate_pairs(self, records: List[Dict[str, Any]], 
                                processor) -> List[EntityPair]:
        """Generate candidate entity pairs for comparison."""
        candidates = []
        
        # Use processor-specific logic to identify potential duplicates
        for i, record_a in enumerate(records):
            for j, record_b in enumerate(records[i+1:], i+1):
                # Quick pre-screening to avoid unnecessary comparisons
                if processor.is_potential_duplicate(record_a, record_b):
                    pair = EntityPair(
                        entity_a=record_a,
                        entity_b=record_b,
                        entity_type=processor.entity_type
                    )
                    candidates.append(pair)
                    
        return candidates
        
    def _analyze_entity_pair(self, pair: EntityPair, processor, enable_ai: bool):
        """Analyze a single entity pair for potential duplication."""
        
        # Layer 1: Fuzzy matching and similarity scoring
        pair.similarity_scores = self.similarity_scorer.calculate_similarity(
            pair.entity_a, pair.entity_b, processor.get_comparison_fields()
        )
        
        # Calculate initial confidence score
        pair.confidence_score = processor.calculate_confidence(pair.similarity_scores, pair.entity_a, pair.entity_b)
        
        # Layer 2: AI/LLM analysis for medium+ confidence matches
        if (enable_ai and 
            pair.confidence_score >= self.config["human_review_threshold"] and
            self.config["enable_ai_analysis"]):
            
            try:
                pair.ai_analysis = self.llm_analyzer.analyze_entity_pair(
                    pair.entity_a, pair.entity_b, pair.entity_type
                )
                
                # Refine confidence based on AI analysis
                if pair.ai_analysis:
                    ai_confidence = pair.ai_analysis.confidence_score
                    pair.confidence_score = self._combine_scores(
                        pair.confidence_score, ai_confidence
                    )
                    pair.recommended_action = pair.ai_analysis.recommended_action
                    pair.risk_assessment = pair.ai_analysis.risk_assessment
                    
                self.stats["ai_analyses_performed"] += 1
                
            except Exception as e:
                logger.warning(f"AI analysis failed for entity pair: {e}")
                pair.ai_analysis = None
                
        # Determine if human review is required
        pair.human_review_required = (
            self.config["human_review_threshold"] <= pair.confidence_score < self.config["auto_merge_threshold"]
            or pair.risk_assessment == "high"
            or (pair.ai_analysis and pair.ai_analysis.recommended_action == "needs_human_review")
        )
        
    def _combine_scores(self, fuzzy_score: float, ai_score: float) -> float:
        """Combine fuzzy matching and AI confidence scores."""
        # Weighted average with slight bias toward AI analysis
        return (fuzzy_score * 0.4) + (ai_score * 0.6)
        
    def _pair_to_dict(self, pair: EntityPair) -> Dict[str, Any]:
        """Convert EntityPair to dictionary for serialization."""
        # Convert ai_analysis to dict if it's an LLMAnalysisResult object
        ai_analysis_dict = None
        if pair.ai_analysis:
            if hasattr(pair.ai_analysis, '__dict__'):
                ai_analysis_dict = {
                    "confidence_score": pair.ai_analysis.confidence_score,
                    "recommended_action": pair.ai_analysis.recommended_action,
                    "reasoning": pair.ai_analysis.reasoning,
                    "key_evidence": pair.ai_analysis.key_evidence,
                    "risk_assessment": pair.ai_analysis.risk_assessment,
                    "model_used": pair.ai_analysis.model_used
                }
            else:
                ai_analysis_dict = pair.ai_analysis
        
        return {
            "entity_a": pair.entity_a,
            "entity_b": pair.entity_b,
            "entity_type": pair.entity_type,
            "similarity_scores": pair.similarity_scores,
            "confidence_score": pair.confidence_score,
            "ai_analysis": ai_analysis_dict,
            "recommended_action": pair.recommended_action,
            "human_review_required": pair.human_review_required,
            "risk_assessment": pair.risk_assessment
        }
        
    def _calculate_confidence_distribution(self, pairs: List[EntityPair]) -> Dict[str, int]:
        """Calculate distribution of confidence scores."""
        distribution = {
            "high (90%+)": 0,
            "medium (70-90%)": 0, 
            "low (50-70%)": 0,
            "very_low (<50%)": 0
        }
        
        for pair in pairs:
            if pair.confidence_score >= 90:
                distribution["high (90%+)"] += 1
            elif pair.confidence_score >= 70:
                distribution["medium (70-90%)"] += 1
            elif pair.confidence_score >= 50:
                distribution["low (50-70%)"] += 1
            else:
                distribution["very_low (<50%)"] += 1
                
        return distribution
        
    def _execute_automatic_merges(self, high_confidence_matches: List[Dict[str, Any]]) -> int:
        """Execute automatic merges for high-confidence matches."""
        if self.config["safety_mode"]:
            logger.info("🛡️  Safety mode enabled - skipping automatic merges")
            return 0
            
        merged_count = 0
        
        for match in high_confidence_matches:
            try:
                # Create merge proposal
                proposal = MergeProposal(
                    primary_entity=match["entity_a"],
                    secondary_entity=match["entity_b"],
                    confidence_score=match["confidence_score"],
                    evidence=match["similarity_scores"],
                    ai_analysis=match.get("ai_analysis")
                )
                
                # Execute merge with audit trail
                if self.merge_executor.execute_merge(proposal, auto_approved=True):
                    merged_count += 1
                    self.stats["auto_merges"] += 1
                    
            except Exception as e:
                logger.error(f"Failed to execute automatic merge: {e}")
                
        logger.info(f"🔄 Executed {merged_count} automatic merges")
        return merged_count
        
    def _create_review_tasks(self, medium_confidence_matches: List[Dict[str, Any]], 
                           database_name: str) -> int:
        """Create human review tasks for medium-confidence matches."""
        review_count = 0
        
        for match in medium_confidence_matches:
            try:
                # Create review task in audit system
                self.audit_system.create_review_task(
                    database_name=database_name,
                    entity_pair=match,
                    priority="medium" if match["confidence_score"] >= 80 else "low",
                    ai_analysis=match.get("ai_analysis")
                )
                
                review_count += 1
                self.stats["human_reviews_created"] += 1
                
            except Exception as e:
                logger.error(f"Failed to create review task: {e}")
                
        logger.info(f"📋 Created {review_count} human review tasks")
        return review_count
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive deduplication statistics."""
        return {
            "engine_stats": self.stats.copy(),
            "ai_analyzer_stats": self.llm_analyzer.get_statistics(),
            "audit_stats": self.audit_system.get_statistics(),
            "configuration": self.config
        }
        
    def analyze_all_databases(self, databases: Dict[str, List[Dict[str, Any]]]) -> Dict[str, DeduplicationResult]:
        """Analyze multiple databases for deduplication."""
        results = {}
        
        total_start_time = time.time()
        logger.info(f"🚀 Starting comprehensive deduplication analysis")
        logger.info(f"   📊 Analyzing {len(databases)} databases")
        
        for db_name, records in databases.items():
            if records:  # Skip empty databases
                results[db_name] = self.analyze_database(db_name, records)
            else:
                logger.info(f"⏭️  Skipping empty database: {db_name}")
                
        total_time = time.time() - total_start_time
        
        # Generate comprehensive summary
        total_entities = sum(result.total_entities for result in results.values())
        total_potential_duplicates = sum(result.potential_duplicates for result in results.values())
        
        logger.info(f"✅ Comprehensive deduplication analysis complete")
        logger.info(f"   ⏱️  Total processing time: {total_time:.2f} seconds")
        logger.info(f"   📊 Total entities analyzed: {total_entities}")
        logger.info(f"   🔍 Total potential duplicates found: {total_potential_duplicates}")
        logger.info(f"   🤖 AI analyses performed: {self.stats['ai_analyses_performed']}")
        logger.info(f"   📋 Human reviews created: {self.stats['human_reviews_created']}")
        
        return results