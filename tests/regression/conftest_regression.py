"""Fixtures and configuration for regression tests."""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from typing import Dict, List, Any


@pytest.fixture
def regression_test_data():
    """Comprehensive test data for regression testing."""
    return {
        "entities": [
            {
                "id": "person-1",
                "Full Name": "John Smith",
                "Email": "john@example.com",
                "Phone": "555-1234",
                "Organization": "Acme Corp",
                "Title": "Manager"
            },
            {
                "id": "person-2", 
                "Full Name": "John Smith",
                "Email": "j.smith@acme.com",
                "Phone": "555-1234",
                "Organization": ["Acme Corp", "Beta Inc"],
                "Department": "Sales"
            },
            {
                "id": "person-3",
                "Full Name": "Jane Doe",
                "Email": "jane@example.com",
                "Phone": "555-5678",
                "Organization": "Gamma LLC"
            },
            {
                "id": "person-4",
                "Full Name": "Jane Doe",
                "Email": "j.doe@gamma.com", 
                "Phone": "555-5678",
                "Organization": "Gamma LLC",
                "Title": "Director"
            }
        ],
        "known_duplicates": [
            {
                "primary": "person-1",
                "secondary": "person-2",
                "confidence": 95.0,
                "reason": "Same name, phone, and organization"
            },
            {
                "primary": "person-3",
                "secondary": "person-4", 
                "confidence": 90.0,
                "reason": "Same name, phone, and organization"
            }
        ]
    }


@pytest.fixture
def mock_historical_bug_scenarios():
    """Mock scenarios representing historical bugs that have been fixed."""
    return {
        "low_confidence_review_bug": {
            "description": "UI shows low confidence matches but excludes them from review",
            "scenario": {
                "high_confidence": [],
                "medium_confidence": [],
                "low_confidence": [
                    {"id": "low-1", "confidence": 65.0},
                    {"id": "low-2", "confidence": 68.0},
                    {"id": "low-3", "confidence": 62.0},
                    {"id": "low-4", "confidence": 69.0}
                ]
            },
            "expected_ui_summary": "4 matches of low confidence",
            "expected_review_count": 4,
            "bug_behavior": "nothing to review"
        },
        "primary_entity_inconsistency": {
            "description": "Primary entity selection not preserved through workflow",
            "scenario": {
                "match": {
                    "entity_a": {"id": "a1", "Full Name": "Test A"},
                    "entity_b": {"id": "b1", "Full Name": "Test B"},
                    "primary_entity": "A"
                },
                "user_action": "swap_to_B"
            },
            "expected_behavior": "B should remain primary through merge",
            "bug_behavior": "reverts to A during merge"
        },
        "threshold_boundary_bug": {
            "description": "Matches at exact threshold boundaries miscategorized",
            "scenario": {
                "auto_threshold": 90.0,
                "review_threshold": 70.0,
                "test_confidences": [90.0, 89.9, 70.0, 69.9]
            },
            "expected_categories": ["high", "medium", "medium", "low"],
            "bug_behavior": "inconsistent categorization at boundaries"
        }
    }


@pytest.fixture
def mock_regression_cli():
    """Mock CLI with comprehensive regression test configuration."""
    cli = Mock()
    cli.engine = Mock()
    cli.engine.engine = Mock()
    
    # Default safe configuration
    cli.engine.engine.config = {
        "enable_ai_analysis": False,  # Disabled for deterministic testing
        "auto_merge_threshold": 90.0,
        "human_review_threshold": 70.0,
        "safety_mode": True,
        "databases": ["People & Contacts"]
    }
    
    # Mock database loading
    async def mock_load_databases():
        return {
            "People & Contacts": [
                {"id": "1", "Full Name": "Person 1"},
                {"id": "2", "Full Name": "Person 2"}
            ]
        }
    
    cli._load_databases = mock_load_databases
    
    # Mock analysis with configurable results
    cli.engine.analyze_databases_async = AsyncMock()
    
    return cli


@pytest.fixture
def bug_reproduction_helpers():
    """Helper functions for reproducing specific bugs."""
    
    class BugReproductionHelpers:
        
        @staticmethod
        def reproduce_low_confidence_bug(db_result):
            """Reproduce the low confidence review bug."""
            # This simulates the OLD (buggy) behavior
            matches_to_review = []
            
            # Old code ONLY included medium confidence
            for match in db_result.medium_confidence_matches:
                match["database"] = "Test DB"
                matches_to_review.append(match)
                
            # BUG: Low confidence matches were NOT included
            # for match in db_result.low_confidence_matches:
            #     match["database"] = "Test DB"  
            #     matches_to_review.append(match)
            
            return matches_to_review
            
        @staticmethod
        def reproduce_primary_entity_bug(match, user_swaps_to_b=True):
            """Reproduce primary entity selection inconsistency."""
            original_primary = match["primary_entity"]
            
            if user_swaps_to_b:
                # User swaps to B
                match["primary_entity"] = "B"
                
            # BUG: System reverts to original during merge
            # This simulates the buggy behavior:
            merge_primary = original_primary  # Bug: ignores user selection
            
            return merge_primary
            
        @staticmethod
        def reproduce_threshold_boundary_bug(confidence, auto_threshold, review_threshold):
            """Reproduce threshold boundary categorization bug."""
            # BUG: Inconsistent boundary handling
            # Old buggy logic used inconsistent comparisons
            
            if confidence > auto_threshold:  # BUG: should be >=
                return "high"
            elif confidence > review_threshold:  # BUG: should be >=
                return "medium" 
            else:
                return "low"
                
        @staticmethod
        def correct_low_confidence_logic(db_result):
            """Demonstrate the FIXED behavior."""
            matches_to_review = []
            
            # Include medium confidence
            for match in db_result.medium_confidence_matches:
                match["database"] = "Test DB"
                matches_to_review.append(match)
                
            # FIX: Include low confidence matches for review
            for match in db_result.low_confidence_matches:
                match["database"] = "Test DB"
                matches_to_review.append(match)
                
            return matches_to_review
            
        @staticmethod
        def correct_primary_entity_logic(match):
            """Demonstrate the FIXED primary entity behavior."""
            # FIXED: Respect user's primary entity selection
            if match["primary_entity"] == "B":
                return match["entity_b"], match["entity_a"]
            else:
                return match["entity_a"], match["entity_b"]
                
        @staticmethod
        def correct_threshold_logic(confidence, auto_threshold, review_threshold):
            """Demonstrate the FIXED threshold logic."""
            # FIXED: Use >= for inclusive boundaries
            if confidence >= auto_threshold:
                return "high"
            elif confidence >= review_threshold:
                return "medium"
            else:
                return "low"
    
    return BugReproductionHelpers()


@pytest.fixture
def regression_validation_helpers():
    """Helper functions for validating regression fixes."""
    
    class RegressionValidationHelpers:
        
        @staticmethod
        def validate_ui_backend_consistency(ui_summary, backend_processing):
            """Validate that UI display matches backend processing."""
            errors = []
            
            # Check that counts match
            if ui_summary.get("low_confidence", 0) > 0:
                low_in_review = sum(1 for match in backend_processing.get("review_matches", [])
                                  if "low" in match.get("id", "").lower())
                if low_in_review != ui_summary["low_confidence"]:
                    errors.append(f"UI shows {ui_summary['low_confidence']} low confidence matches, but only {low_in_review} in review")
                    
            return errors
            
        @staticmethod
        def validate_primary_entity_preservation(original_match, final_merge_result):
            """Validate that primary entity selection is preserved."""
            errors = []
            
            expected_primary_id = (original_match["entity_b"]["id"] 
                                 if original_match["primary_entity"] == "B" 
                                 else original_match["entity_a"]["id"])
                                 
            if final_merge_result["id"] != expected_primary_id:
                errors.append(f"Primary entity not preserved: expected {expected_primary_id}, got {final_merge_result['id']}")
                
            return errors
            
        @staticmethod 
        def validate_threshold_consistency(matches, auto_threshold, review_threshold):
            """Validate consistent threshold application."""
            errors = []
            
            for match in matches:
                confidence = match["confidence"]
                category = match["category"]
                
                if confidence >= auto_threshold and category != "high":
                    errors.append(f"Match {match['id']} with confidence {confidence} should be high, got {category}")
                elif confidence >= review_threshold and confidence < auto_threshold and category != "medium":
                    errors.append(f"Match {match['id']} with confidence {confidence} should be medium, got {category}")
                elif confidence < review_threshold and category != "low":
                    errors.append(f"Match {match['id']} with confidence {confidence} should be low, got {category}")
                    
            return errors
            
        @staticmethod
        def validate_data_integrity(original_entities, final_entities, merge_metadata):
            """Validate that no data is lost during processing."""
            errors = []
            
            # Check that all original entity IDs are accounted for
            original_ids = {entity["id"] for entity in original_entities}
            final_ids = set()
            
            for entity in final_entities:
                if "_merge_info" in entity and "merged_from" in entity["_merge_info"]:
                    # This entity is a result of a merge
                    final_ids.update(entity["_merge_info"]["merged_from"])
                else:
                    final_ids.add(entity["id"])
                    
            missing_ids = original_ids - final_ids
            if missing_ids:
                errors.append(f"Lost entity IDs during processing: {missing_ids}")
                
            return errors
            
        @staticmethod
        def validate_performance_regression(current_metrics, baseline_metrics, tolerance=0.2):
            """Validate that performance hasn't regressed beyond tolerance."""
            errors = []
            
            for metric, current_value in current_metrics.items():
                if metric in baseline_metrics:
                    baseline_value = baseline_metrics[metric]
                    
                    if metric in ["processing_time", "memory_usage"]:
                        # Lower is better
                        max_allowed = baseline_value * (1 + tolerance)
                        if current_value > max_allowed:
                            regression_pct = ((current_value - baseline_value) / baseline_value) * 100
                            errors.append(f"Performance regression in {metric}: {regression_pct:.1f}% worse than baseline")
                    elif metric in ["entities_per_second", "throughput"]:
                        # Higher is better
                        min_allowed = baseline_value * (1 - tolerance)
                        if current_value < min_allowed:
                            regression_pct = ((baseline_value - current_value) / baseline_value) * 100
                            errors.append(f"Performance regression in {metric}: {regression_pct:.1f}% worse than baseline")
                            
            return errors
    
    return RegressionValidationHelpers()


@pytest.fixture
def mock_merge_executor():
    """Mock merge executor for regression testing."""
    executor = Mock()
    
    def mock_create_proposal(primary_entity, secondary_entity, **kwargs):
        proposal = Mock()
        proposal.proposal_id = f"proposal-{primary_entity['id']}-{secondary_entity['id']}"
        proposal.primary_entity = primary_entity
        proposal.secondary_entity = secondary_entity
        proposal.confidence_score = kwargs.get("confidence_score", 85.0)
        return proposal
        
    def mock_execute_merge(proposal, auto_approved=False):
        result = Mock()
        result.success = True
        result.proposal_id = proposal.proposal_id
        
        # Perform conservative merge
        merged = proposal.primary_entity.copy()
        
        # Fill missing fields from secondary
        for key, value in proposal.secondary_entity.items():
            if key not in merged or not merged[key]:
                merged[key] = value
                
        # Add merge metadata
        merged["_merge_info"] = {
            "merged_from": [proposal.primary_entity["id"], proposal.secondary_entity["id"]],
            "auto_approved": auto_approved,
            "timestamp": datetime.now().isoformat()
        }
        
        result.merged_entity = merged
        return result
        
    executor.create_proposal = mock_create_proposal
    executor.execute_merge = mock_execute_merge
    
    return executor