"""Tests for text pipeline validation."""

import pytest
from datetime import datetime

from blackcore.minimal.property_validation import (
    ValidationLevel,
    ValidationError,
    ValidationErrorType,
    ValidationResult
)
from blackcore.minimal.text_pipeline_validator import (
    TextPipelineValidator,
    TransformationContext,
    TransformationStep,
    PipelineValidationResult,
    TransformationValidator,
    create_pipeline_validation_rules
)
from blackcore.minimal.data_transformer import DataTransformer
from blackcore.minimal.models import ExtractedEntities, Entity, EntityType


class TestTransformationContext:
    """Test TransformationContext class."""
    
    def test_context_creation(self):
        """Test creating transformation context."""
        context = TransformationContext(
            step=TransformationStep.PRE_EXTRACTION,
            source_type="transcript",
            target_type="entity",
            database_name="People & Contacts",
            field_name="Full Name",
            metadata={"key": "value"}
        )
        
        assert context.step == TransformationStep.PRE_EXTRACTION
        assert context.source_type == "transcript"
        assert context.target_type == "entity"
        assert context.database_name == "People & Contacts"
        assert context.field_name == "Full Name"
        assert context.metadata["key"] == "value"


class TestPipelineValidationResult:
    """Test PipelineValidationResult class."""
    
    def test_result_creation(self):
        """Test creating pipeline validation result."""
        result = PipelineValidationResult(is_valid=True)
        assert result.is_valid
        assert len(result.validation_results) == 0
        assert len(result.transformation_history) == 0
    
    def test_add_step_result(self):
        """Test adding step results."""
        result = PipelineValidationResult(is_valid=True)
        
        step_result = ValidationResult(is_valid=True)
        result.add_step_result(TransformationStep.PRE_EXTRACTION, step_result)
        
        assert TransformationStep.PRE_EXTRACTION in result.validation_results
        assert result.is_valid
        
        # Add failed result
        failed_result = ValidationResult(is_valid=False)
        failed_result.add_error(ValidationError(
            error_type=ValidationErrorType.TYPE_ERROR,
            field_name="test",
            message="Error"
        ))
        result.add_step_result(TransformationStep.POST_EXTRACTION, failed_result)
        
        assert not result.is_valid
    
    def test_add_transformation(self):
        """Test recording transformations."""
        result = PipelineValidationResult(is_valid=True)
        
        # Mock logger.time()
        import blackcore.minimal.text_pipeline_validator as module
        module.logger.time = lambda: "2025-01-15T10:00:00"
        
        result.add_transformation(
            TransformationStep.POST_TRANSFORM,
            "original value",
            "transformed value"
        )
        
        assert len(result.transformation_history) == 1
        history = result.transformation_history[0]
        assert history["step"] == "post_transform"
        assert history["original"] == "original value"
        assert history["transformed"] == "transformed value"


class TestTextPipelineValidator:
    """Test TextPipelineValidator class."""
    
    def test_validator_creation(self):
        """Test creating pipeline validator."""
        validator = TextPipelineValidator(ValidationLevel.STANDARD)
        assert validator.validation_level == ValidationLevel.STANDARD
        assert len(validator.validators_cache) == 0
        assert all(len(rules) == 0 for rules in validator.transformation_rules.values())
    
    def test_add_transformation_rule(self):
        """Test adding custom transformation rules."""
        validator = TextPipelineValidator()
        
        def custom_rule(value, context):
            result = ValidationResult(is_valid=True)
            if value == "invalid":
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.BUSINESS_RULE_ERROR,
                    field_name=context.field_name or "unknown",
                    message="Custom rule failed"
                ))
            return result
        
        validator.add_transformation_rule(TransformationStep.PRE_EXTRACTION, custom_rule)
        
        assert len(validator.transformation_rules[TransformationStep.PRE_EXTRACTION]) == 1
    
    def test_validate_step(self):
        """Test step validation."""
        validator = TextPipelineValidator()
        
        context = TransformationContext(
            step=TransformationStep.PRE_EXTRACTION,
            source_type="transcript",
            target_type="entity"
        )
        
        # Valid value
        result = validator.validate_step("valid text", TransformationStep.PRE_EXTRACTION, context)
        assert result.is_valid
        
        # Add custom rule and test again
        def length_rule(value, context):
            result = ValidationResult(is_valid=True)
            if isinstance(value, str) and len(value) < 5:
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.LENGTH_ERROR,
                    field_name="text",
                    message="Text too short"
                ))
            return result
        
        validator.add_transformation_rule(TransformationStep.PRE_EXTRACTION, length_rule)
        
        result = validator.validate_step("hi", TransformationStep.PRE_EXTRACTION, context)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.LENGTH_ERROR for e in result.errors)
    
    def test_validate_transformation_chain(self):
        """Test validating transformation chains."""
        validator = TextPipelineValidator()
        
        context = TransformationContext(
            step=TransformationStep.PRE_TRANSFORM,
            source_type="json",
            target_type="notion_property",
            field_name="text_field"
        )
        
        # Simple transformation chain
        transformations = [
            lambda x: x.upper(),
            lambda x: x.strip(),
            lambda x: x[:10]  # Truncate
        ]
        
        result = validator.validate_transformation_chain(
            "  hello world  ",
            context,
            transformations
        )
        
        assert result.is_valid
        assert result.final_value == "HELLO WORL"
        assert len(result.transformation_history) == 3
    
    def test_validate_transformation_chain_with_error(self):
        """Test transformation chain with errors."""
        validator = TextPipelineValidator(ValidationLevel.STRICT)
        
        context = TransformationContext(
            step=TransformationStep.PRE_TRANSFORM,
            source_type="json",
            target_type="notion_property",
            field_name="number_field"
        )
        
        # Transformation that will fail
        def bad_transform(x):
            raise ValueError("Transform failed")
        
        transformations = [
            lambda x: int(x),
            bad_transform,
            lambda x: x * 2
        ]
        
        result = validator.validate_transformation_chain(
            "42",
            context,
            transformations
        )
        
        assert not result.is_valid
        assert result.final_value == 42  # Stopped at first successful transform
        assert any(e.error_type == ValidationErrorType.BUSINESS_RULE_ERROR for e in result.validation_results[TransformationStep.POST_TRANSFORM].errors)
    
    def test_step_specific_validation(self):
        """Test built-in step-specific validation."""
        validator = TextPipelineValidator()
        
        # Test PRE_EXTRACTION validation
        context = TransformationContext(
            step=TransformationStep.PRE_EXTRACTION,
            source_type="transcript",
            target_type="entity"
        )
        
        # Too short transcript
        result = validator._apply_step_validation(
            "Hi",
            TransformationStep.PRE_EXTRACTION,
            context
        )
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.LENGTH_ERROR for e in result.errors)
        
        # Transcript with encoding errors
        result = validator._apply_step_validation(
            "Hello \ufffd World with enough content",
            TransformationStep.PRE_EXTRACTION,
            context
        )
        assert result.is_valid  # Warning only
        assert len(result.warnings) > 0
        
        # Test POST_EXTRACTION validation
        context.step = TransformationStep.POST_EXTRACTION
        
        # Mock extracted entities
        class MockExtracted:
            entities = []
        
        extracted = MockExtracted()
        result = validator._apply_step_validation(
            extracted,
            TransformationStep.POST_EXTRACTION,
            context
        )
        assert result.is_valid  # Warning only for no entities
        assert len(result.warnings) > 0
        
        # Test PRE_NOTION validation
        context.step = TransformationStep.PRE_NOTION
        
        # Invalid Notion payload
        result = validator._apply_step_validation(
            {"invalid": "payload"},
            TransformationStep.PRE_NOTION,
            context
        )
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.SCHEMA_ERROR for e in result.errors)
        
        # Valid Notion payload
        result = validator._apply_step_validation(
            {"properties": {"Name": {"title": [{"text": {"content": "Test"}}]}}},
            TransformationStep.PRE_NOTION,
            context
        )
        assert result.is_valid
    
    def test_validate_text_transformation(self):
        """Test text transformation validation."""
        validator = TextPipelineValidator()
        
        # Test truncation
        result = validator.validate_text_transformation(
            "This is a very long text that will be truncated",
            "This is a very long text th",
            "truncate"
        )
        assert result.is_valid
        assert len(result.warnings) > 0  # Should warn about missing ellipsis
        
        result = validator.validate_text_transformation(
            "This is a very long text that will be truncated",
            "This is a very long text th...",
            "truncate"
        )
        assert result.is_valid
        assert len(result.warnings) == 0
        
        # Test sanitization
        original = "Hello\x00World\x01\x02\x03"
        sanitized = "HelloWorld"
        result = validator.validate_text_transformation(
            original,
            sanitized,
            "sanitize"
        )
        assert result.is_valid
        assert len(result.warnings) > 0  # Should warn about removed characters
        
        # Test URL normalization
        result = validator.validate_text_transformation(
            "example.com",
            "https://example.com",
            "url_normalize"
        )
        assert result.is_valid
        
        # Test date parsing
        result = validator.validate_text_transformation(
            "January 15, 2025",
            "2025-01-15",
            "date_parse"
        )
        assert result.is_valid


class TestTransformationValidator:
    """Test TransformationValidator class."""
    
    def test_validator_creation(self):
        """Test creating transformation validator."""
        # Mock data transformer
        property_mappings = {
            "Test Database": {
                "transformations": {
                    "Test Field": {"type": "text", "max_length": 100}
                }
            }
        }
        
        transformer = DataTransformer(property_mappings, {})
        validator = TransformationValidator(transformer, ValidationLevel.STANDARD)
        
        assert validator.data_transformer == transformer
        assert validator.validation_level == ValidationLevel.STANDARD
        assert validator.pipeline_validator.validation_level == ValidationLevel.STANDARD
    
    def test_validate_transform_value(self):
        """Test validating transformation values."""
        property_mappings = {
            "Test Database": {
                "transformations": {
                    "Date Field": {"type": "date"},
                    "URL Field": {"type": "url"},
                    "Select Field": {"type": "select", "default": "Option1"}
                }
            }
        }
        
        transformer = DataTransformer(property_mappings, {})
        validator = TransformationValidator(transformer, ValidationLevel.STANDARD)
        
        # Test date transformation
        result = validator.validate_transform_value(
            "2025-01-15",
            "date",
            {},
            "Test Database",
            "Date Field"
        )
        assert result.is_valid
        
        # Test URL transformation
        result = validator.validate_transform_value(
            "https://example.com",
            "url",
            {},
            "Test Database",
            "URL Field"
        )
        assert result.is_valid
        
        # Test invalid transformation
        result = validator.validate_transform_value(
            "not a date",
            "date",
            {},
            "Test Database",
            "Date Field"
        )
        # The actual transformation might fail, but pre-validation should pass
        # since "not a date" is a valid string


class TestPipelineValidationRules:
    """Test standard pipeline validation rules."""
    
    def test_create_pipeline_validation_rules(self):
        """Test creating standard validation rules."""
        rules = create_pipeline_validation_rules(ValidationLevel.STANDARD)
        
        assert TransformationStep.PRE_EXTRACTION in rules
        assert TransformationStep.POST_EXTRACTION in rules
        assert TransformationStep.PRE_NOTION in rules
        
        assert len(rules[TransformationStep.PRE_EXTRACTION]) >= 1
        assert len(rules[TransformationStep.POST_EXTRACTION]) >= 1
        assert len(rules[TransformationStep.PRE_NOTION]) >= 1
    
    def test_transcript_quality_rule(self):
        """Test transcript quality validation rule."""
        rules = create_pipeline_validation_rules()
        quality_rule = rules[TransformationStep.PRE_EXTRACTION][0]
        
        context = TransformationContext(
            step=TransformationStep.PRE_EXTRACTION,
            source_type="transcript",
            target_type="entity"
        )
        
        # Good transcript
        result = quality_rule("This is a good transcript with clear content.", context)
        assert result.is_valid
        
        # Garbled text
        result = quality_rule("What??? Is??? This??? Text???", context)
        assert result.is_valid  # Warning only
        assert len(result.warnings) > 0
        
        # Repetitive text
        result = quality_rule("test test test test test test test test test test test", context)
        assert result.is_valid  # Warning only
        assert len(result.warnings) > 0
    
    def test_entity_consistency_rule(self):
        """Test entity consistency validation rule."""
        rules = create_pipeline_validation_rules()
        consistency_rule = rules[TransformationStep.POST_EXTRACTION][0]
        
        context = TransformationContext(
            step=TransformationStep.POST_EXTRACTION,
            source_type="transcript",
            target_type="entity"
        )
        
        # Mock extracted entities
        class MockEntity:
            def __init__(self, name):
                self.name = name
        
        class MockExtracted:
            def __init__(self, entities):
                self.entities = entities
        
        # No duplicates
        extracted = MockExtracted([
            MockEntity("John Doe"),
            MockEntity("Jane Smith")
        ])
        result = consistency_rule(extracted, context)
        assert result.is_valid
        assert len(result.warnings) == 0
        
        # Case-different duplicates
        extracted = MockExtracted([
            MockEntity("John Doe"),
            MockEntity("john doe"),
            MockEntity("JOHN DOE")
        ])
        result = consistency_rule(extracted, context)
        assert result.is_valid  # Warning only
        assert len(result.warnings) >= 2
    
    def test_notion_payload_size_rule(self):
        """Test Notion payload size validation rule."""
        rules = create_pipeline_validation_rules()
        size_rule = rules[TransformationStep.PRE_NOTION][0]
        
        context = TransformationContext(
            step=TransformationStep.PRE_NOTION,
            source_type="json",
            target_type="api_request"
        )
        
        # Small payload
        small_payload = {"properties": {"Name": "Test"}}
        result = size_rule(small_payload, context)
        assert result.is_valid
        assert len(result.warnings) == 0
        
        # Large payload (simulate)
        large_payload = {"data": "x" * (2 * 1024 * 1024 + 1)}  # Over 2MB
        result = size_rule(large_payload, context)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.LENGTH_ERROR for e in result.errors)
        
        # Near limit payload
        near_limit_payload = {"data": "x" * int(1.6 * 1024 * 1024)}  # 1.6MB
        result = size_rule(near_limit_payload, context)
        assert result.is_valid
        assert len(result.warnings) > 0


class TestIntegration:
    """Integration tests for pipeline validation."""
    
    def test_full_pipeline_validation(self):
        """Test full pipeline validation flow."""
        # Set up validator with all rules
        validator = TextPipelineValidator(ValidationLevel.STANDARD)
        rules = create_pipeline_validation_rules(ValidationLevel.STANDARD)
        for step, step_rules in rules.items():
            for rule in step_rules:
                validator.add_transformation_rule(step, rule)
        
        # Test transcript processing flow
        transcript = "This is a test transcript with John Doe and Jane Smith discussing important matters."
        
        # Pre-extraction
        context = TransformationContext(
            step=TransformationStep.PRE_EXTRACTION,
            source_type="transcript",
            target_type="entity"
        )
        result = validator.validate_step(transcript, TransformationStep.PRE_EXTRACTION, context)
        assert result.is_valid
        
        # Mock extraction
        class MockEntity:
            def __init__(self, name, entity_type):
                self.name = name
                self.entity_type = entity_type
        
        class MockExtracted:
            def __init__(self, entities):
                self.entities = entities
        
        extracted = MockExtracted([
            MockEntity("John Doe", EntityType.PERSON),
            MockEntity("Jane Smith", EntityType.PERSON)
        ])
        
        # Post-extraction
        context.step = TransformationStep.POST_EXTRACTION
        result = validator.validate_step(extracted, TransformationStep.POST_EXTRACTION, context)
        assert result.is_valid
        
        # Pre-Notion
        notion_payload = {
            "properties": {
                "Name": {"title": [{"text": {"content": "John Doe"}}]},
                "Type": {"select": {"name": "Person"}}
            }
        }
        context.step = TransformationStep.PRE_NOTION
        result = validator.validate_step(notion_payload, TransformationStep.PRE_NOTION, context)
        assert result.is_valid
    
    def test_data_transformer_integration(self):
        """Test integration with DataTransformer."""
        property_mappings = {
            "Test Database": {
                "mappings": {
                    "name": "Name",
                    "date": "Date",
                    "url": "Website"
                },
                "transformations": {
                    "Name": {"type": "rich_text", "max_length": 100},
                    "Date": {"type": "date"},
                    "Website": {"type": "url"}
                }
            }
        }
        
        transformer = DataTransformer(property_mappings, {}, ValidationLevel.STANDARD)
        
        # Test successful transformation with validation
        value = transformer.transform_value(
            "Test Name",
            "rich_text",
            {"max_length": 100},
            "Test Database",
            "Name"
        )
        assert value == "Test Name"
        
        # Test date transformation with validation
        value = transformer.transform_value(
            "2025-01-15",
            "date",
            {},
            "Test Database",
            "Date"
        )
        assert value == "2025-01-15"
        
        # Test URL transformation with validation
        value = transformer.transform_value(
            "example.com",
            "url",
            {},
            "Test Database",
            "Website"
        )
        assert value == "https://example.com"