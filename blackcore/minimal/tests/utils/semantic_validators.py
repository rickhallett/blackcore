"""Semantic validators for AI entity extraction accuracy."""

import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class EntityType(Enum):
    """Types of entities that can be extracted."""
    PERSON = "person"
    ORGANIZATION = "organization"
    PLACE = "place"
    EVENT = "event"
    TASK = "task"
    TRANSGRESSION = "transgression"


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """A validation issue found during semantic validation."""
    entity_type: EntityType
    field: str
    message: str
    severity: ValidationSeverity
    expected: Optional[Any] = None
    actual: Optional[Any] = None


@dataclass
class ValidationResult:
    """Result of semantic validation."""
    is_valid: bool
    confidence_score: float  # 0.0 to 1.0
    issues: List[ValidationIssue]
    suggestions: List[str]


class SemanticValidator:
    """Base validator for semantic validation of extracted entities."""
    
    def __init__(self):
        self.validators = {
            EntityType.PERSON: PersonValidator(),
            EntityType.ORGANIZATION: OrganizationValidator(),
            EntityType.PLACE: PlaceValidator(),
            EntityType.EVENT: EventValidator(),
            EntityType.TASK: TaskValidator(),
            EntityType.TRANSGRESSION: TransgressionValidator()
        }
    
    def validate_entity(self, entity: Dict[str, Any], entity_type: EntityType, 
                       context: Optional[str] = None) -> ValidationResult:
        """Validate a single entity for semantic correctness."""
        if entity_type not in self.validators:
            return ValidationResult(
                is_valid=False,
                confidence_score=0.0,
                issues=[ValidationIssue(
                    entity_type=entity_type,
                    field="type",
                    message=f"Unknown entity type: {entity_type}",
                    severity=ValidationSeverity.ERROR
                )],
                suggestions=[]
            )
        
        validator = self.validators[entity_type]
        return validator.validate(entity, context)
    
    def validate_relationships(self, entities: List[Dict[str, Any]], 
                             relationships: List[Dict[str, Any]]) -> ValidationResult:
        """Validate relationships between entities for logical consistency."""
        issues = []
        suggestions = []
        
        # Build entity index
        entity_index = {e.get("id"): e for e in entities}
        
        for rel in relationships:
            source_id = rel.get("source")
            target_id = rel.get("target")
            rel_type = rel.get("type")
            
            # Check if entities exist
            if source_id not in entity_index:
                issues.append(ValidationIssue(
                    entity_type=EntityType.PERSON,  # Default, could be any
                    field="relationship",
                    message=f"Source entity {source_id} not found",
                    severity=ValidationSeverity.ERROR
                ))
                continue
                
            if target_id not in entity_index:
                issues.append(ValidationIssue(
                    entity_type=EntityType.PERSON,  # Default, could be any
                    field="relationship",
                    message=f"Target entity {target_id} not found",
                    severity=ValidationSeverity.ERROR
                ))
                continue
            
            # Validate relationship makes sense
            source = entity_index[source_id]
            target = entity_index[target_id]
            
            if not self._is_valid_relationship(source, target, rel_type):
                issues.append(ValidationIssue(
                    entity_type=EntityType.PERSON,  # Default
                    field="relationship",
                    message=f"Invalid relationship '{rel_type}' between {source.get('type')} and {target.get('type')}",
                    severity=ValidationSeverity.WARNING
                ))
                suggestions.append(f"Consider if '{rel_type}' is appropriate for these entity types")
        
        confidence = 1.0 - (len(issues) * 0.1)  # Reduce confidence per issue
        return ValidationResult(
            is_valid=len([i for i in issues if i.severity == ValidationSeverity.ERROR]) == 0,
            confidence_score=max(0.0, confidence),
            issues=issues,
            suggestions=suggestions
        )
    
    def _is_valid_relationship(self, source: Dict, target: Dict, rel_type: str) -> bool:
        """Check if a relationship type makes sense between two entity types."""
        valid_relationships = {
            ("person", "organization"): ["works_at", "owns", "founded", "manages"],
            ("person", "person"): ["knows", "reports_to", "married_to", "related_to"],
            ("organization", "organization"): ["subsidiary_of", "partner_with", "competes_with"],
            ("person", "event"): ["attended", "organized", "spoke_at"],
            ("organization", "place"): ["located_at", "operates_in"],
            ("person", "transgression"): ["committed", "reported", "investigated"],
        }
        
        source_type = source.get("type", "").lower()
        target_type = target.get("type", "").lower()
        
        # Check both directions
        for (s, t), valid_rels in valid_relationships.items():
            if (source_type == s and target_type == t) or (source_type == t and target_type == s):
                if rel_type.lower() in [r.lower() for r in valid_rels]:
                    return True
        
        return False


class PersonValidator:
    """Validator for person entities."""
    
    def validate(self, entity: Dict[str, Any], context: Optional[str] = None) -> ValidationResult:
        """Validate a person entity."""
        issues = []
        suggestions = []
        
        # Check required fields
        name = entity.get("name", "").strip()
        if not name:
            issues.append(ValidationIssue(
                entity_type=EntityType.PERSON,
                field="name",
                message="Person name is required",
                severity=ValidationSeverity.ERROR
            ))
        else:
            # Validate name format
            if not self._is_valid_person_name(name):
                issues.append(ValidationIssue(
                    entity_type=EntityType.PERSON,
                    field="name",
                    message=f"'{name}' doesn't appear to be a valid person name",
                    severity=ValidationSeverity.WARNING
                ))
                suggestions.append("Check if this might be an organization or title instead")
        
        # Check email format if present
        email = entity.get("email")
        if email and not self._is_valid_email(email):
            issues.append(ValidationIssue(
                entity_type=EntityType.PERSON,
                field="email",
                message=f"Invalid email format: {email}",
                severity=ValidationSeverity.WARNING
            ))
        
        # Check phone format if present
        phone = entity.get("phone")
        if phone and not self._is_valid_phone(phone):
            issues.append(ValidationIssue(
                entity_type=EntityType.PERSON,
                field="phone",
                message=f"Invalid phone format: {phone}",
                severity=ValidationSeverity.INFO
            ))
        
        # Check role/title makes sense
        role = entity.get("role", "")
        if role and self._looks_like_organization(role):
            issues.append(ValidationIssue(
                entity_type=EntityType.PERSON,
                field="role",
                message=f"Role '{role}' looks like an organization name",
                severity=ValidationSeverity.WARNING
            ))
            suggestions.append("Consider extracting this as a separate organization entity")
        
        # Context validation
        if context and name:
            if name.lower() not in context.lower():
                issues.append(ValidationIssue(
                    entity_type=EntityType.PERSON,
                    field="name",
                    message=f"Person name '{name}' not found in provided context",
                    severity=ValidationSeverity.WARNING
                ))
        
        confidence = self._calculate_confidence(issues)
        return ValidationResult(
            is_valid=len([i for i in issues if i.severity == ValidationSeverity.ERROR]) == 0,
            confidence_score=confidence,
            issues=issues,
            suggestions=suggestions
        )
    
    def _is_valid_person_name(self, name: str) -> bool:
        """Check if a string looks like a person's name."""
        # Common patterns that indicate NOT a person name
        org_indicators = ["inc", "ltd", "llc", "corp", "company", "foundation", "institute"]
        name_lower = name.lower()
        
        for indicator in org_indicators:
            if indicator in name_lower:
                return False
        
        # Should have at least one space (first and last name)
        # But allow single names for certain cultures
        if " " not in name and len(name) < 3:
            return False
        
        # Check for common name patterns
        name_pattern = re.compile(r'^[A-Za-z\s\'-\.]+$')
        return bool(name_pattern.match(name))
    
    def _is_valid_email(self, email: str) -> bool:
        """Check if email format is valid."""
        email_pattern = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w+$')
        return bool(email_pattern.match(email))
    
    def _is_valid_phone(self, phone: str) -> bool:
        """Check if phone format is valid."""
        # Remove common separators
        cleaned = re.sub(r'[\s\-\(\)\+]', '', phone)
        # Should be mostly digits
        return len(cleaned) >= 7 and cleaned[1:].isdigit()
    
    def _looks_like_organization(self, text: str) -> bool:
        """Check if text looks more like an organization than a role."""
        org_indicators = ["inc", "ltd", "llc", "corp", "company", "&", "and sons"]
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in org_indicators)
    
    def _calculate_confidence(self, issues: List[ValidationIssue]) -> float:
        """Calculate confidence score based on issues."""
        if not issues:
            return 1.0
        
        # Reduce confidence based on issue severity
        confidence = 1.0
        for issue in issues:
            if issue.severity == ValidationSeverity.ERROR:
                confidence -= 0.3
            elif issue.severity == ValidationSeverity.WARNING:
                confidence -= 0.15
            elif issue.severity == ValidationSeverity.INFO:
                confidence -= 0.05
        
        return max(0.0, confidence)


class OrganizationValidator:
    """Validator for organization entities."""
    
    def validate(self, entity: Dict[str, Any], context: Optional[str] = None) -> ValidationResult:
        """Validate an organization entity."""
        issues = []
        suggestions = []
        
        # Check required fields
        name = entity.get("name", "").strip()
        if not name:
            issues.append(ValidationIssue(
                entity_type=EntityType.ORGANIZATION,
                field="name",
                message="Organization name is required",
                severity=ValidationSeverity.ERROR
            ))
        else:
            # Check if it looks like a person name
            if self._looks_like_person_name(name):
                issues.append(ValidationIssue(
                    entity_type=EntityType.ORGANIZATION,
                    field="name",
                    message=f"'{name}' appears to be a person's name, not an organization",
                    severity=ValidationSeverity.WARNING
                ))
                suggestions.append("Consider extracting this as a person entity instead")
        
        # Validate organization type
        org_type = entity.get("type", "")
        if org_type and org_type not in self._get_valid_org_types():
            issues.append(ValidationIssue(
                entity_type=EntityType.ORGANIZATION,
                field="type",
                message=f"Unknown organization type: {org_type}",
                severity=ValidationSeverity.INFO
            ))
        
        # Check website format
        website = entity.get("website")
        if website and not self._is_valid_url(website):
            issues.append(ValidationIssue(
                entity_type=EntityType.ORGANIZATION,
                field="website",
                message=f"Invalid website URL: {website}",
                severity=ValidationSeverity.WARNING
            ))
        
        confidence = self._calculate_confidence(issues)
        return ValidationResult(
            is_valid=len([i for i in issues if i.severity == ValidationSeverity.ERROR]) == 0,
            confidence_score=confidence,
            issues=issues,
            suggestions=suggestions
        )
    
    def _looks_like_person_name(self, name: str) -> bool:
        """Check if name looks like a person rather than organization."""
        # Simple heuristic: if it's 2-3 words and doesn't have org indicators
        words = name.split()
        if 2 <= len(words) <= 3:
            org_indicators = ["inc", "ltd", "llc", "corp", "company", "&"]
            name_lower = name.lower()
            if not any(indicator in name_lower for indicator in org_indicators):
                # Could be a person's name
                return True
        return False
    
    def _get_valid_org_types(self) -> List[str]:
        """Get list of valid organization types."""
        return [
            "corporation", "nonprofit", "government", "educational",
            "healthcare", "technology", "finance", "retail", "manufacturing"
        ]
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL format is valid."""
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return bool(url_pattern.match(url))
    
    def _calculate_confidence(self, issues: List[ValidationIssue]) -> float:
        """Calculate confidence score based on issues."""
        if not issues:
            return 1.0
        
        confidence = 1.0
        for issue in issues:
            if issue.severity == ValidationSeverity.ERROR:
                confidence -= 0.3
            elif issue.severity == ValidationSeverity.WARNING:
                confidence -= 0.15
            elif issue.severity == ValidationSeverity.INFO:
                confidence -= 0.05
        
        return max(0.0, confidence)


class PlaceValidator:
    """Validator for place entities."""
    
    def validate(self, entity: Dict[str, Any], context: Optional[str] = None) -> ValidationResult:
        """Validate a place entity."""
        issues = []
        suggestions = []
        
        name = entity.get("name", "").strip()
        if not name:
            issues.append(ValidationIssue(
                entity_type=EntityType.PLACE,
                field="name",
                message="Place name is required",
                severity=ValidationSeverity.ERROR
            ))
        
        # Check coordinates if provided
        lat = entity.get("latitude")
        lon = entity.get("longitude")
        if lat is not None or lon is not None:
            if not self._are_valid_coordinates(lat, lon):
                issues.append(ValidationIssue(
                    entity_type=EntityType.PLACE,
                    field="coordinates",
                    message=f"Invalid coordinates: lat={lat}, lon={lon}",
                    severity=ValidationSeverity.WARNING
                ))
        
        confidence = self._calculate_confidence(issues)
        return ValidationResult(
            is_valid=len([i for i in issues if i.severity == ValidationSeverity.ERROR]) == 0,
            confidence_score=confidence,
            issues=issues,
            suggestions=suggestions
        )
    
    def _are_valid_coordinates(self, lat: Any, lon: Any) -> bool:
        """Check if coordinates are valid."""
        try:
            lat_f = float(lat)
            lon_f = float(lon)
            return -90 <= lat_f <= 90 and -180 <= lon_f <= 180
        except (TypeError, ValueError):
            return False
    
    def _calculate_confidence(self, issues: List[ValidationIssue]) -> float:
        """Calculate confidence score based on issues."""
        if not issues:
            return 1.0
        
        confidence = 1.0
        for issue in issues:
            if issue.severity == ValidationSeverity.ERROR:
                confidence -= 0.3
            elif issue.severity == ValidationSeverity.WARNING:
                confidence -= 0.15
        
        return max(0.0, confidence)


class EventValidator:
    """Validator for event entities."""
    
    def validate(self, entity: Dict[str, Any], context: Optional[str] = None) -> ValidationResult:
        """Validate an event entity."""
        issues = []
        suggestions = []
        
        name = entity.get("name", "").strip()
        if not name:
            issues.append(ValidationIssue(
                entity_type=EntityType.EVENT,
                field="name",
                message="Event name is required",
                severity=ValidationSeverity.ERROR
            ))
        
        # Check date validity
        date = entity.get("date")
        if date and not self._is_valid_date(date):
            issues.append(ValidationIssue(
                entity_type=EntityType.EVENT,
                field="date",
                message=f"Invalid date format: {date}",
                severity=ValidationSeverity.WARNING
            ))
            suggestions.append("Use ISO 8601 format (YYYY-MM-DD)")
        
        confidence = self._calculate_confidence(issues)
        return ValidationResult(
            is_valid=len([i for i in issues if i.severity == ValidationSeverity.ERROR]) == 0,
            confidence_score=confidence,
            issues=issues,
            suggestions=suggestions
        )
    
    def _is_valid_date(self, date: str) -> bool:
        """Check if date is in valid format."""
        # Simple ISO 8601 date check
        date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}')
        return bool(date_pattern.match(str(date)))
    
    def _calculate_confidence(self, issues: List[ValidationIssue]) -> float:
        """Calculate confidence score based on issues."""
        if not issues:
            return 1.0
        
        confidence = 1.0
        for issue in issues:
            if issue.severity == ValidationSeverity.ERROR:
                confidence -= 0.3
            elif issue.severity == ValidationSeverity.WARNING:
                confidence -= 0.15
        
        return max(0.0, confidence)


class TaskValidator:
    """Validator for task entities."""
    
    def validate(self, entity: Dict[str, Any], context: Optional[str] = None) -> ValidationResult:
        """Validate a task entity."""
        issues = []
        suggestions = []
        
        title = entity.get("title", "").strip()
        if not title:
            issues.append(ValidationIssue(
                entity_type=EntityType.TASK,
                field="title",
                message="Task title is required",
                severity=ValidationSeverity.ERROR
            ))
        
        # Check status validity
        status = entity.get("status", "")
        valid_statuses = ["pending", "in_progress", "completed", "cancelled"]
        if status and status.lower() not in valid_statuses:
            issues.append(ValidationIssue(
                entity_type=EntityType.TASK,
                field="status",
                message=f"Invalid status: {status}",
                severity=ValidationSeverity.INFO
            ))
            suggestions.append(f"Valid statuses: {', '.join(valid_statuses)}")
        
        # Check priority validity
        priority = entity.get("priority", "")
        valid_priorities = ["low", "medium", "high", "critical"]
        if priority and priority.lower() not in valid_priorities:
            issues.append(ValidationIssue(
                entity_type=EntityType.TASK,
                field="priority",
                message=f"Invalid priority: {priority}",
                severity=ValidationSeverity.INFO
            ))
        
        confidence = self._calculate_confidence(issues)
        return ValidationResult(
            is_valid=len([i for i in issues if i.severity == ValidationSeverity.ERROR]) == 0,
            confidence_score=confidence,
            issues=issues,
            suggestions=suggestions
        )
    
    def _calculate_confidence(self, issues: List[ValidationIssue]) -> float:
        """Calculate confidence score based on issues."""
        if not issues:
            return 1.0
        
        confidence = 1.0
        for issue in issues:
            if issue.severity == ValidationSeverity.ERROR:
                confidence -= 0.3
            elif issue.severity == ValidationSeverity.WARNING:
                confidence -= 0.15
            elif issue.severity == ValidationSeverity.INFO:
                confidence -= 0.05
        
        return max(0.0, confidence)


class TransgressionValidator:
    """Validator for transgression entities."""
    
    def validate(self, entity: Dict[str, Any], context: Optional[str] = None) -> ValidationResult:
        """Validate a transgression entity."""
        issues = []
        suggestions = []
        
        description = entity.get("description", "").strip()
        if not description:
            issues.append(ValidationIssue(
                entity_type=EntityType.TRANSGRESSION,
                field="description",
                message="Transgression description is required",
                severity=ValidationSeverity.ERROR
            ))
        
        # Check severity validity
        severity = entity.get("severity", "")
        valid_severities = ["low", "medium", "high", "critical"]
        if severity and severity.lower() not in valid_severities:
            issues.append(ValidationIssue(
                entity_type=EntityType.TRANSGRESSION,
                field="severity",
                message=f"Invalid severity: {severity}",
                severity=ValidationSeverity.WARNING
            ))
            suggestions.append(f"Valid severities: {', '.join(valid_severities)}")
        
        confidence = self._calculate_confidence(issues)
        return ValidationResult(
            is_valid=len([i for i in issues if i.severity == ValidationSeverity.ERROR]) == 0,
            confidence_score=confidence,
            issues=issues,
            suggestions=suggestions
        )
    
    def _calculate_confidence(self, issues: List[ValidationIssue]) -> float:
        """Calculate confidence score based on issues."""
        if not issues:
            return 1.0
        
        confidence = 1.0
        for issue in issues:
            if issue.severity == ValidationSeverity.ERROR:
                confidence -= 0.3
            elif issue.severity == ValidationSeverity.WARNING:
                confidence -= 0.15
        
        return max(0.0, confidence)


class ExtractionAccuracyAnalyzer:
    """Analyze the accuracy of entity extraction against ground truth."""
    
    def __init__(self):
        self.semantic_validator = SemanticValidator()
    
    def analyze_extraction(self, 
                         extracted_entities: List[Dict[str, Any]],
                         ground_truth: List[Dict[str, Any]],
                         context: str) -> Dict[str, Any]:
        """Analyze extraction accuracy against ground truth."""
        results = {
            "precision": 0.0,
            "recall": 0.0,
            "f1_score": 0.0,
            "semantic_accuracy": 0.0,
            "missing_entities": [],
            "extra_entities": [],
            "validation_issues": [],
            "confidence_scores": []
        }
        
        # Match entities between extracted and ground truth
        matched_pairs = self._match_entities(extracted_entities, ground_truth)
        
        # Calculate metrics
        true_positives = len(matched_pairs)
        false_positives = len(extracted_entities) - true_positives
        false_negatives = len(ground_truth) - true_positives
        
        if extracted_entities:
            results["precision"] = true_positives / len(extracted_entities)
        
        if ground_truth:
            results["recall"] = true_positives / len(ground_truth)
        
        if results["precision"] + results["recall"] > 0:
            results["f1_score"] = 2 * (results["precision"] * results["recall"]) / (
                results["precision"] + results["recall"]
            )
        
        # Semantic validation of extracted entities
        total_confidence = 0.0
        for entity in extracted_entities:
            entity_type = EntityType(entity.get("type", "person"))
            validation_result = self.semantic_validator.validate_entity(
                entity, entity_type, context
            )
            results["validation_issues"].extend(validation_result.issues)
            results["confidence_scores"].append(validation_result.confidence_score)
            total_confidence += validation_result.confidence_score
        
        if extracted_entities:
            results["semantic_accuracy"] = total_confidence / len(extracted_entities)
        
        # Find missing and extra entities
        extracted_ids = {e.get("id") for e in extracted_entities}
        truth_ids = {e.get("id") for e in ground_truth}
        
        for entity in ground_truth:
            if entity.get("id") not in extracted_ids:
                results["missing_entities"].append(entity)
        
        for entity in extracted_entities:
            if entity.get("id") not in truth_ids:
                results["extra_entities"].append(entity)
        
        return results
    
    def _match_entities(self, extracted: List[Dict], ground_truth: List[Dict]) -> List[Tuple[Dict, Dict]]:
        """Match extracted entities with ground truth entities."""
        matches = []
        used_truth = set()
        
        for ext_entity in extracted:
            best_match = None
            best_score = 0.0
            
            for i, truth_entity in enumerate(ground_truth):
                if i in used_truth:
                    continue
                
                score = self._calculate_similarity(ext_entity, truth_entity)
                if score > best_score and score > 0.7:  # 70% similarity threshold
                    best_score = score
                    best_match = (ext_entity, truth_entity, i)
            
            if best_match:
                matches.append((best_match[0], best_match[1]))
                used_truth.add(best_match[2])
        
        return matches
    
    def _calculate_similarity(self, entity1: Dict, entity2: Dict) -> float:
        """Calculate similarity between two entities."""
        # Simple similarity based on name and type
        if entity1.get("type") != entity2.get("type"):
            return 0.0
        
        name1 = entity1.get("name", "").lower()
        name2 = entity2.get("name", "").lower()
        
        if name1 == name2:
            return 1.0
        elif name1 in name2 or name2 in name1:
            return 0.8
        else:
            # Calculate Jaccard similarity
            words1 = set(name1.split())
            words2 = set(name2.split())
            if not words1 or not words2:
                return 0.0
            
            intersection = words1 & words2
            union = words1 | words2
            return len(intersection) / len(union)