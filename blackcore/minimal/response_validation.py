"""
Response Quality Validation Framework

Provides comprehensive validation for LLM responses including
structural validation, semantic consistency, and confidence calibration.
"""

import json
import re
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import numpy as np

from .models import ExtractedEntities, ExtractedEntity, EntityType, ExtractedRelationship


@dataclass
class ValidationIssue:
    """Represents a validation issue found in LLM response."""
    severity: str  # critical, warning, info
    category: str  # structure, consistency, semantic, confidence
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Complete validation result for an LLM response."""
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    quality_score: float = 1.0  # 0-1 score
    
    # Detailed scores
    structural_score: float = 1.0
    consistency_score: float = 1.0
    semantic_score: float = 1.0
    confidence_score: float = 1.0
    
    # Statistics
    stats: Dict[str, Any] = field(default_factory=dict)


class ResponseValidator:
    """Validates LLM responses for quality and consistency."""
    
    # Validation rules
    ENTITY_NAME_PATTERN = re.compile(r'^[\w\s\-\'\.]+$')
    MIN_CONFIDENCE = 0.0
    MAX_CONFIDENCE = 1.0
    
    # Known entity patterns for validation
    PERSON_NAME_PATTERN = re.compile(r'^[A-Z][a-z]+([\s\-][A-Z][a-z]+)*$')
    ORG_NAME_PATTERN = re.compile(r'^[\w\s\&\-\'\.]+$')
    EMAIL_PATTERN = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w+$')
    PHONE_PATTERN = re.compile(r'^[\+\d\s\-\(\)]+$')
    
    def __init__(
        self,
        strict_mode: bool = False,
        custom_rules: Optional[Dict[str, Any]] = None
    ):
        """Initialize validator.
        
        Args:
            strict_mode: Whether to use strict validation
            custom_rules: Custom validation rules
        """
        self.strict_mode = strict_mode
        self.custom_rules = custom_rules or {}
        
    def validate_response(
        self,
        response: ExtractedEntities,
        transcript: Optional[str] = None,
        expected_types: Optional[Set[EntityType]] = None
    ) -> ValidationResult:
        """Validate complete LLM response.
        
        Args:
            response: Extracted entities from LLM
            transcript: Original transcript for context
            expected_types: Expected entity types
            
        Returns:
            Comprehensive validation result
        """
        issues = []
        
        # Structural validation
        structural_issues = self._validate_structure(response)
        issues.extend(structural_issues)
        structural_score = 1.0 - (len(structural_issues) * 0.1)
        
        # Consistency validation
        consistency_issues = self._validate_consistency(response)
        issues.extend(consistency_issues)
        consistency_score = 1.0 - (len(consistency_issues) * 0.15)
        
        # Semantic validation
        semantic_issues = self._validate_semantics(response, transcript)
        issues.extend(semantic_issues)
        semantic_score = 1.0 - (len(semantic_issues) * 0.2)
        
        # Confidence validation
        confidence_issues = self._validate_confidence(response)
        issues.extend(confidence_issues)
        confidence_score = 1.0 - (len(confidence_issues) * 0.05)
        
        # Type validation
        if expected_types:
            type_issues = self._validate_expected_types(response, expected_types)
            issues.extend(type_issues)
        
        # Calculate overall score
        quality_score = np.mean([
            structural_score,
            consistency_score,
            semantic_score,
            confidence_score
        ])
        
        # Determine if valid
        critical_issues = [i for i in issues if i.severity == 'critical']
        is_valid = len(critical_issues) == 0 and quality_score >= 0.5
        
        # Gather statistics
        stats = self._gather_statistics(response)
        
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            quality_score=max(0, min(1, quality_score)),
            structural_score=max(0, min(1, structural_score)),
            consistency_score=max(0, min(1, consistency_score)),
            semantic_score=max(0, min(1, semantic_score)),
            confidence_score=max(0, min(1, confidence_score)),
            stats=stats
        )
    
    def _validate_structure(self, response: ExtractedEntities) -> List[ValidationIssue]:
        """Validate response structure."""
        issues = []
        
        # Check entities
        if not response.entities and not response.summary:
            issues.append(ValidationIssue(
                severity='critical',
                category='structure',
                message='Empty response - no entities or summary',
                details={'response_length': 0}
            ))
        
        # Validate each entity
        for i, entity in enumerate(response.entities):
            # Check required fields
            if not entity.name or not entity.name.strip():
                issues.append(ValidationIssue(
                    severity='critical',
                    category='structure',
                    message=f'Entity {i} has empty name',
                    details={'entity_index': i}
                ))
            
            # Check name format
            if entity.name and not self.ENTITY_NAME_PATTERN.match(entity.name):
                issues.append(ValidationIssue(
                    severity='warning',
                    category='structure',
                    message=f'Entity name contains invalid characters: {entity.name}',
                    details={'entity_name': entity.name, 'entity_index': i}
                ))
            
            # Check entity type
            if not isinstance(entity.type, EntityType):
                issues.append(ValidationIssue(
                    severity='critical',
                    category='structure',
                    message=f'Invalid entity type: {entity.type}',
                    details={'entity_index': i, 'invalid_type': str(entity.type)}
                ))
        
        # Validate relationships
        for i, rel in enumerate(response.relationships):
            # Check required fields
            if not rel.source_entity or not rel.target_entity:
                issues.append(ValidationIssue(
                    severity='critical',
                    category='structure',
                    message=f'Relationship {i} missing source or target',
                    details={'relationship_index': i}
                ))
            
            # Check relationship type
            if not rel.relationship_type:
                issues.append(ValidationIssue(
                    severity='warning',
                    category='structure',
                    message=f'Relationship {i} missing type',
                    details={'relationship_index': i}
                ))
        
        return issues
    
    def _validate_consistency(self, response: ExtractedEntities) -> List[ValidationIssue]:
        """Validate internal consistency."""
        issues = []
        
        # Check for duplicate entities
        entity_names = defaultdict(list)
        for i, entity in enumerate(response.entities):
            key = (entity.name.lower(), entity.type)
            entity_names[key].append(i)
        
        for (name, entity_type), indices in entity_names.items():
            if len(indices) > 1:
                issues.append(ValidationIssue(
                    severity='warning',
                    category='consistency',
                    message=f'Duplicate entity: {name} ({entity_type.value})',
                    details={'indices': indices, 'count': len(indices)}
                ))
        
        # Check relationship consistency
        entity_names_set = {e.name for e in response.entities}
        
        for i, rel in enumerate(response.relationships):
            # Check if entities exist
            if rel.source_entity not in entity_names_set:
                issues.append(ValidationIssue(
                    severity='critical',
                    category='consistency',
                    message=f'Relationship references non-existent source: {rel.source_entity}',
                    details={'relationship_index': i, 'missing_entity': rel.source_entity}
                ))
            
            if rel.target_entity not in entity_names_set:
                issues.append(ValidationIssue(
                    severity='critical',
                    category='consistency',
                    message=f'Relationship references non-existent target: {rel.target_entity}',
                    details={'relationship_index': i, 'missing_entity': rel.target_entity}
                ))
            
            # Check for self-relationships
            if rel.source_entity == rel.target_entity:
                issues.append(ValidationIssue(
                    severity='warning',
                    category='consistency',
                    message=f'Self-relationship detected: {rel.source_entity}',
                    details={'relationship_index': i}
                ))
        
        # Check for orphaned entities (no relationships)
        entities_in_relationships = set()
        for rel in response.relationships:
            entities_in_relationships.add(rel.source_entity)
            entities_in_relationships.add(rel.target_entity)
        
        orphaned = [e.name for e in response.entities if e.name not in entities_in_relationships]
        if orphaned and len(response.entities) > 3:  # Only flag if many entities
            issues.append(ValidationIssue(
                severity='info',
                category='consistency',
                message=f'{len(orphaned)} entities have no relationships',
                details={'orphaned_entities': orphaned}
            ))
        
        return issues
    
    def _validate_semantics(
        self,
        response: ExtractedEntities,
        transcript: Optional[str] = None
    ) -> List[ValidationIssue]:
        """Validate semantic correctness."""
        issues = []
        
        # Type-specific validation
        for i, entity in enumerate(response.entities):
            if entity.type == EntityType.PERSON:
                # Validate person name format
                if self.strict_mode and not self.PERSON_NAME_PATTERN.match(entity.name):
                    issues.append(ValidationIssue(
                        severity='info',
                        category='semantic',
                        message=f'Person name may be incorrectly formatted: {entity.name}',
                        details={'entity_index': i, 'name': entity.name}
                    ))
                
                # Check email format if present
                if entity.properties and 'email' in entity.properties:
                    email = entity.properties['email']
                    if not self.EMAIL_PATTERN.match(email):
                        issues.append(ValidationIssue(
                            severity='warning',
                            category='semantic',
                            message=f'Invalid email format: {email}',
                            details={'entity_index': i, 'email': email}
                        ))
            
            elif entity.type == EntityType.ORGANIZATION:
                # Validate org name
                if not self.ORG_NAME_PATTERN.match(entity.name):
                    issues.append(ValidationIssue(
                        severity='info',
                        category='semantic',
                        message=f'Organization name contains unusual characters: {entity.name}',
                        details={'entity_index': i, 'name': entity.name}
                    ))
            
            elif entity.type == EntityType.TASK:
                # Tasks should have action words
                action_words = ['complete', 'review', 'create', 'update', 'fix', 'implement']
                if not any(word in entity.name.lower() for word in action_words):
                    issues.append(ValidationIssue(
                        severity='info',
                        category='semantic',
                        message=f'Task may not be actionable: {entity.name}',
                        details={'entity_index': i, 'name': entity.name}
                    ))
        
        # Validate against transcript if provided
        if transcript:
            transcript_lower = transcript.lower()
            
            # Check if entities are mentioned in transcript
            for entity in response.entities:
                # Simple substring check (could be more sophisticated)
                if entity.name.lower() not in transcript_lower:
                    # Check for partial matches
                    name_parts = entity.name.lower().split()
                    if not any(part in transcript_lower for part in name_parts if len(part) > 3):
                        issues.append(ValidationIssue(
                            severity='warning',
                            category='semantic',
                            message=f'Entity not found in transcript: {entity.name}',
                            details={'entity_name': entity.name}
                        ))
        
        # Validate relationship types
        valid_relationship_types = {
            'works_for', 'manages', 'reports_to', 'owns', 'participates_in',
            'located_at', 'scheduled_for', 'assigned_to', 'related_to',
            'mentions', 'created_by', 'responsible_for'
        }
        
        for i, rel in enumerate(response.relationships):
            if rel.relationship_type not in valid_relationship_types:
                issues.append(ValidationIssue(
                    severity='info',
                    category='semantic',
                    message=f'Non-standard relationship type: {rel.relationship_type}',
                    details={'relationship_index': i, 'type': rel.relationship_type}
                ))
        
        return issues
    
    def _validate_confidence(self, response: ExtractedEntities) -> List[ValidationIssue]:
        """Validate confidence scores."""
        issues = []
        
        confidences = [e.confidence for e in response.entities]
        
        if not confidences:
            return issues
        
        # Check confidence range
        for i, entity in enumerate(response.entities):
            if entity.confidence < self.MIN_CONFIDENCE or entity.confidence > self.MAX_CONFIDENCE:
                issues.append(ValidationIssue(
                    severity='critical',
                    category='confidence',
                    message=f'Confidence out of range: {entity.confidence}',
                    details={'entity_index': i, 'confidence': entity.confidence}
                ))
        
        # Check confidence distribution
        avg_confidence = np.mean(confidences)
        std_confidence = np.std(confidences)
        
        # Flag if all confidences are the same (likely default value)
        if std_confidence == 0 and len(confidences) > 3:
            issues.append(ValidationIssue(
                severity='warning',
                category='confidence',
                message='All entities have identical confidence scores',
                details={'confidence': avg_confidence, 'count': len(confidences)}
            ))
        
        # Flag if confidence is suspiciously high
        if avg_confidence > 0.95:
            issues.append(ValidationIssue(
                severity='info',
                category='confidence',
                message='Unusually high average confidence',
                details={'avg_confidence': avg_confidence}
            ))
        
        # Flag if confidence is suspiciously low
        if avg_confidence < 0.3:
            issues.append(ValidationIssue(
                severity='warning',
                category='confidence',
                message='Very low average confidence',
                details={'avg_confidence': avg_confidence}
            ))
        
        # Check confidence calibration
        if len(confidences) > 10:
            # Entities with high confidence should have more properties
            high_conf_entities = [e for e in response.entities if e.confidence > 0.8]
            low_conf_entities = [e for e in response.entities if e.confidence < 0.5]
            
            if high_conf_entities and low_conf_entities:
                avg_props_high = np.mean([len(e.properties or {}) for e in high_conf_entities])
                avg_props_low = np.mean([len(e.properties or {}) for e in low_conf_entities])
                
                if avg_props_high < avg_props_low:
                    issues.append(ValidationIssue(
                        severity='warning',
                        category='confidence',
                        message='Confidence may be poorly calibrated',
                        details={
                            'high_conf_avg_props': avg_props_high,
                            'low_conf_avg_props': avg_props_low
                        }
                    ))
        
        return issues
    
    def _validate_expected_types(
        self,
        response: ExtractedEntities,
        expected_types: Set[EntityType]
    ) -> List[ValidationIssue]:
        """Validate against expected entity types."""
        issues = []
        
        found_types = {e.type for e in response.entities}
        missing_types = expected_types - found_types
        
        if missing_types:
            issues.append(ValidationIssue(
                severity='info',
                category='structure',
                message=f'Missing expected entity types: {[t.value for t in missing_types]}',
                details={'missing_types': [t.value for t in missing_types]}
            ))
        
        return issues
    
    def _gather_statistics(self, response: ExtractedEntities) -> Dict[str, Any]:
        """Gather response statistics."""
        stats = {
            'entity_count': len(response.entities),
            'relationship_count': len(response.relationships),
            'unique_entity_types': len({e.type for e in response.entities}),
            'avg_confidence': np.mean([e.confidence for e in response.entities]) if response.entities else 0,
            'entity_type_distribution': defaultdict(int),
            'relationship_type_distribution': defaultdict(int),
            'avg_properties_per_entity': 0,
            'avg_context_length': 0
        }
        
        # Entity type distribution
        for entity in response.entities:
            stats['entity_type_distribution'][entity.type.value] += 1
        
        # Relationship type distribution
        for rel in response.relationships:
            stats['relationship_type_distribution'][rel.relationship_type] += 1
        
        # Average properties
        if response.entities:
            props_counts = [len(e.properties or {}) for e in response.entities]
            stats['avg_properties_per_entity'] = np.mean(props_counts)
        
        # Average context length
        if response.entities:
            context_lengths = [len(e.context or '') for e in response.entities]
            stats['avg_context_length'] = np.mean(context_lengths)
        
        # Convert defaultdicts to regular dicts
        stats['entity_type_distribution'] = dict(stats['entity_type_distribution'])
        stats['relationship_type_distribution'] = dict(stats['relationship_type_distribution'])
        
        return stats
    
    def validate_batch(
        self,
        responses: List[ExtractedEntities],
        transcripts: Optional[List[str]] = None
    ) -> List[ValidationResult]:
        """Validate multiple responses."""
        results = []
        
        for i, response in enumerate(responses):
            transcript = transcripts[i] if transcripts and i < len(transcripts) else None
            result = self.validate_response(response, transcript)
            results.append(result)
        
        return results
    
    def generate_validation_report(
        self,
        results: List[ValidationResult]
    ) -> Dict[str, Any]:
        """Generate summary report from validation results."""
        report = {
            'total_responses': len(results),
            'valid_responses': sum(1 for r in results if r.is_valid),
            'avg_quality_score': np.mean([r.quality_score for r in results]),
            'issue_summary': defaultdict(lambda: defaultdict(int)),
            'score_distribution': {
                'structural': np.mean([r.structural_score for r in results]),
                'consistency': np.mean([r.consistency_score for r in results]),
                'semantic': np.mean([r.semantic_score for r in results]),
                'confidence': np.mean([r.confidence_score for r in results])
            },
            'common_issues': []
        }
        
        # Aggregate issues
        issue_counts = defaultdict(int)
        for result in results:
            for issue in result.issues:
                key = f"{issue.category}:{issue.message}"
                issue_counts[key] += 1
                report['issue_summary'][issue.category][issue.severity] += 1
        
        # Find most common issues
        report['common_issues'] = sorted(
            issue_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # Convert defaultdicts
        report['issue_summary'] = {
            k: dict(v) for k, v in report['issue_summary'].items()
        }
        
        return report


class ConfidenceCalibrator:
    """Calibrates LLM confidence scores based on historical accuracy."""
    
    def __init__(self):
        self.calibration_data = []
        
    def add_sample(
        self,
        predicted_confidence: float,
        actual_accuracy: float,
        entity_type: EntityType
    ):
        """Add a calibration sample."""
        self.calibration_data.append({
            'predicted': predicted_confidence,
            'actual': actual_accuracy,
            'type': entity_type
        })
    
    def calibrate_confidence(
        self,
        raw_confidence: float,
        entity_type: Optional[EntityType] = None
    ) -> float:
        """Calibrate confidence based on historical data."""
        if not self.calibration_data:
            return raw_confidence
        
        # Filter by entity type if specified
        data = self.calibration_data
        if entity_type:
            data = [d for d in data if d['type'] == entity_type]
        
        if not data:
            return raw_confidence
        
        # Simple linear calibration
        predicted_vals = [d['predicted'] for d in data]
        actual_vals = [d['actual'] for d in data]
        
        # Find similar confidence values
        similar_data = [
            d for d in data 
            if abs(d['predicted'] - raw_confidence) < 0.1
        ]
        
        if similar_data:
            # Use average of similar samples
            avg_actual = np.mean([d['actual'] for d in similar_data])
            return avg_actual
        else:
            # Linear interpolation
            return np.interp(raw_confidence, predicted_vals, actual_vals)
    
    def get_calibration_curve(
        self,
        entity_type: Optional[EntityType] = None,
        bins: int = 10
    ) -> Tuple[List[float], List[float]]:
        """Get calibration curve data."""
        if not self.calibration_data:
            return [], []
        
        # Filter by type
        data = self.calibration_data
        if entity_type:
            data = [d for d in data if d['type'] == entity_type]
        
        # Bin the data
        bin_edges = np.linspace(0, 1, bins + 1)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        
        binned_predicted = []
        binned_actual = []
        
        for i in range(bins):
            bin_data = [
                d for d in data 
                if bin_edges[i] <= d['predicted'] < bin_edges[i+1]
            ]
            
            if bin_data:
                binned_predicted.append(bin_centers[i])
                binned_actual.append(np.mean([d['actual'] for d in bin_data]))
        
        return binned_predicted, binned_actual