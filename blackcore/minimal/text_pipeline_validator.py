"""Text pipeline validation for transformation steps.

This module provides validation at each transformation step to ensure
data integrity throughout the text processing pipeline.
"""

from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime

from blackcore.minimal.property_validation import (
    PropertyValidatorFactory,
    ValidationLevel,
    ValidationResult,
    ValidationError,
    ValidationErrorType,
    PropertyValidator,
    validate_property_value
)

logger = logging.getLogger(__name__)


class TransformationStep(Enum):
    """Transformation pipeline steps."""
    PRE_EXTRACTION = "pre_extraction"      # Before AI entity extraction
    POST_EXTRACTION = "post_extraction"    # After AI entity extraction
    PRE_TRANSFORM = "pre_transform"        # Before data transformation
    POST_TRANSFORM = "post_transform"      # After data transformation
    PRE_NOTION = "pre_notion"             # Before sending to Notion
    POST_NOTION = "post_notion"           # After Notion response


@dataclass
class TransformationContext:
    """Context information for transformation validation."""
    step: TransformationStep
    source_type: str  # e.g., "json", "transcript", "api_response"
    target_type: str  # e.g., "entity", "notion_property", "api_request"
    database_name: Optional[str] = None
    field_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineValidationResult:
    """Result of pipeline validation with transformation history."""
    is_valid: bool
    validation_results: Dict[TransformationStep, ValidationResult] = field(default_factory=dict)
    transformation_history: List[Dict[str, Any]] = field(default_factory=list)
    final_value: Any = None
    
    def add_step_result(self, step: TransformationStep, result: ValidationResult):
        """Add validation result for a transformation step."""
        self.validation_results[step] = result
        if not result.is_valid:
            self.is_valid = False
    
    def add_transformation(self, step: TransformationStep, original: Any, transformed: Any):
        """Record a transformation for audit trail."""
        self.transformation_history.append({
            "step": step.value,
            "original": original,
            "transformed": transformed,
            "timestamp": datetime.utcnow().isoformat()
        })


class TextPipelineValidator:
    """Validates text transformations throughout the processing pipeline."""
    
    def __init__(self, 
                 validation_level: ValidationLevel = ValidationLevel.STANDARD,
                 property_mappings: Optional[Dict[str, Any]] = None):
        """Initialize pipeline validator.
        
        Args:
            validation_level: Default validation strictness
            property_mappings: Property mapping configuration
        """
        self.validation_level = validation_level
        self.property_mappings = property_mappings or {}
        self.validators_cache: Dict[str, PropertyValidator] = {}
        self.transformation_rules: Dict[TransformationStep, List[Callable]] = {
            step: [] for step in TransformationStep
        }
    
    def add_transformation_rule(self, 
                              step: TransformationStep, 
                              rule: Callable[[Any, TransformationContext], ValidationResult]):
        """Add a custom validation rule for a transformation step."""
        self.transformation_rules[step].append(rule)
    
    def validate_transformation_chain(self,
                                    value: Any,
                                    context: TransformationContext,
                                    transformations: List[Callable[[Any], Any]]) -> PipelineValidationResult:
        """Validate a chain of transformations.
        
        Args:
            value: Initial value
            context: Transformation context
            transformations: List of transformation functions
            
        Returns:
            PipelineValidationResult with complete validation history
        """
        result = PipelineValidationResult(is_valid=True)
        current_value = value
        
        # Validate initial value
        pre_result = self.validate_step(
            current_value, 
            TransformationStep.PRE_TRANSFORM,
            context
        )
        result.add_step_result(TransformationStep.PRE_TRANSFORM, pre_result)
        
        if not pre_result.is_valid and self.validation_level.value >= ValidationLevel.STRICT.value:
            result.final_value = current_value
            return result
        
        # Apply transformations with validation at each step
        for i, transform in enumerate(transformations):
            try:
                # Apply transformation
                transformed_value = transform(current_value)
                result.add_transformation(
                    TransformationStep.POST_TRANSFORM,
                    current_value,
                    transformed_value
                )
                
                # Validate transformed value
                post_result = self.validate_step(
                    transformed_value,
                    TransformationStep.POST_TRANSFORM,
                    context
                )
                result.add_step_result(TransformationStep.POST_TRANSFORM, post_result)
                
                if not post_result.is_valid and self.validation_level.value >= ValidationLevel.STRICT.value:
                    logger.warning(
                        f"Transformation {i+1} failed validation: {post_result.errors}"
                    )
                    if self.validation_level == ValidationLevel.SECURITY:
                        # Reject transformation in security mode
                        result.final_value = current_value
                        return result
                
                current_value = transformed_value
                
            except Exception as e:
                error_result = ValidationResult(is_valid=False)
                error_result.add_error(ValidationError(
                    error_type=ValidationErrorType.BUSINESS_RULE_ERROR,
                    field_name=context.field_name or "unknown",
                    message=f"Transformation {i+1} failed: {str(e)}",
                    value=current_value,
                    context={"transform_index": i, "error": str(e)}
                ))
                result.add_step_result(TransformationStep.POST_TRANSFORM, error_result)
                result.final_value = current_value
                return result
        
        result.final_value = current_value
        return result
    
    def validate_step(self,
                     value: Any,
                     step: TransformationStep,
                     context: TransformationContext) -> ValidationResult:
        """Validate a value at a specific transformation step.
        
        Args:
            value: Value to validate
            step: Current transformation step
            context: Transformation context
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)
        
        # Apply step-specific validation rules
        for rule in self.transformation_rules[step]:
            rule_result = rule(value, context)
            result.merge(rule_result)
        
        # Apply property-specific validation if we have field info
        if context.field_name and context.database_name:
            prop_result = self._validate_property(value, context)
            result.merge(prop_result)
        
        # Apply step-specific built-in validations
        step_result = self._apply_step_validation(value, step, context)
        result.merge(step_result)
        
        return result
    
    def _validate_property(self, value: Any, context: TransformationContext) -> ValidationResult:
        """Validate value against property schema."""
        # Get property type from mappings
        db_config = self.property_mappings.get(context.database_name, {})
        transformations = db_config.get("transformations", {})
        transform_config = transformations.get(context.field_name, {})
        
        property_type = transform_config.get("type", "rich_text")
        
        # Get or create validator
        cache_key = f"{context.database_name}:{context.field_name}:{property_type}"
        if cache_key not in self.validators_cache:
            self.validators_cache[cache_key] = PropertyValidatorFactory.create_validator(
                property_type,
                context.field_name,
                transform_config,
                self.validation_level
            )
        
        validator = self.validators_cache[cache_key]
        return validator.validate(value)
    
    def _apply_step_validation(self, 
                             value: Any, 
                             step: TransformationStep,
                             context: TransformationContext) -> ValidationResult:
        """Apply built-in validation rules for each step."""
        result = ValidationResult(is_valid=True)
        
        if step == TransformationStep.PRE_EXTRACTION:
            # Validate raw transcript text
            if isinstance(value, str):
                # Check for minimum content
                if len(value.strip()) < 10:
                    result.add_error(ValidationError(
                        error_type=ValidationErrorType.LENGTH_ERROR,
                        field_name="transcript",
                        message="Transcript too short for meaningful extraction",
                        value=value
                    ))
                
                # Check for encoding issues
                if '\ufffd' in value:  # Unicode replacement character
                    result.add_warning(ValidationError(
                        error_type=ValidationErrorType.FORMAT_ERROR,
                        field_name="transcript",
                        message="Transcript contains encoding errors",
                        value=value
                    ))
        
        elif step == TransformationStep.POST_EXTRACTION:
            # Validate extracted entities
            if hasattr(value, 'entities'):
                entities = getattr(value, 'entities', [])
                if not entities:
                    result.add_warning(ValidationError(
                        error_type=ValidationErrorType.BUSINESS_RULE_ERROR,
                        field_name="entities",
                        message="No entities extracted from transcript",
                        value=value
                    ))
                
                # Validate entity structure
                for entity in entities:
                    if not hasattr(entity, 'name') or not entity.name:
                        result.add_error(ValidationError(
                            error_type=ValidationErrorType.REQUIRED_ERROR,
                            field_name="entity.name",
                            message="Entity missing required name field",
                            value=entity
                        ))
        
        elif step == TransformationStep.PRE_NOTION:
            # Validate Notion API payload structure
            if isinstance(value, dict):
                # Check for required Notion fields
                if 'properties' not in value and 'parent' not in value:
                    result.add_error(ValidationError(
                        error_type=ValidationErrorType.SCHEMA_ERROR,
                        field_name="notion_payload",
                        message="Notion payload missing required fields",
                        value=value
                    ))
                
                # Validate property structure
                properties = value.get('properties', {})
                for prop_name, prop_value in properties.items():
                    if not isinstance(prop_value, dict):
                        result.add_error(ValidationError(
                            error_type=ValidationErrorType.TYPE_ERROR,
                            field_name=f"properties.{prop_name}",
                            message="Property value must be a dictionary",
                            value=prop_value
                        ))
        
        return result
    
    def validate_text_transformation(self,
                                   original: str,
                                   transformed: str,
                                   transformation_type: str) -> ValidationResult:
        """Validate a text transformation.
        
        Args:
            original: Original text
            transformed: Transformed text
            transformation_type: Type of transformation applied
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)
        
        # Check for data loss
        if transformation_type == "truncate":
            if len(original) > len(transformed) and not transformed.endswith("..."):
                result.add_warning(ValidationError(
                    error_type=ValidationErrorType.FORMAT_ERROR,
                    field_name="text",
                    message="Truncated text should indicate truncation with ellipsis",
                    value=transformed,
                    context={"original_length": len(original), "truncated_length": len(transformed)}
                ))
        
        # Check for character encoding issues
        if transformation_type == "sanitize":
            # Count removed characters
            removed_chars = len(original) - len(transformed)
            if removed_chars > len(original) * 0.1:  # More than 10% removed
                result.add_warning(ValidationError(
                    error_type=ValidationErrorType.SECURITY_ERROR,
                    field_name="text",
                    message=f"Sanitization removed {removed_chars} characters ({removed_chars/len(original)*100:.1f}%)",
                    value=transformed,
                    context={"removed_count": removed_chars}
                ))
        
        # Validate URL transformations
        if transformation_type == "url_normalize":
            url_result = validate_property_value(
                "url", "url", transformed, validation_level=self.validation_level
            )
            result.merge(url_result)
        
        # Validate date transformations
        if transformation_type == "date_parse":
            date_result = validate_property_value(
                "date", "date", transformed, validation_level=self.validation_level
            )
            result.merge(date_result)
        
        return result


class TransformationValidator:
    """Validates individual transformations in the data transformer."""
    
    def __init__(self, 
                 data_transformer,
                 validation_level: ValidationLevel = ValidationLevel.STANDARD):
        """Initialize transformation validator.
        
        Args:
            data_transformer: DataTransformer instance to validate
            validation_level: Validation strictness level
        """
        self.data_transformer = data_transformer
        self.validation_level = validation_level
        self.pipeline_validator = TextPipelineValidator(
            validation_level=validation_level,
            property_mappings=data_transformer.property_mappings
        )
    
    def validate_transform_value(self,
                               value: Any,
                               transform_type: Optional[str],
                               config: Dict[str, Any],
                               database_name: str,
                               field_name: str) -> ValidationResult:
        """Validate a transformation operation.
        
        Args:
            value: Value to transform
            transform_type: Type of transformation
            config: Transformation configuration
            database_name: Database name
            field_name: Field name
            
        Returns:
            ValidationResult
        """
        context = TransformationContext(
            step=TransformationStep.PRE_TRANSFORM,
            source_type="json",
            target_type="notion_property",
            database_name=database_name,
            field_name=field_name,
            metadata=config
        )
        
        # Validate pre-transformation
        pre_result = self.pipeline_validator.validate_step(
            value, TransformationStep.PRE_TRANSFORM, context
        )
        
        if not pre_result.is_valid and self.validation_level.value >= ValidationLevel.STRICT.value:
            return pre_result
        
        # Perform transformation
        try:
            transformed = self.data_transformer.transform_value(
                value, transform_type, config, database_name, field_name
            )
        except Exception as e:
            result = ValidationResult(is_valid=False)
            result.add_error(ValidationError(
                error_type=ValidationErrorType.BUSINESS_RULE_ERROR,
                field_name=field_name,
                message=f"Transformation failed: {str(e)}",
                value=value,
                context={"transform_type": transform_type, "error": str(e)}
            ))
            return result
        
        # Validate post-transformation
        context.step = TransformationStep.POST_TRANSFORM
        post_result = self.pipeline_validator.validate_step(
            transformed, TransformationStep.POST_TRANSFORM, context
        )
        
        # Validate specific transformation
        if transform_type in ["date", "url", "select", "status", "rich_text"]:
            specific_result = self.pipeline_validator.validate_text_transformation(
                str(value), str(transformed), transform_type
            )
            post_result.merge(specific_result)
        
        return post_result


def create_pipeline_validation_rules(validation_level: ValidationLevel = ValidationLevel.STANDARD):
    """Create standard validation rules for text pipeline.
    
    Args:
        validation_level: Validation strictness level
        
    Returns:
        Dictionary of validation rules by transformation step
    """
    rules = {}
    
    # Pre-extraction rules
    def validate_transcript_quality(value: Any, context: TransformationContext) -> ValidationResult:
        """Validate transcript quality before extraction."""
        result = ValidationResult(is_valid=True)
        
        if isinstance(value, str):
            # Check for garbled text patterns
            if value.count('?') / len(value) > 0.1:  # More than 10% question marks
                result.add_warning(ValidationError(
                    error_type=ValidationErrorType.FORMAT_ERROR,
                    field_name="transcript",
                    message="Transcript may contain garbled text",
                    value=value[:100] + "..."
                ))
            
            # Check for repetitive patterns
            words = value.split()
            if len(words) > 10:
                unique_words = len(set(words))
                if unique_words / len(words) < 0.3:  # Less than 30% unique words
                    result.add_warning(ValidationError(
                        error_type=ValidationErrorType.FORMAT_ERROR,
                        field_name="transcript",
                        message="Transcript contains highly repetitive content",
                        value=value[:100] + "..."
                    ))
        
        return result
    
    # Post-extraction rules
    def validate_entity_consistency(value: Any, context: TransformationContext) -> ValidationResult:
        """Validate entity consistency after extraction."""
        result = ValidationResult(is_valid=True)
        
        if hasattr(value, 'entities'):
            entities = getattr(value, 'entities', [])
            names = [e.name for e in entities if hasattr(e, 'name')]
            
            # Check for near-duplicates
            for i, name1 in enumerate(names):
                for name2 in names[i+1:]:
                    if name1.lower() == name2.lower() and name1 != name2:
                        result.add_warning(ValidationError(
                            error_type=ValidationErrorType.BUSINESS_RULE_ERROR,
                            field_name="entities",
                            message=f"Possible duplicate entities with different casing: '{name1}' and '{name2}'",
                            value=value
                        ))
        
        return result
    
    # Pre-Notion rules
    def validate_notion_payload_size(value: Any, context: TransformationContext) -> ValidationResult:
        """Validate Notion API payload size constraints."""
        result = ValidationResult(is_valid=True)
        
        if isinstance(value, dict):
            # Estimate payload size
            import json
            payload_size = len(json.dumps(value))
            
            # Notion has a 2MB limit for API requests
            if payload_size > 2 * 1024 * 1024:
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.LENGTH_ERROR,
                    field_name="payload",
                    message=f"Payload size ({payload_size} bytes) exceeds Notion API limit",
                    value=value
                ))
            elif payload_size > 1.5 * 1024 * 1024:
                result.add_warning(ValidationError(
                    error_type=ValidationErrorType.LENGTH_ERROR,
                    field_name="payload",
                    message=f"Payload size ({payload_size} bytes) approaching Notion API limit",
                    value=value
                ))
        
        return result
    
    rules = {
        TransformationStep.PRE_EXTRACTION: [validate_transcript_quality],
        TransformationStep.POST_EXTRACTION: [validate_entity_consistency],
        TransformationStep.PRE_NOTION: [validate_notion_payload_size]
    }
    
    return rules