"""
Human Review Interface

Provides a comprehensive interface for human reviewers to validate,
approve, or reject entity merge proposals with detailed context and evidence.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ReviewContext:
    """Context information for a human review task."""
    task_id: str
    entity_pair: Dict[str, Any]
    similarity_analysis: Dict[str, Any]
    ai_analysis: Optional[Dict[str, Any]] = None
    graph_analysis: Optional[Dict[str, Any]] = None
    risk_factors: List[str] = field(default_factory=list)
    supporting_evidence: List[str] = field(default_factory=list)
    conflicting_evidence: List[str] = field(default_factory=list)
    reviewer_guidance: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReviewDecision:
    """A human reviewer's decision on an entity pair."""
    task_id: str
    reviewer_id: str
    decision: str  # 'merge', 'separate', 'defer', 'needs_more_info'
    confidence: float
    reasoning: str
    notes: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    time_spent_seconds: int = 0
    flags: List[str] = field(default_factory=list)


class HumanReviewInterface:
    """
    Interface for human reviewers to make deduplication decisions.
    
    Provides structured workflows, decision support tools, and
    comprehensive context to help humans make accurate judgments.
    """
    
    def __init__(self, audit_system, config: Optional[Dict[str, Any]] = None):
        """Initialize the review interface."""
        self.audit_system = audit_system
        self.config = config or self._load_default_config()
        
        # Review statistics
        self.stats = {
            "reviews_completed": 0,
            "merge_decisions": 0,
            "separate_decisions": 0,
            "defer_decisions": 0,
            "average_review_time": 0.0,
            "reviewer_accuracy": {},
            "difficult_cases": 0
        }
        
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration for review interface."""
        return {
            "max_review_time_minutes": 15,
            "require_confidence_score": True,
            "enable_reviewer_guidance": True,
            "show_ai_analysis": True,
            "show_graph_context": True,
            "require_reasoning": True,
            "flag_difficult_cases": True,
            "quality_check_sample_rate": 0.1
        }
        
    def get_next_review_task(self, reviewer_id: str, priority: Optional[str] = None) -> Optional[ReviewContext]:
        """Get the next review task for a reviewer."""
        
        # Get pending tasks from audit system
        pending_tasks = self.audit_system.get_pending_reviews(
            reviewer_id=None,  # Get unassigned tasks
            priority=priority
        )
        
        if not pending_tasks:
            logger.info(f"No pending review tasks for reviewer {reviewer_id}")
            return None
            
        # Assign the highest priority task
        task = pending_tasks[0]
        
        # Assign task to reviewer
        if self.audit_system.assign_review_task(task.task_id, reviewer_id):
            # Build comprehensive review context
            context = self._build_review_context(task)
            logger.info(f"📋 Assigned review task {task.task_id} to {reviewer_id}")
            return context
        else:
            logger.warning(f"Failed to assign task {task.task_id} to {reviewer_id}")
            return None
            
    def _build_review_context(self, task) -> ReviewContext:
        """Build comprehensive context for a review task."""
        
        entity_a = task.entity_pair.get("entity_a", {})
        entity_b = task.entity_pair.get("entity_b", {})
        
        # Extract similarity analysis
        similarity_analysis = task.entity_pair.get("similarity_scores", {})
        
        # Build context
        context = ReviewContext(
            task_id=task.task_id,
            entity_pair=task.entity_pair,
            similarity_analysis=similarity_analysis,
            ai_analysis=task.ai_analysis
        )
        
        # Add risk factors analysis
        context.risk_factors = self._identify_risk_factors(entity_a, entity_b, similarity_analysis)
        
        # Extract evidence
        context.supporting_evidence = self._extract_supporting_evidence(entity_a, entity_b, similarity_analysis)
        context.conflicting_evidence = self._extract_conflicting_evidence(entity_a, entity_b)
        
        # Generate reviewer guidance
        if self.config["enable_reviewer_guidance"]:
            context.reviewer_guidance = self._generate_reviewer_guidance(context)
            
        return context
        
    def _identify_risk_factors(self, entity_a: Dict[str, Any], entity_b: Dict[str, Any], 
                             similarity_analysis: Dict[str, Any]) -> List[str]:
        """Identify risk factors that require human attention."""
        risks = []
        
        # Check for conflicting unique identifiers
        unique_fields = ["Email", "Phone", "Website", "ID"]
        for field in unique_fields:
            val_a = str(entity_a.get(field, "")).strip()
            val_b = str(entity_b.get(field, "")).strip()
            
            if val_a and val_b and val_a.lower() != val_b.lower():
                risks.append(f"Conflicting {field}: '{val_a}' vs '{val_b}'")
                
        # Check for temporal inconsistencies
        date_fields = ["Date of Event", "Date Created", "Date Modified"]
        for field in date_fields:
            date_a = entity_a.get(field)
            date_b = entity_b.get(field)
            
            if date_a and date_b and str(date_a) != str(date_b):
                risks.append(f"Different {field}: {date_a} vs {date_b}")
                
        # Check for low similarity scores in critical fields
        critical_fields = ["Full Name", "Organization Name", "Event / Place Name"]
        for field in critical_fields:
            if field in similarity_analysis:
                field_scores = similarity_analysis[field]
                if isinstance(field_scores, dict):
                    composite_score = field_scores.get("composite", 0)
                    if composite_score < 70:
                        risks.append(f"Low {field} similarity: {composite_score:.1f}%")
                        
        # Check for missing key information
        key_fields = ["Full Name", "Organization Name", "Title", "Email"]
        for field in key_fields:
            val_a = entity_a.get(field, "")
            val_b = entity_b.get(field, "")
            
            if not val_a or not val_b:
                risks.append(f"Missing {field} in one entity")
                
        return risks
        
    def _extract_supporting_evidence(self, entity_a: Dict[str, Any], entity_b: Dict[str, Any],
                                   similarity_analysis: Dict[str, Any]) -> List[str]:
        """Extract evidence that supports merging the entities."""
        evidence = []
        
        # Exact matches
        for field, scores in similarity_analysis.items():
            if isinstance(scores, dict) and scores.get("exact", 0) == 100:
                value = entity_a.get(field, entity_b.get(field, "Unknown"))
                evidence.append(f"Exact {field} match: '{value}'")
                
        # High similarity scores
        for field, scores in similarity_analysis.items():
            if isinstance(scores, dict):
                composite = scores.get("composite", 0)
                if composite >= 85:
                    evidence.append(f"High {field} similarity: {composite:.1f}%")
                    
        # AI analysis supporting evidence
        if hasattr(self, 'ai_analysis') and self.ai_analysis:
            ai_evidence = self.ai_analysis.get("key_evidence", [])
            for item in ai_evidence:
                evidence.append(f"AI identified: {item}")
                
        return evidence
        
    def _extract_conflicting_evidence(self, entity_a: Dict[str, Any], entity_b: Dict[str, Any]) -> List[str]:
        """Extract evidence that conflicts with merging the entities."""
        conflicts = []
        
        # Check for different categorical values
        categorical_fields = ["Type", "Category", "Status", "Role"]
        for field in categorical_fields:
            val_a = str(entity_a.get(field, "")).strip()
            val_b = str(entity_b.get(field, "")).strip()
            
            if val_a and val_b and val_a.lower() != val_b.lower():
                conflicts.append(f"Different {field}: '{val_a}' vs '{val_b}'")
                
        # Check for contradictory descriptions
        description_fields = ["Description", "Notes", "Summary"]
        for field in description_fields:
            desc_a = str(entity_a.get(field, "")).lower()
            desc_b = str(entity_b.get(field, "")).lower()
            
            if desc_a and desc_b:
                # Simple check for contradictory words
                contradictions = ["not", "different", "separate", "distinct", "other"]
                if any(word in desc_a and word in desc_b for word in contradictions):
                    conflicts.append(f"Potentially contradictory {field} content")
                    
        return conflicts
        
    def _generate_reviewer_guidance(self, context: ReviewContext) -> Dict[str, Any]:
        """Generate guidance to help the reviewer make a decision."""
        guidance = {
            "decision_framework": [],
            "key_questions": [],
            "red_flags": [],
            "confidence_indicators": []
        }
        
        entity_type = context.entity_pair.get("entity_type", "Unknown")
        
        # Entity-type specific guidance
        if entity_type == "People & Contacts":
            guidance["decision_framework"] = [
                "1. Check for exact email/phone matches (strong evidence)",
                "2. Look for name variations and nicknames",
                "3. Verify organizational connections",
                "4. Consider temporal context and roles"
            ]
            guidance["key_questions"] = [
                "Could these be the same person using different names?",
                "Do the organizational connections make sense?",
                "Are there any conflicting contact details?"
            ]
            guidance["red_flags"] = [
                "Different email domains with no explanation",
                "Conflicting phone numbers",
                "Different organizations with no connection"
            ]
            
        elif entity_type == "Organizations & Bodies":
            guidance["decision_framework"] = [
                "1. Check for exact website/domain matches",
                "2. Look for abbreviation patterns",
                "3. Verify address and contact information",
                "4. Check for name evolution or rebranding"
            ]
            guidance["key_questions"] = [
                "Could this be the same organization with a name change?",
                "Do the key people overlap suggest same organization?",
                "Are the addresses related (same building, etc.)?"
            ]
            guidance["red_flags"] = [
                "Different websites with same organization type",
                "Conflicting addresses in different cities",
                "Different key personnel with no overlap"
            ]
            
        # Add confidence indicators based on analysis
        if context.ai_analysis:
            ai_confidence = context.ai_analysis.get("confidence_score", 0)
            if ai_confidence >= 90:
                guidance["confidence_indicators"].append("AI analysis shows high confidence")
            elif ai_confidence <= 50:
                guidance["confidence_indicators"].append("AI analysis shows low confidence")
                
        # Add risk-based guidance
        if len(context.risk_factors) == 0:
            guidance["confidence_indicators"].append("No significant risk factors identified")
        elif len(context.risk_factors) >= 3:
            guidance["red_flags"].append("Multiple risk factors present - proceed with caution")
            
        return guidance
        
    def submit_review_decision(self, decision: ReviewDecision) -> bool:
        """Submit a reviewer's decision."""
        
        # Validate decision
        validation_errors = self._validate_decision(decision)
        if validation_errors:
            logger.warning(f"Decision validation failed: {validation_errors}")
            return False
            
        try:
            # Submit to audit system
            success = self.audit_system.complete_review_task(
                task_id=decision.task_id,
                reviewer_id=decision.reviewer_id,
                decision=decision.decision,
                confidence=decision.confidence,
                notes=f"{decision.reasoning}\\n\\nNotes: {decision.notes or 'None'}"
            )
            
            if success:
                # Update statistics
                self._update_review_statistics(decision)
                
                # Check for quality assurance
                if self._should_quality_check(decision):
                    self._flag_for_quality_check(decision)
                    
                logger.info(f"✅ Review decision submitted for task {decision.task_id}")
                logger.info(f"   Decision: {decision.decision} (confidence: {decision.confidence}%)")
                
                return True
            else:
                logger.error(f"Failed to submit review decision for task {decision.task_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error submitting review decision: {e}")
            return False
            
    def _validate_decision(self, decision: ReviewDecision) -> List[str]:
        """Validate a review decision."""
        errors = []
        
        # Check required fields
        if not decision.decision:
            errors.append("Decision is required")
            
        if decision.decision not in ["merge", "separate", "defer", "needs_more_info"]:
            errors.append("Invalid decision value")
            
        if self.config["require_confidence_score"]:
            if decision.confidence < 0 or decision.confidence > 100:
                errors.append("Confidence must be between 0 and 100")
                
        if self.config["require_reasoning"]:
            if not decision.reasoning or len(decision.reasoning.strip()) < 10:
                errors.append("Detailed reasoning is required")
                
        # Check review time
        if decision.time_spent_seconds > (self.config["max_review_time_minutes"] * 60):
            errors.append(f"Review time exceeded maximum of {self.config['max_review_time_minutes']} minutes")
            
        return errors
        
    def _update_review_statistics(self, decision: ReviewDecision):
        """Update review statistics."""
        self.stats["reviews_completed"] += 1
        
        if decision.decision == "merge":
            self.stats["merge_decisions"] += 1
        elif decision.decision == "separate":
            self.stats["separate_decisions"] += 1
        elif decision.decision == "defer":
            self.stats["defer_decisions"] += 1
            
        # Update average review time
        total_time = self.stats["average_review_time"] * (self.stats["reviews_completed"] - 1)
        total_time += decision.time_spent_seconds
        self.stats["average_review_time"] = total_time / self.stats["reviews_completed"]
        
        # Track difficult cases
        if (decision.time_spent_seconds > 300 or  # More than 5 minutes
            decision.confidence < 70 or
            "difficult" in decision.flags):
            self.stats["difficult_cases"] += 1
            
    def _should_quality_check(self, decision: ReviewDecision) -> bool:
        """Determine if a decision should be flagged for quality checking."""
        if not self.config["flag_difficult_cases"]:
            return False
            
        # Random sampling
        import random
        if random.random() < self.config["quality_check_sample_rate"]:
            return True
            
        # Flag based on criteria
        quality_flags = [
            decision.confidence < 60,  # Low confidence
            decision.time_spent_seconds < 30,  # Very quick decision
            len(decision.reasoning) < 20,  # Brief reasoning
            "conflict" in decision.reasoning.lower(),  # Mentions conflicts
        ]
        
        return sum(quality_flags) >= 2
        
    def _flag_for_quality_check(self, decision: ReviewDecision):
        """Flag a decision for quality checking."""
        logger.info(f"🔍 Flagging decision {decision.task_id} for quality review")
        # Implementation would add to a quality review queue
        
    def get_reviewer_dashboard(self, reviewer_id: str) -> Dict[str, Any]:
        """Get dashboard information for a reviewer."""
        
        # Get assigned tasks
        assigned_tasks = self.audit_system.get_pending_reviews(reviewer_id=reviewer_id)
        
        # Get reviewer statistics
        reviewer_stats = self.stats.get("reviewer_accuracy", {}).get(reviewer_id, {})
        
        return {
            "assigned_tasks": len(assigned_tasks),
            "next_task_priority": assigned_tasks[0].priority if assigned_tasks else None,
            "reviewer_stats": reviewer_stats,
            "system_stats": {
                "total_pending_reviews": len(self.audit_system.get_pending_reviews()),
                "average_review_time": self.stats["average_review_time"],
                "difficult_cases_percentage": (self.stats["difficult_cases"] / max(self.stats["reviews_completed"], 1)) * 100
            },
            "guidance": {
                "suggested_daily_reviews": 10,
                "estimated_time_per_review": self.stats["average_review_time"] / 60,  # minutes
                "quality_tips": [
                    "Take time to review all evidence carefully",
                    "When in doubt, choose 'defer' for additional review",
                    "Look for patterns in organizational connections",
                    "Consider temporal context for events and activities"
                ]
            }
        }
        
    def generate_review_report(self, days_back: int = 30) -> Dict[str, Any]:
        """Generate a comprehensive review activity report."""
        
        # Get quality metrics from audit system
        quality_metrics = self.audit_system.get_quality_metrics(days_back)
        
        report = {
            "period_days": days_back,
            "review_activity": {
                "total_reviews": self.stats["reviews_completed"],
                "merge_decisions": self.stats["merge_decisions"],
                "separate_decisions": self.stats["separate_decisions"],
                "defer_decisions": self.stats["defer_decisions"]
            },
            "performance_metrics": {
                "average_review_time_minutes": self.stats["average_review_time"] / 60,
                "difficult_cases_rate": (self.stats["difficult_cases"] / max(self.stats["reviews_completed"], 1)) * 100,
                "quality_metrics": quality_metrics
            },
            "recommendations": []
        }
        
        # Add recommendations based on metrics
        if report["performance_metrics"]["average_review_time_minutes"] > 10:
            report["recommendations"].append("Consider providing additional reviewer training to improve efficiency")
            
        if report["performance_metrics"]["difficult_cases_rate"] > 30:
            report["recommendations"].append("High rate of difficult cases - consider improving AI analysis or pre-screening")
            
        return report
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get review interface statistics."""
        return {
            "interface_stats": self.stats.copy(),
            "configuration": self.config
        }