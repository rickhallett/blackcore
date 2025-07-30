"""Workflow-specific test fixtures and utilities."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from typing import Dict, List, Any

import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from blackcore.deduplication import DeduplicationEngine
from blackcore.deduplication.cli.standard_mode import StandardModeCLI
from blackcore.deduplication.cli.async_engine import AsyncDeduplicationEngine
from blackcore.deduplication.merge_proposals import MergeExecutor


class MockConsole:
    """Mock Rich Console for testing CLI output."""

    def __init__(self):
        self.output = []
        self.inputs = []
        self.input_index = 0

    def print(self, *args, **kwargs):
        """Capture print output."""
        self.output.append({"args": args, "kwargs": kwargs})

    def clear(self):
        """Mock clear screen."""
        self.output.append({"action": "clear"})

    def set_inputs(self, inputs: List[str]):
        """Set predetermined inputs for testing."""
        self.inputs = inputs
        self.input_index = 0

    def get_input(self):
        """Get next predetermined input."""
        if self.input_index < len(self.inputs):
            result = self.inputs[self.input_index]
            self.input_index += 1
            return result
        return ""

    def get_output_text(self) -> str:
        """Get all output as text."""
        result = []
        for item in self.output:
            if "args" in item:
                for arg in item["args"]:
                    result.append(str(arg))
        return "\n".join(result)


class MockCLIRunner:
    """Mock CLI runner for testing user workflows."""

    def __init__(self):
        self.mock_console = MockConsole()
        self.user_inputs = []
        self.decisions = []

    async def run_workflow(self, cli_instance, user_actions: List[Dict[str, Any]]):
        """Run a complete workflow with predetermined user actions."""
        results = []

        for action in user_actions:
            action_type = action.get("type")

            if action_type == "menu_choice":
                # Simulate menu selection
                choice = action.get("value")
                result = await self._simulate_menu_choice(cli_instance, choice)
                results.append(
                    {"action": "menu_choice", "choice": choice, "result": result}
                )

            elif action_type == "config_setting":
                # Simulate configuration setting
                setting = action.get("setting")
                value = action.get("value")
                result = await self._simulate_config_setting(
                    cli_instance, setting, value
                )
                results.append(
                    {
                        "action": "config_setting",
                        "setting": setting,
                        "value": value,
                        "result": result,
                    }
                )

            elif action_type == "review_decision":
                # Simulate review decision
                decision = action.get("decision")  # 'a', 'r', 'd', 's', 'm', etc.
                result = await self._simulate_review_decision(cli_instance, decision)
                results.append(
                    {
                        "action": "review_decision",
                        "decision": decision,
                        "result": result,
                    }
                )

            elif action_type == "confirm":
                # Simulate yes/no confirmation
                confirm = action.get("value")
                result = await self._simulate_confirmation(cli_instance, confirm)
                results.append(
                    {"action": "confirm", "value": confirm, "result": result}
                )

        return results

    async def _simulate_menu_choice(self, cli_instance, choice: str):
        """Simulate menu choice selection."""
        with patch("rich.prompt.Prompt.ask", return_value=choice):
            if choice == "1":
                return await cli_instance._new_analysis()
            elif choice == "2":
                return await cli_instance._configure_settings()
            elif choice == "3":
                return await cli_instance._view_statistics()
            elif choice == "4":
                return await cli_instance._show_help()
            elif choice == "5":
                return "exit"

    async def _simulate_config_setting(self, cli_instance, setting: str, value: Any):
        """Simulate configuration setting."""
        if hasattr(cli_instance, "config_wizard"):
            if setting == "ai_enabled":
                cli_instance.config_wizard.config = (
                    cli_instance.config_wizard.config or {}
                )
                cli_instance.config_wizard.config["enable_ai_analysis"] = value
            elif setting == "databases":
                cli_instance.config_wizard.config = (
                    cli_instance.config_wizard.config or {}
                )
                cli_instance.config_wizard.config["databases"] = value
        return {"setting": setting, "value": value}

    async def _simulate_review_decision(self, cli_instance, decision: str):
        """Simulate review decision."""
        self.decisions.append(decision)
        return {"decision": decision, "timestamp": "mock_time"}

    async def _simulate_confirmation(self, cli_instance, confirm: bool):
        """Simulate yes/no confirmation."""
        with patch("rich.prompt.Confirm.ask", return_value=confirm):
            return confirm


@pytest.fixture
def mock_console():
    """Provide a mock console for testing."""
    return MockConsole()


@pytest.fixture
def cli_runner():
    """Provide a CLI runner for testing workflows."""
    return MockCLIRunner()


@pytest.fixture
def sample_people_data():
    """Provide sample people data with known duplicates."""
    return [
        {
            "id": "person-1",
            "Full Name": "John Smith",
            "Email": "john.smith@example.com",
            "Phone": "555-0123",
            "Organization": "Acme Corp",
        },
        {
            "id": "person-2",
            "Full Name": "John Smith",  # Exact duplicate
            "Email": "john.smith@example.com",
            "Phone": "555-0123",
            "Organization": "Acme Corp",
        },
        {
            "id": "person-3",
            "Full Name": "John Doe",
            "Email": "john.doe@example.com",
            "Phone": "555-0456",
            "Organization": "Beta Inc",
        },
        {
            "id": "person-4",
            "Full Name": "Jon Smith",  # Similar to John Smith
            "Email": "j.smith@acme.com",
            "Phone": "555-0123",
            "Organization": "Acme Corp",
        },
        {
            "id": "person-5",
            "Full Name": "Jane Doe",
            "Email": "jane.doe@example.com",
            "Phone": "555-0789",
            "Organization": "Gamma LLC",
        },
        {
            "id": "person-6",
            "Full Name": "Tony Powell",
            "Email": ["tony.powell@example.com", "tpowell@org.com"],  # List value
            "Phone": "555-1111",
            "Organization": ["ABC Org", "XYZ Corp"],  # List value
        },
        {
            "id": "person-7",
            "Full Name": "Tony Powell",  # Similar with some differences
            "Email": "tony.powell@example.com",
            "Phone": "555-1111",
            "Organization": "ABC Org",
            "Title": "Director",
        },
    ]


@pytest.fixture
def expected_duplicates():
    """Expected duplicate matches for sample_people_data."""
    return {
        "high_confidence": [
            # Exact duplicates
            {"entity_a_id": "person-1", "entity_b_id": "person-2", "confidence": 100.0},
        ],
        "medium_confidence": [
            # Similar with high confidence
            {"entity_a_id": "person-6", "entity_b_id": "person-7", "confidence": 85.0},
        ],
        "low_confidence": [
            # Name similarity but different details
            {"entity_a_id": "person-1", "entity_b_id": "person-4", "confidence": 65.0},
        ],
    }


@pytest.fixture
def mock_deduplication_engine():
    """Mock deduplication engine with predictable results."""
    engine = Mock(spec=DeduplicationEngine)

    # Mock configuration
    engine.config = {
        "auto_merge_threshold": 90.0,
        "human_review_threshold": 70.0,
        "enable_ai_analysis": False,
        "safety_mode": True,
    }

    return engine


@pytest.fixture
def mock_async_engine():
    """Mock async deduplication engine."""
    engine = Mock(spec=AsyncDeduplicationEngine)
    engine.engine = Mock()
    engine.engine.config = {
        "auto_merge_threshold": 90.0,
        "human_review_threshold": 70.0,
        "enable_ai_analysis": False,
        "safety_mode": True,
    }
    return engine


@pytest.fixture
def mock_merge_executor():
    """Mock merge executor with predictable results."""
    executor = Mock(spec=MergeExecutor)

    def mock_create_proposal(*args, **kwargs):
        proposal = Mock()
        proposal.proposal_id = "test-proposal-123"
        proposal.safety_checks = []
        proposal.risk_factors = []
        proposal.merge_strategy = "conservative"
        return proposal

    def mock_execute_merge(proposal, auto_approved=False):
        result = Mock()
        result.success = True
        result.merged_entity = {
            "id": "merged-entity",
            "Full Name": "Merged Entity",
            "_merge_info": {
                "merged_from": ["entity-a", "entity-b"],
                "merge_confidence": 95.0,
                "merge_strategy": "conservative",
            },
        }
        result.errors = []
        return result

    executor.create_proposal.side_effect = mock_create_proposal
    executor.execute_merge.side_effect = mock_execute_merge

    return executor


@pytest.fixture
def workflow_test_data():
    """Complete test data for workflow testing."""
    return {
        "people_data": [
            {
                "id": "test-1",
                "Full Name": "David Hollister",
                "Email": "david@example.com",
                "Organization": "Test Org",
            },
            {
                "id": "test-2",
                "Full Name": "David Hollister",  # Exact match
                "Email": "david@example.com",
                "Organization": "Test Org",
            },
            {
                "id": "test-3",
                "Full Name": "Dave Hollister",  # Similar match
                "Email": "dave@example.com",
                "Organization": "Test Org",
            },
        ],
        "expected_results": {
            "total_entities": 3,
            "potential_duplicates": 2,
            "high_confidence_matches": 1,
            "medium_confidence_matches": 1,
            "low_confidence_matches": 0,
        },
    }


class WorkflowValidator:
    """Validates workflow consistency and correctness."""

    @staticmethod
    def validate_summary_consistency(
        summary_counts: Dict[str, int], actual_matches: Dict[str, List]
    ) -> List[str]:
        """Validate that summary counts match actual match data."""
        errors = []

        # Check high confidence matches
        if summary_counts.get("high_confidence", 0) != len(
            actual_matches.get("high_confidence", [])
        ):
            errors.append(
                f"High confidence count mismatch: summary={summary_counts.get('high_confidence', 0)}, "
                f"actual={len(actual_matches.get('high_confidence', []))}"
            )

        # Check medium confidence matches
        if summary_counts.get("medium_confidence", 0) != len(
            actual_matches.get("medium_confidence", [])
        ):
            errors.append(
                f"Medium confidence count mismatch: summary={summary_counts.get('medium_confidence', 0)}, "
                f"actual={len(actual_matches.get('medium_confidence', []))}"
            )

        # Check low confidence matches
        if summary_counts.get("low_confidence", 0) != len(
            actual_matches.get("low_confidence", [])
        ):
            errors.append(
                f"Low confidence count mismatch: summary={summary_counts.get('low_confidence', 0)}, "
                f"actual={len(actual_matches.get('low_confidence', []))}"
            )

        return errors

    @staticmethod
    def validate_review_availability(
        summary_counts: Dict[str, int], matches_for_review: List
    ) -> List[str]:
        """Validate that all matches shown in summary are available for review."""
        errors = []

        total_expected = (
            summary_counts.get("high_confidence", 0)
            + summary_counts.get("medium_confidence", 0)
            + summary_counts.get("low_confidence", 0)
        )

        actual_review_count = len(matches_for_review)

        if total_expected != actual_review_count:
            errors.append(
                f"Review availability mismatch: expected {total_expected} matches for review, "
                f"but only {actual_review_count} available"
            )

        return errors


@pytest.fixture
def workflow_validator():
    """Provide workflow validator for testing."""
    return WorkflowValidator()


@pytest.fixture
async def mock_cli_with_data(sample_people_data, mock_async_engine):
    """Provide a CLI instance with mock data loaded."""
    cli = StandardModeCLI()
    cli.engine = mock_async_engine

    # Mock the database loading to return our sample data
    async def mock_load_databases():
        return {"People & Contacts": sample_people_data}

    cli._load_databases = mock_load_databases

    return cli
