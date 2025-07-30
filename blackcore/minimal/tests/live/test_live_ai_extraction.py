"""Live AI entity extraction tests.

These tests make real API calls to AI providers to validate semantic accuracy
of entity extraction from actual transcript content using a structured test library.
"""

import pytest
from typing import List, Dict, Any

from blackcore.minimal.models import ExtractedEntities, Entity, EntityType
from blackcore.minimal.ai_extractor import AIExtractor
from .transcript_library import (
    TestTranscriptLibrary, 
    ExtractionResultValidator,
    TranscriptCategory
)


@pytest.fixture(scope="session")
def transcript_library() -> TestTranscriptLibrary:
    """Get the test transcript library."""
    return TestTranscriptLibrary()


@pytest.fixture
def result_validator() -> ExtractionResultValidator:
    """Get the extraction result validator."""
    return ExtractionResultValidator()


class TestLiveAIEntityExtraction:
    """Test live AI entity extraction with real API calls using structured test library."""
    
    def test_simple_meeting_transcript_ai_extraction(
        self, 
        live_ai_extractor: AIExtractor,
        transcript_library: TestTranscriptLibrary,
        result_validator: ExtractionResultValidator
    ):
        """Test AI extraction on a simple meeting transcript using structured validation."""
        # Get test transcript from library
        test_transcript = transcript_library.get_transcript("simple_meeting")
        assert test_transcript is not None, "Simple meeting transcript not found in library"
        
        # Extract entities using live AI
        result = live_ai_extractor.extract_entities(test_transcript.content)
        
        # Validate result structure
        assert isinstance(result, ExtractedEntities)
        assert len(result.entities) > 0
        
        # Validate against expected outcomes using structured validator
        validation_result = result_validator.validate_extraction(result, test_transcript.expected_outcome)
        
        # Print detailed validation results
        print(f"\n✅ {test_transcript.title} - Live AI Extraction Results:")
        print(f"   - Overall Score: {validation_result['overall_score']:.2f}")
        print(f"   - Entity Coverage: {validation_result['entity_coverage']:.2f} ({validation_result['required_entities_found']}/{validation_result['required_entities_total']})")
        print(f"   - Type Accuracy: {validation_result['type_accuracy']:.2f}")
        print(f"   - Name Accuracy: {validation_result['name_accuracy']:.2f}")
        print(f"   - Entity Count Valid: {validation_result['entity_count_valid']}")
        print(f"   - Required Types Found: {validation_result['required_types_found']}")
        if validation_result['required_types_missing']:
            print(f"   - Missing Types: {validation_result['required_types_missing']}")
        
        # Print detailed validation info
        for detail in validation_result['validation_details']:
            print(f"   {detail}")
        
        # Assert that the extraction passed validation
        assert validation_result['passed'], f"Extraction validation failed with score {validation_result['overall_score']:.2f}"
        
        # Additional assertions for critical requirements
        assert validation_result['entity_coverage'] >= 0.8, f"Entity coverage too low: {validation_result['entity_coverage']:.2f}"
        assert validation_result['type_accuracy'] >= 0.9, f"Type accuracy too low: {validation_result['type_accuracy']:.2f}"


    def test_security_incident_transcript_ai_extraction(
        self,
        live_ai_extractor: AIExtractor,
        transcript_library: TestTranscriptLibrary,
        result_validator: ExtractionResultValidator
    ):
        """Test AI extraction on a security incident transcript using structured validation."""
        # Get test transcript from library
        test_transcript = transcript_library.get_transcript("security_incident")
        assert test_transcript is not None, "Security incident transcript not found in library"
        
        # Extract entities using live AI  
        result = live_ai_extractor.extract_entities(test_transcript.content)
        
        # Validate result structure
        assert isinstance(result, ExtractedEntities)
        assert len(result.entities) > 0
        
        # Validate against expected outcomes using structured validator
        validation_result = result_validator.validate_extraction(result, test_transcript.expected_outcome)
        
        # Print detailed validation results
        print(f"\n✅ {test_transcript.title} - Live AI Extraction Results:")
        print(f"   - Overall Score: {validation_result['overall_score']:.2f}")
        print(f"   - Entity Coverage: {validation_result['entity_coverage']:.2f} ({validation_result['required_entities_found']}/{validation_result['required_entities_total']})")
        print(f"   - Type Accuracy: {validation_result['type_accuracy']:.2f}")
        print(f"   - Name Accuracy: {validation_result['name_accuracy']:.2f}")
        print(f"   - Entity Count Valid: {validation_result['entity_count_valid']}")
        print(f"   - Required Types Found: {validation_result['required_types_found']}")
        if validation_result['required_types_missing']:
            print(f"   - Missing Types: {validation_result['required_types_missing']}")
        
        # Print detailed validation info
        for detail in validation_result['validation_details']:
            print(f"   {detail}")
        
        # Assert that the extraction passed validation
        assert validation_result['passed'], f"Extraction validation failed with score {validation_result['overall_score']:.2f}"
        
        # Additional security-specific assertions
        assert validation_result['entity_coverage'] >= 0.7, f"Entity coverage too low for complex security incident: {validation_result['entity_coverage']:.2f}"
        
        # Ensure transgression was detected
        entity_types = {entity.type for entity in result.entities}
        assert EntityType.TRANSGRESSION in entity_types, "Security incident must include transgression entity"


    def test_complex_multi_organization_transcript(
        self,
        live_ai_extractor: AIExtractor,
        transcript_library: TestTranscriptLibrary,
        result_validator: ExtractionResultValidator
    ):
        """Test AI extraction on complex multi-organization content using structured validation."""
        # Get test transcript from library
        test_transcript = transcript_library.get_transcript("multi_org_partnership")
        assert test_transcript is not None, "Multi-org partnership transcript not found in library"
        
        # Extract entities using live AI
        result = live_ai_extractor.extract_entities(test_transcript.content)
        
        # Validate result structure
        assert isinstance(result, ExtractedEntities)
        assert len(result.entities) > 0
        
        # Validate against expected outcomes using structured validator
        validation_result = result_validator.validate_extraction(result, test_transcript.expected_outcome)
        
        # Print detailed validation results
        print(f"\n✅ {test_transcript.title} - Live AI Extraction Results:")
        print(f"   - Overall Score: {validation_result['overall_score']:.2f}")
        print(f"   - Entity Coverage: {validation_result['entity_coverage']:.2f} ({validation_result['required_entities_found']}/{validation_result['required_entities_total']})")
        print(f"   - Type Accuracy: {validation_result['type_accuracy']:.2f}")
        print(f"   - Name Accuracy: {validation_result['name_accuracy']:.2f}")
        print(f"   - Entity Count Valid: {validation_result['entity_count_valid']}")
        print(f"   - Required Types Found: {validation_result['required_types_found']}")
        if validation_result['required_types_missing']:
            print(f"   - Missing Types: {validation_result['required_types_missing']}")
        
        # Print detailed validation info
        for detail in validation_result['validation_details']:
            print(f"   {detail}")
        
        # Assert that the extraction passed validation
        assert validation_result['passed'], f"Extraction validation failed with score {validation_result['overall_score']:.2f}"
        
        # Additional assertions for complex multi-org scenarios
        assert validation_result['entity_coverage'] >= 0.75, f"Entity coverage too low for complex partnership: {validation_result['entity_coverage']:.2f}"
        
        # Ensure key entity types are present
        entity_types = {entity.type for entity in result.entities}
        required_types = {EntityType.ORGANIZATION, EntityType.PERSON, EntityType.PLACE}
        assert required_types.issubset(entity_types), f"Missing required types. Found: {entity_types}, Required: {required_types}"
        
        # Validate relationships were extracted
        assert len(result.relationships) > 0, "Expected relationships between entities for complex partnership"


    @pytest.mark.slow
    def test_ai_extraction_consistency(
        self,
        live_ai_extractor: AIExtractor,
        transcript_library: TestTranscriptLibrary,
        result_validator: ExtractionResultValidator
    ):
        """Test that AI extraction produces consistent results across multiple runs using structured validation."""
        # Get test transcript from library
        test_transcript = transcript_library.get_transcript("board_meeting")
        assert test_transcript is not None, "Board meeting transcript not found in library"
        
        # Run extraction multiple times to test consistency
        results = []
        validation_results = []
        
        for i in range(3):
            result = live_ai_extractor.extract_entities(test_transcript.content)
            validation_result = result_validator.validate_extraction(result, test_transcript.expected_outcome)
            results.append(result)
            validation_results.append(validation_result)
        
        # Analyze consistency across runs
        entity_counts = [len(r.entities) for r in results]
        overall_scores = [v['overall_score'] for v in validation_results]
        entity_coverages = [v['entity_coverage'] for v in validation_results]
        
        avg_count = sum(entity_counts) / len(entity_counts)
        avg_score = sum(overall_scores) / len(overall_scores)
        avg_coverage = sum(entity_coverages) / len(entity_coverages)
        
        # Validate consistency in entity counts
        for count in entity_counts:
            variation = abs(count - avg_count) / avg_count if avg_count > 0 else 0
            assert variation < 0.5, f"Entity count variation too high: {entity_counts}"
        
        # Validate consistency in validation scores
        for score in overall_scores:
            score_variation = abs(score - avg_score) / avg_score if avg_score > 0 else 0
            assert score_variation < 0.3, f"Score variation too high: {overall_scores}"
        
        # All runs should pass validation
        passed_count = sum(1 for v in validation_results if v['passed'])
        assert passed_count >= 2, f"Too many validation failures: {passed_count}/3 passed"
        
        # All results should consistently extract key required entities
        for i, result in enumerate(results):
            validation_result = validation_results[i]
            assert validation_result['entity_coverage'] >= 0.6, f"Run {i+1} entity coverage too low: {validation_result['entity_coverage']:.2f}"
        
        print(f"\n✅ {test_transcript.title} - AI Consistency Test Results:")
        print(f"   - Entity counts across runs: {entity_counts}")
        print(f"   - Average entities: {avg_count:.1f}")
        print(f"   - Max count variation: {max(entity_counts) - min(entity_counts)} entities")
        print(f"   - Overall scores: {[f'{s:.2f}' for s in overall_scores]}")
        print(f"   - Average score: {avg_score:.2f}")
        print(f"   - Entity coverage: {[f'{c:.2f}' for c in entity_coverages]}")
        print(f"   - Validation passed: {passed_count}/3 runs")


    @pytest.mark.parametrize("transcript_id", ["simple_meeting", "security_incident", "multi_org_partnership", "board_meeting"])
    def test_transcript_library_systematic_validation(
        self,
        transcript_id: str,
        live_ai_extractor: AIExtractor,
        transcript_library: TestTranscriptLibrary,
        result_validator: ExtractionResultValidator
    ):
        """Systematically test all transcripts in the library for comprehensive validation."""
        # Get test transcript from library
        test_transcript = transcript_library.get_transcript(transcript_id)
        assert test_transcript is not None, f"Transcript '{transcript_id}' not found in library"
        
        # Extract entities using live AI
        result = live_ai_extractor.extract_entities(test_transcript.content)
        
        # Validate result structure
        assert isinstance(result, ExtractedEntities)
        assert len(result.entities) > 0, f"No entities extracted for {transcript_id}"
        
        # Validate against expected outcomes using structured validator
        validation_result = result_validator.validate_extraction(result, test_transcript.expected_outcome)
        
        # Print concise validation results for batch testing
        print(f"\n📊 {test_transcript.title} ({transcript_id}):")
        print(f"   Score: {validation_result['overall_score']:.2f} | " +
              f"Coverage: {validation_result['entity_coverage']:.2f} | " +
              f"Type Acc: {validation_result['type_accuracy']:.2f} | " +
              f"Name Acc: {validation_result['name_accuracy']:.2f}")
        print(f"   Found: {validation_result['required_entities_found']}/{validation_result['required_entities_total']} | " +
              f"Types: {len(validation_result['required_types_found'])}/{len(test_transcript.expected_outcome.required_entity_types)} | " +
              f"{'✅ PASSED' if validation_result['passed'] else '❌ FAILED'}")
        
        # Assert that the extraction passed validation
        assert validation_result['passed'], f"Transcript '{transcript_id}' validation failed with score {validation_result['overall_score']:.2f}"
        
        # Category-specific validation
        if test_transcript.category == TranscriptCategory.SECURITY_INCIDENT:
            entity_types = {entity.type for entity in result.entities}
            assert EntityType.TRANSGRESSION in entity_types, f"Security incident must include transgression entity for {transcript_id}"
        
        elif test_transcript.category == TranscriptCategory.PARTNERSHIP:
            # Complex partnerships should have relationships
            assert len(result.relationships) > 0, f"Partnership transcript should have relationships for {transcript_id}"
            
        elif test_transcript.category == TranscriptCategory.MEETING:
            # Meeting transcripts should have people and tasks
            entity_types = {entity.type for entity in result.entities}
            assert EntityType.PERSON in entity_types, f"Meeting should have person entities for {transcript_id}"
            
        elif test_transcript.category == TranscriptCategory.BOARD_MEETING:
            # Board meetings should have decisions/tasks
            entity_types = {entity.type for entity in result.entities}
            assert EntityType.TASK in entity_types, f"Board meeting should have task entities for {transcript_id}"


    def test_transcript_library_comprehensive_report(
        self,
        live_ai_extractor: AIExtractor,
        transcript_library: TestTranscriptLibrary,
        result_validator: ExtractionResultValidator
    ):
        """Generate a comprehensive validation report across all transcript categories."""
        all_transcripts = transcript_library.get_all_transcripts()
        
        category_results = {}
        overall_results = []
        
        print(f"\n🔍 Comprehensive Transcript Library Validation")
        print(f"{'='*80}")
        
        for transcript in all_transcripts:
            # Extract entities
            result = live_ai_extractor.extract_entities(transcript.content)
            validation_result = result_validator.validate_extraction(result, transcript.expected_outcome)
            
            # Track by category
            category = transcript.category.value
            if category not in category_results:
                category_results[category] = []
            category_results[category].append(validation_result)
            overall_results.append(validation_result)
            
            print(f"{transcript.title:35} | Score: {validation_result['overall_score']:.2f} | " +
                  f"{'✅' if validation_result['passed'] else '❌'}")
        
        print(f"{'='*80}")
        
        # Category summaries
        for category, results in category_results.items():
            passed = sum(1 for r in results if r['passed'])
            avg_score = sum(r['overall_score'] for r in results) / len(results)
            avg_coverage = sum(r['entity_coverage'] for r in results) / len(results)
            
            print(f"{category.upper():20} | {passed}/{len(results)} passed | " +
                  f"Avg Score: {avg_score:.2f} | Avg Coverage: {avg_coverage:.2f}")
        
        # Overall summary
        total_passed = sum(1 for r in overall_results if r['passed'])
        overall_avg_score = sum(r['overall_score'] for r in overall_results) / len(overall_results)
        overall_avg_coverage = sum(r['entity_coverage'] for r in overall_results) / len(overall_results)
        
        print(f"{'='*80}")
        print(f"OVERALL SUMMARY      | {total_passed}/{len(overall_results)} passed | " +
              f"Avg Score: {overall_avg_score:.2f} | Avg Coverage: {overall_avg_coverage:.2f}")
        print(f"{'='*80}")
        
        # Assert overall quality thresholds
        assert total_passed >= len(overall_results) * 0.75, f"Too many transcript validations failed: {total_passed}/{len(overall_results)}"
        assert overall_avg_score >= 0.7, f"Overall average score too low: {overall_avg_score:.2f}"
        assert overall_avg_coverage >= 0.7, f"Overall average coverage too low: {overall_avg_coverage:.2f}"