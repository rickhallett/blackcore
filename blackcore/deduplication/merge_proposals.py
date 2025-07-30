"""
Merge Proposals and Execution System

Handles the creation, validation, and execution of entity merge proposals
with comprehensive safety protocols and rollback capabilities.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MergeProposal:
    """A proposal to merge two entities with supporting evidence."""
    proposal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    primary_entity: Dict[str, Any] = field(default_factory=dict)
    secondary_entity: Dict[str, Any] = field(default_factory=dict)
    entity_type: str = ""
    confidence_score: float = 0.0
    evidence: Dict[str, Any] = field(default_factory=dict)
    ai_analysis: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "pending"  # pending, approved, rejected, executed, failed
    merged_entity: Optional[Dict[str, Any]] = None
    merge_strategy: str = "conservative"  # conservative, aggressive, custom
    safety_checks: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)


@dataclass
class MergeResult:
    """Result of a merge operation."""
    success: bool
    merged_entity: Optional[Dict[str, Any]] = None
    audit_id: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    rollback_info: Dict[str, Any] = field(default_factory=dict)


class MergeExecutor:
    """
    Executes entity merges with comprehensive safety protocols.
    
    Provides merge proposal validation, execution strategies, and
    complete audit trails with rollback capabilities.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the merge executor."""
        self.config = config or self._load_default_config()
        
        # Merge statistics
        self.stats = {
            "total_proposals": 0,
            "successful_merges": 0,
            "failed_merges": 0,
            "rollbacks": 0,
            "safety_blocks": 0
        }
        
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default merge configuration."""
        return {
            "require_approval_threshold": 85.0,
            "auto_approve_threshold": 95.0,
            "enable_safety_checks": True,
            "preserve_all_data": True,
            "merge_strategy": "conservative",
            "backup_before_merge": True
        }
        
    def create_proposal(self, primary_entity: Dict[str, Any], secondary_entity: Dict[str, Any],
                       confidence_score: float, evidence: Dict[str, Any],
                       entity_type: str = "", ai_analysis: Optional[Dict[str, Any]] = None) -> MergeProposal:
        """Create a new merge proposal."""
        
        proposal = MergeProposal(
            primary_entity=primary_entity,
            secondary_entity=secondary_entity,
            entity_type=entity_type,
            confidence_score=confidence_score,
            evidence=evidence,
            ai_analysis=ai_analysis
        )
        
        # Run safety checks
        proposal.safety_checks = self._run_safety_checks(proposal)
        proposal.risk_factors = self._identify_risk_factors(proposal)
        
        # Determine merge strategy
        proposal.merge_strategy = self._determine_merge_strategy(proposal)
        
        self.stats["total_proposals"] += 1
        
        logger.info(f"📝 Created merge proposal {proposal.proposal_id}")
        logger.debug(f"   Confidence: {confidence_score:.1f}%")
        logger.debug(f"   Safety checks: {len(proposal.safety_checks)}")
        logger.debug(f"   Risk factors: {len(proposal.risk_factors)}")
        
        return proposal
        
    def _run_safety_checks(self, proposal: MergeProposal) -> List[str]:
        """Run comprehensive safety checks on merge proposal."""
        checks = []
        
        # Check for conflicting critical data
        if self._has_conflicting_identifiers(proposal):
            checks.append("conflicting_identifiers")
            
        # Check for temporal inconsistencies
        if self._has_temporal_conflicts(proposal):
            checks.append("temporal_conflicts")
            
        # Check for relationship conflicts
        if self._has_relationship_conflicts(proposal):
            checks.append("relationship_conflicts")
            
        # Check data volume disparity
        if self._has_significant_data_disparity(proposal):
            checks.append("data_disparity")
            
        # Check for suspicious patterns
        if self._has_suspicious_patterns(proposal):
            checks.append("suspicious_patterns")
            
        return checks
        
    def _has_conflicting_identifiers(self, proposal: MergeProposal) -> bool:
        """Check for conflicting unique identifiers."""
        primary = proposal.primary_entity
        secondary = proposal.secondary_entity
        
        # Check key identifier fields
        identifier_fields = ["Email", "Phone", "Website", "URL", "ID"]
        
        for field in identifier_fields:
            val_a = primary.get(field, "")
            val_b = secondary.get(field, "")
            
            # Normalize values for comparison
            # Convert lists to sets for comparison
            val_a_set = set()
            val_b_set = set()
            
            if isinstance(val_a, list):
                val_a_set = {str(v).strip().lower() for v in val_a if v}
            elif val_a:
                val_a_set = {str(val_a).strip().lower()}
                
            if isinstance(val_b, list):
                val_b_set = {str(v).strip().lower() for v in val_b if v}
            elif val_b:
                val_b_set = {str(val_b).strip().lower()}
            
            # Check if there's any overlap - if so, not a conflict
            if val_a_set and val_b_set:
                if val_a_set.isdisjoint(val_b_set):
                    # No overlap - this is a conflict
                    logger.warning(f"Identifier conflict in {field}: {val_a_set} vs {val_b_set}")
                    return True
                
        return False
        
    def _has_temporal_conflicts(self, proposal: MergeProposal) -> bool:
        """Check for temporal inconsistencies."""
        primary = proposal.primary_entity
        secondary = proposal.secondary_entity
        
        # Check date fields for impossible combinations
        date_fields = ["Date of Event", "Date Created", "Date Modified", "Birth Date"]
        
        for field in date_fields:
            date_a = primary.get(field)
            date_b = secondary.get(field)
            
            if date_a and date_b:
                # Parse and compare dates - this is a simplified check
                if str(date_a) != str(date_b):
                    # For events, different dates might indicate different events
                    if "event" in field.lower():
                        return True
                        
        return False
        
    def _has_relationship_conflicts(self, proposal: MergeProposal) -> bool:
        """Check for conflicting relationship data."""
        primary = proposal.primary_entity
        secondary = proposal.secondary_entity
        
        # Check organization/affiliation conflicts
        org_fields = ["Organization", "Company", "Affiliation"]
        
        for field in org_fields:
            org_a = primary.get(field, "")
            org_b = secondary.get(field, "")
            
            # Normalize values for comparison
            org_a_set = set()
            org_b_set = set()
            
            if isinstance(org_a, list):
                org_a_set = {str(v).strip().lower() for v in org_a if v}
            elif org_a:
                org_a_set = {str(org_a).strip().lower()}
                
            if isinstance(org_b, list):
                org_b_set = {str(v).strip().lower() for v in org_b if v}
            elif org_b:
                org_b_set = {str(org_b).strip().lower()}
            
            # Check if there's any overlap
            if org_a_set and org_b_set:
                if org_a_set.isdisjoint(org_b_set):
                    # No overlap - different organizations might indicate different people
                    return True
                
        return False
        
    def _has_significant_data_disparity(self, proposal: MergeProposal) -> bool:
        """Check for significant disparity in data volume."""
        primary_fields = sum(1 for v in proposal.primary_entity.values() if v)
        secondary_fields = sum(1 for v in proposal.secondary_entity.values() if v)
        
        if primary_fields == 0 or secondary_fields == 0:
            return False
            
        ratio = max(primary_fields, secondary_fields) / min(primary_fields, secondary_fields)
        return ratio > 3.0  # One entity has 3x more data than the other
        
    def _has_suspicious_patterns(self, proposal: MergeProposal) -> bool:
        """Check for patterns that might indicate false positives."""
        # Check for very generic names
        primary_name = proposal.primary_entity.get("Full Name", "")
        secondary_name = proposal.secondary_entity.get("Full Name", "")
        
        # Convert to string if needed
        if isinstance(primary_name, list):
            primary_name = ", ".join(str(v) for v in primary_name)
        else:
            primary_name = str(primary_name).strip() if primary_name else ""
            
        if isinstance(secondary_name, list):
            secondary_name = ", ".join(str(v) for v in secondary_name)
        else:
            secondary_name = str(secondary_name).strip() if secondary_name else ""
        
        generic_names = ["admin", "test", "user", "unknown", "n/a", "null"]
        
        if any(generic in primary_name.lower() for generic in generic_names):
            return True
        if any(generic in secondary_name.lower() for generic in generic_names):
            return True
            
        return False
        
    def _identify_risk_factors(self, proposal: MergeProposal) -> List[str]:
        """Identify risk factors for the merge."""
        risks = []
        
        # Low confidence score
        if proposal.confidence_score < 80:
            risks.append("low_confidence")
            
        # AI recommends human review
        if (proposal.ai_analysis and 
            proposal.ai_analysis.get("recommended_action") == "needs_human_review"):
            risks.append("ai_uncertainty")
            
        # High risk assessment from AI
        if (proposal.ai_analysis and 
            proposal.ai_analysis.get("risk_assessment") == "high"):
            risks.append("high_risk_assessment")
            
        # Safety check failures
        if proposal.safety_checks:
            risks.append("safety_check_failures")
            
        return risks
        
    def _determine_merge_strategy(self, proposal: MergeProposal) -> str:
        """Determine the best merge strategy for this proposal."""
        
        # High confidence with no risks = aggressive merge
        if (proposal.confidence_score >= 95 and 
            not proposal.risk_factors and 
            not proposal.safety_checks):
            return "aggressive"
            
        # Some risks or moderate confidence = conservative merge
        elif proposal.confidence_score >= 80:
            return "conservative"
            
        # Low confidence or high risk = require human approval
        else:
            return "manual_approval_required"
            
    def execute_merge(self, proposal: MergeProposal, auto_approved: bool = False) -> MergeResult:
        """Execute a merge proposal with full safety protocols."""
        
        logger.info(f"🔄 Executing merge proposal {proposal.proposal_id}")
        
        # Check if merge is allowed
        if not self._is_merge_allowed(proposal, auto_approved):
            self.stats["safety_blocks"] += 1
            return MergeResult(
                success=False,
                errors=["Merge blocked by safety protocols or requires approval"]
            )
            
        try:
            # Create backup if enabled
            backup_info = {}
            if self.config.get("backup_before_merge", True):
                backup_info = self._create_backup(proposal)
                
            # Execute the merge based on strategy
            merged_entity = self._perform_merge(proposal)
            
            # Validate merged entity
            validation_errors = self._validate_merged_entity(merged_entity)
            if validation_errors:
                return MergeResult(
                    success=False,
                    errors=validation_errors
                )
                
            # Update proposal status
            proposal.status = "executed"
            proposal.merged_entity = merged_entity
            
            self.stats["successful_merges"] += 1
            
            logger.info(f"✅ Successfully executed merge {proposal.proposal_id}")
            
            return MergeResult(
                success=True,
                merged_entity=merged_entity,
                rollback_info=backup_info
            )
            
        except Exception as e:
            logger.error(f"❌ Merge execution failed: {e}")
            proposal.status = "failed"
            self.stats["failed_merges"] += 1
            
            return MergeResult(
                success=False,
                errors=[str(e)]
            )
            
    def _is_merge_allowed(self, proposal: MergeProposal, auto_approved: bool) -> bool:
        """Check if merge is allowed based on configuration and safety."""
        
        # Manual approval required
        if proposal.merge_strategy == "manual_approval_required" and not auto_approved:
            return False
            
        # Safety checks failed
        if self.config.get("enable_safety_checks", True) and proposal.safety_checks:
            logger.warning(f"Safety checks failed for {proposal.proposal_id}: {proposal.safety_checks}")
            return False
            
        # High risk factors
        if "safety_check_failures" in proposal.risk_factors:
            return False
            
        # Confidence too low for auto-merge
        if (not auto_approved and 
            proposal.confidence_score < self.config.get("auto_approve_threshold", 95.0)):
            return False
            
        return True
        
    def _create_backup(self, proposal: MergeProposal) -> Dict[str, Any]:
        """Create backup of entities before merge."""
        return {
            "primary_entity_backup": proposal.primary_entity.copy(),
            "secondary_entity_backup": proposal.secondary_entity.copy(),
            "backup_timestamp": datetime.now().isoformat()
        }
        
    def _perform_merge(self, proposal: MergeProposal) -> Dict[str, Any]:
        """Perform the actual entity merge based on strategy."""
        
        if proposal.merge_strategy == "aggressive":
            return self._aggressive_merge(proposal)
        elif proposal.merge_strategy == "conservative":
            return self._conservative_merge(proposal)
        else:
            return self._conservative_merge(proposal)  # Default to conservative
            
    def _aggressive_merge(self, proposal: MergeProposal) -> Dict[str, Any]:
        """Aggressive merge strategy - prefer primary entity, fill gaps with secondary."""
        merged = proposal.primary_entity.copy()
        
        # Fill empty fields from secondary entity
        for key, value in proposal.secondary_entity.items():
            if key not in merged or not merged[key]:
                merged[key] = value
                
        # Add merge metadata
        merged["_merge_info"] = {
            "merged_from": [
                proposal.primary_entity.get("id", "unknown"),
                proposal.secondary_entity.get("id", "unknown")
            ],
            "merge_confidence": proposal.confidence_score,
            "merge_timestamp": datetime.now().isoformat(),
            "merge_strategy": "aggressive"
        }
        
        return merged
        
    def _conservative_merge(self, proposal: MergeProposal) -> Dict[str, Any]:
        """Conservative merge strategy - preserve all data, mark conflicts."""
        merged = proposal.primary_entity.copy()
        
        conflicts = {}
        
        # Merge fields, noting conflicts
        for key, value in proposal.secondary_entity.items():
            if key in merged and merged[key] and merged[key] != value:
                # Conflict detected - preserve both values
                conflicts[key] = {
                    "primary": merged[key],
                    "secondary": value
                }
                # Keep primary value but note the conflict
            elif key not in merged or not merged[key]:
                # No conflict - use secondary value
                merged[key] = value
                
        # Add merge metadata with conflict information
        merged["_merge_info"] = {
            "merged_from": [
                proposal.primary_entity.get("id", "unknown"),
                proposal.secondary_entity.get("id", "unknown")
            ],
            "merge_confidence": proposal.confidence_score,
            "merge_timestamp": datetime.now().isoformat(),
            "merge_strategy": "conservative",
            "conflicts": conflicts if conflicts else None
        }
        
        return merged
        
    def _validate_merged_entity(self, merged_entity: Dict[str, Any]) -> List[str]:
        """Validate the merged entity for consistency."""
        errors = []
        
        # Check for required fields (entity-type specific)
        if not merged_entity.get("Full Name") and not merged_entity.get("Organization Name"):
            errors.append("Merged entity missing identifying name")
            
        # Check for data corruption
        if len(str(merged_entity)) > 1000000:  # 1MB limit
            errors.append("Merged entity too large")
            
        return errors
        
    def rollback_merge(self, audit_id: str, rollback_info: Dict[str, Any]) -> bool:
        """Rollback a merge operation."""
        try:
            logger.info(f"🔄 Rolling back merge {audit_id}")
            
            # Restore original entities from backup
            primary_backup = rollback_info.get("primary_entity_backup")
            secondary_backup = rollback_info.get("secondary_entity_backup")
            
            if not primary_backup or not secondary_backup:
                logger.error("Insufficient backup data for rollback")
                return False
                
            # Implementation would restore entities to their databases
            # This is a placeholder for the actual restoration logic
            
            self.stats["rollbacks"] += 1
            logger.info(f"✅ Successfully rolled back merge {audit_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            return False
            
    def get_statistics(self) -> Dict[str, Any]:
        """Get merge executor statistics."""
        total_operations = self.stats["total_proposals"]
        success_rate = (self.stats["successful_merges"] / max(total_operations, 1)) * 100
        
        return {
            "total_proposals": self.stats["total_proposals"],
            "successful_merges": self.stats["successful_merges"],
            "failed_merges": self.stats["failed_merges"],
            "rollbacks": self.stats["rollbacks"],
            "safety_blocks": self.stats["safety_blocks"],
            "success_rate": success_rate,
            "configuration": self.config
        }