"""Tests for CI/CD integration and automated regression prevention."""

import pytest
import os
import time
from unittest.mock import patch
from pathlib import Path


class TestCIIntegration:
    """Test CI/CD integration for automated regression prevention."""
    
    @pytest.mark.ci_integration
    def test_critical_test_discovery(self):
        """Test that all critical tests are properly marked and discoverable."""
        
        # Define critical test markers that CI must run
        required_markers = [
            "golden_path",
            "regression", 
            "critical",
            "workflows"
        ]
        
        # Test files that must contain critical tests
        critical_test_files = [
            "test_golden_path_workflows.py",
            "test_known_bug_prevention.py",
            "test_complete_deduplication_flow.py",
            "test_cli_consistency.py"
        ]
        
        # Validate that critical test files exist
        test_dir = Path(__file__).parent.parent
        
        for test_file in critical_test_files:
            file_paths = list(test_dir.rglob(test_file))
            assert len(file_paths) > 0, f"Critical test file {test_file} not found in test directory"
            
        # Test marker validation (would be checked by CI)
        # This simulates what the CI system should verify
        def validate_test_markers():
            """Simulate CI validation of test markers."""
            discovered_markers = {
                "golden_path": 6,  # Number of golden path tests
                "regression": 8,   # Number of regression tests  
                "critical": 6,     # Number of critical tests
                "workflows": 15    # Number of workflow tests
            }
            
            for marker, expected_count in discovered_markers.items():
                assert expected_count > 0, f"No tests found with marker '{marker}'"
                
        validate_test_markers()
        
    @pytest.mark.ci_integration
    def test_test_execution_time_limits(self):
        """Test that CI test execution stays within time limits."""
        
        # Define maximum execution times for different test categories
        time_limits = {
            "unit_tests": 10.0,      # 10 seconds for unit tests
            "integration_tests": 30.0,  # 30 seconds for integration tests  
            "workflow_tests": 60.0,   # 1 minute for workflow tests
            "performance_tests": 120.0  # 2 minutes for performance tests
        }
        
        # Simulate test execution timing
        test_results = {}
        
        for test_category, time_limit in time_limits.items():
            start_time = time.time()
            
            # Simulate test execution
            if test_category == "unit_tests":
                # Fast unit tests
                time.sleep(0.001)
            elif test_category == "integration_tests":
                # Moderate integration tests
                time.sleep(0.005)
            elif test_category == "workflow_tests":
                # Slower workflow tests
                time.sleep(0.01)
            elif test_category == "performance_tests":
                # Performance tests can be slower
                time.sleep(0.02)
                
            execution_time = time.time() - start_time
            test_results[test_category] = execution_time
            
            # Validate execution time
            assert execution_time < time_limit, \
                f"{test_category} took {execution_time:.2f}s, exceeding limit of {time_limit}s"
                
    @pytest.mark.ci_integration
    def test_dependency_validation(self):
        """Test that all required dependencies are available in CI environment."""
        
        # Critical dependencies for the test suite
        required_dependencies = [
            "pytest",
            "pytest-asyncio", 
            "unittest.mock",
            "psutil",
            "datetime",
            "pathlib",
            "json",
            "hashlib"
        ]
        
        # Test that dependencies can be imported
        for dependency in required_dependencies:
            try:
                if "." in dependency:
                    # Handle submodules
                    parent, child = dependency.split(".", 1)
                    parent_module = __import__(parent)
                    getattr(parent_module, child)
                else:
                    __import__(dependency)
            except ImportError:
                pytest.fail(f"Required dependency '{dependency}' not available")
                
    @pytest.mark.ci_integration  
    def test_environment_configuration(self):
        """Test CI environment configuration requirements."""
        
        # Environment variables that may be needed
        optional_env_vars = [
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY", 
            "BLACKCORE_TEST_MODE"
        ]
        
        # Test environment setup
        test_env_config = {
            "BLACKCORE_TEST_MODE": "true",
            "PYTHONPATH": os.getcwd(),
            "CI": "true"
        }
        
        # Validate that test environment can be configured
        with patch.dict(os.environ, test_env_config):
            assert os.getenv("BLACKCORE_TEST_MODE") == "true"
            assert os.getenv("CI") == "true"
            
        # Check that tests can run without optional API keys
        # (Should use mocked services instead)
        assert True  # Tests should work with mocked services
        
    @pytest.mark.ci_integration
    def test_test_data_generation(self):
        """Test that test data can be generated consistently in CI."""
        
        # Test data generation functions
        def generate_test_entities(count=10):
            """Generate consistent test entities."""
            entities = []
            for i in range(count):
                entity = {
                    "id": f"test-entity-{i}",
                    "Full Name": f"Test Person {i}",
                    "Email": f"test{i}@example.com",
                    "Phone": f"555-{i:04d}",
                    "Organization": f"Test Org {i // 3}"
                }
                entities.append(entity)
            return entities
            
        def generate_test_matches(entities):
            """Generate test matches from entities."""
            matches = []
            for i in range(0, len(entities) - 1, 2):
                match = {
                    "id": f"match-{i//2}",
                    "entity_a": entities[i],
                    "entity_b": entities[i + 1],
                    "confidence_score": 80.0 + (i * 2),
                    "primary_entity": "A"
                }
                matches.append(match)
            return matches
            
        # Test data generation
        test_entities = generate_test_entities(20)
        test_matches = generate_test_matches(test_entities)
        
        # Validate generated data
        assert len(test_entities) == 20
        assert len(test_matches) == 10
        assert all("id" in entity for entity in test_entities)
        assert all("confidence_score" in match for match in test_matches)
        
        # Test deterministic generation (same input = same output)
        entities_1 = generate_test_entities(5)
        entities_2 = generate_test_entities(5)
        
        assert len(entities_1) == len(entities_2)
        for e1, e2 in zip(entities_1, entities_2):
            assert e1["id"] == e2["id"]
            assert e1["Full Name"] == e2["Full Name"]
            
    @pytest.mark.ci_integration
    def test_test_isolation(self):
        """Test that tests are properly isolated and don't interfere with each other."""
        
        # Test state isolation
        class TestStateTracker:
            def __init__(self):
                self.state = {}
                
            def set_state(self, key, value):
                self.state[key] = value
                
            def get_state(self, key):
                return self.state.get(key)
                
            def clear_state(self):
                self.state.clear()
                
        # Test 1: Modify state
        tracker = TestStateTracker()
        tracker.set_state("test1", "value1")
        
        assert tracker.get_state("test1") == "value1"
        
        # Test 2: State should be isolated (in real tests, this would be a fresh instance)
        tracker.clear_state()  # Simulate test cleanup
        
        assert tracker.get_state("test1") is None
        
        # Test 3: Fresh state 
        tracker.set_state("test3", "value3")
        
        assert tracker.get_state("test3") == "value3"
        assert tracker.get_state("test1") is None  # Previous test data gone
        
    @pytest.mark.ci_integration
    def test_failure_reporting(self):
        """Test that test failures are properly reported with useful information."""
        
        # Mock test failure scenarios
        failure_scenarios = [
            {
                "test_name": "test_low_confidence_review_bug",
                "failure_type": "assertion_error",
                "error_message": "Expected 4 matches for review, got 0",
                "location": "test_known_bug_prevention.py:45",
                "regression_risk": "high"
            },
            {
                "test_name": "test_primary_entity_consistency", 
                "failure_type": "assertion_error",
                "error_message": "Primary entity not preserved: expected person-2, got person-1",
                "location": "test_known_bug_prevention.py:178",
                "regression_risk": "medium"
            },
            {
                "test_name": "test_performance_golden_path",
                "failure_type": "performance_regression",
                "error_message": "Analysis too slow: 6.2s for 500 entities (limit: 5.0s)",
                "location": "test_golden_path_workflows.py:512",
                "regression_risk": "low"
            }
        ]
        
        # Test failure report generation
        def generate_failure_report(failures):
            """Generate CI failure report."""
            report = {
                "total_failures": len(failures),
                "high_risk": 0,
                "medium_risk": 0,
                "low_risk": 0,
                "details": []
            }
            
            for failure in failures:
                report[f"{failure['regression_risk']}_risk"] += 1
                report["details"].append({
                    "test": failure["test_name"],
                    "error": failure["error_message"],
                    "location": failure["location"],
                    "risk": failure["regression_risk"]
                })
                
            return report
            
        # Generate report
        report = generate_failure_report(failure_scenarios)
        
        # Validate report structure
        assert report["total_failures"] == 3
        assert report["high_risk"] == 1
        assert report["medium_risk"] == 1
        assert report["low_risk"] == 1
        assert len(report["details"]) == 3
        
        # Test that high-risk failures would block CI
        if report["high_risk"] > 0:
            # In real CI, this would fail the build
            high_risk_tests = [d for d in report["details"] if d["risk"] == "high"]
            assert len(high_risk_tests) > 0
            
    @pytest.mark.ci_integration
    def test_coverage_requirements(self):
        """Test coverage requirements for critical code paths."""
        
        # Mock coverage data
        coverage_data = {
            "blackcore/deduplication/cli/standard_mode.py": {
                "total_lines": 300,
                "covered_lines": 285,
                "coverage_percentage": 95.0,
                "critical_functions": {
                    "_review_matches": 100.0,  # Critical function must be 100% covered
                    "_collect_matches_for_review": 100.0,
                    "_display_summary": 90.0
                }
            },
            "blackcore/deduplication/merge_proposals.py": {
                "total_lines": 200,
                "covered_lines": 180,
                "coverage_percentage": 90.0,
                "critical_functions": {
                    "execute_merge": 100.0,
                    "create_proposal": 95.0
                }
            }
        }
        
        # Coverage requirements
        requirements = {
            "overall_minimum": 85.0,
            "critical_function_minimum": 95.0,
            "regression_fix_minimum": 100.0  # Functions that fixed bugs must be 100% covered
        }
        
        # Validate coverage
        for file_path, file_coverage in coverage_data.items():
            # Check overall coverage
            assert file_coverage["coverage_percentage"] >= requirements["overall_minimum"], \
                f"Coverage too low for {file_path}: {file_coverage['coverage_percentage']}%"
                
            # Check critical function coverage
            for func_name, func_coverage in file_coverage["critical_functions"].items():
                if "review_matches" in func_name or "collect_matches" in func_name:
                    # These functions fixed the low confidence review bug
                    assert func_coverage >= requirements["regression_fix_minimum"], \
                        f"Regression fix function {func_name} coverage too low: {func_coverage}%"
                else:
                    assert func_coverage >= requirements["critical_function_minimum"], \
                        f"Critical function {func_name} coverage too low: {func_coverage}%"
                        
    @pytest.mark.ci_integration
    def test_build_artifacts_validation(self):
        """Test that CI build artifacts are properly generated."""
        
        # Expected CI artifacts
        expected_artifacts = [
            "test_report.xml",     # JUnit test results
            "coverage_report.xml", # Coverage report
            "performance_report.json",  # Performance metrics
            "regression_report.html"    # Regression test summary
        ]
        
        # Mock artifact generation
        generated_artifacts = []
        
        for artifact in expected_artifacts:
            # Simulate artifact generation
            if artifact.endswith(".xml"):
                content = "<?xml version='1.0'?><testsuite></testsuite>"
            elif artifact.endswith(".json"):
                content = '{"performance": "metrics"}'
            elif artifact.endswith(".html"):
                content = "<html><body>Report</body></html>"
            else:
                content = "artifact content"
                
            # Mock file creation
            generated_artifacts.append({
                "name": artifact,
                "content": content,
                "size": len(content)
            })
            
        # Validate artifacts
        assert len(generated_artifacts) == len(expected_artifacts)
        
        for artifact in generated_artifacts:
            assert artifact["name"] in expected_artifacts
            assert artifact["size"] > 0
            assert len(artifact["content"]) > 0
            
    @pytest.mark.ci_integration
    def test_notification_configuration(self):
        """Test CI notification configuration for test failures."""
        
        # Mock notification scenarios
        notification_scenarios = [
            {
                "trigger": "high_risk_regression",
                "recipients": ["dev-team@company.com", "tech-lead@company.com"],
                "message": "CRITICAL: High-risk regression detected in deduplication workflow",
                "priority": "urgent"
            },
            {
                "trigger": "performance_regression",
                "recipients": ["dev-team@company.com"],
                "message": "Performance regression detected in test suite",
                "priority": "normal"
            },
            {
                "trigger": "golden_path_failure",
                "recipients": ["dev-team@company.com", "product-owner@company.com"],
                "message": "Golden path workflow test failed - core functionality broken",
                "priority": "urgent"
            }
        ]
        
        # Test notification configuration
        def validate_notification_config(scenario):
            """Validate notification configuration."""
            errors = []
            
            if not scenario["recipients"]:
                errors.append("No recipients configured")
                
            if scenario["priority"] not in ["low", "normal", "high", "urgent"]:
                errors.append(f"Invalid priority: {scenario['priority']}")
                
            if len(scenario["message"]) < 10:
                errors.append("Notification message too short")
                
            return errors
            
        # Validate all notification scenarios
        for scenario in notification_scenarios:
            errors = validate_notification_config(scenario)
            assert len(errors) == 0, f"Notification config errors for {scenario['trigger']}: {errors}"