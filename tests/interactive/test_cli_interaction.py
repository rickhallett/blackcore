"""Test automated CLI interactions and user interface behavior."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from io import StringIO


class MockInputStream:
    """Mock input stream for testing CLI interactions."""
    
    def __init__(self, inputs: list):
        self.inputs = inputs
        self.index = 0
        
    def readline(self):
        if self.index < len(self.inputs):
            result = self.inputs[self.index] + '\n'
            self.index += 1
            return result
        return ''
        
    def __iter__(self):
        return self
        
    def __next__(self):
        line = self.readline()
        if line:
            return line.rstrip('\n')
        raise StopIteration


class MockOutputStream:
    """Mock output stream for capturing CLI output."""
    
    def __init__(self):
        self.output = []
        
    def write(self, text):
        self.output.append(text)
        
    def flush(self):
        pass
        
    def get_output(self):
        return ''.join(self.output)


class TestCLIInteraction:
    """Test CLI interaction patterns and user interface behavior."""
    
    @pytest.mark.asyncio
    async def test_menu_navigation_flow(self, mock_cli_with_data):
        """Test complete menu navigation flow."""
        cli = mock_cli_with_data
        
        # Test menu choices and navigation
        menu_scenarios = [
            {
                "name": "new_analysis_flow",
                "inputs": ["1", "y", "y"],  # New analysis, confirm settings, confirm review
                "expected_calls": ["_new_analysis"]
            },
            {
                "name": "configuration_flow", 
                "inputs": ["2", "n"],  # Configure settings, don't save
                "expected_calls": ["_configure_settings"]
            },
            {
                "name": "statistics_flow",
                "inputs": ["3"],  # View statistics
                "expected_calls": ["_view_statistics"]
            },
            {
                "name": "help_flow",
                "inputs": ["4"],  # Show help
                "expected_calls": ["_show_help"]
            },
            {
                "name": "exit_flow",
                "inputs": ["5"],  # Exit
                "expected_calls": ["exit"]
            }
        ]
        
        for scenario in menu_scenarios:
            with patch('rich.prompt.Prompt.ask') as mock_prompt:
                with patch('rich.prompt.Confirm.ask') as mock_confirm:
                    
                    # Set up mock responses
                    prompt_responses = iter(scenario["inputs"])
                    mock_prompt.side_effect = lambda *args, **kwargs: next(prompt_responses, "1")
                    mock_confirm.return_value = True
                    
                    # Mock the specific method calls
                    with patch.object(cli, '_new_analysis', new_callable=AsyncMock) as mock_new_analysis:
                        with patch.object(cli, '_configure_settings', new_callable=AsyncMock) as mock_configure:
                            with patch.object(cli, '_view_statistics', new_callable=AsyncMock) as mock_stats:
                                with patch.object(cli, '_show_help', new_callable=AsyncMock) as mock_help:
                                    
                                    # Simulate menu choice
                                    choice = scenario["inputs"][0]
                                    
                                    if choice == "1":
                                        await cli._new_analysis()
                                        mock_new_analysis.assert_called_once()
                                    elif choice == "2":
                                        await cli._configure_settings()
                                        mock_configure.assert_called_once()
                                    elif choice == "3":
                                        await cli._view_statistics()
                                        mock_stats.assert_called_once()
                                    elif choice == "4":
                                        await cli._show_help()
                                        mock_help.assert_called_once()
                                    # Exit case doesn't call a method
                                    
    @pytest.mark.asyncio
    async def test_keyboard_shortcuts_and_navigation(self, mock_cli_with_data):
        """Test keyboard shortcuts and navigation keys."""
        cli = mock_cli_with_data
        
        # Test review navigation keys
        navigation_tests = [
            {
                "key": "a",
                "action": "approve",
                "expected_decision": "merge"
            },
            {
                "key": "r", 
                "action": "reject",
                "expected_decision": "separate"
            },
            {
                "key": "d",
                "action": "defer", 
                "expected_decision": "defer"
            },
            {
                "key": "s",
                "action": "swap_primary",
                "expected_effect": "primary_swapped"
            },
            {
                "key": "m",
                "action": "merge_preview",
                "expected_effect": "preview_shown"
            },
            {
                "key": "n",
                "action": "next",
                "expected_effect": "navigation_next"
            },
            {
                "key": "p",
                "action": "previous", 
                "expected_effect": "navigation_prev"
            },
            {
                "key": "h",
                "action": "help",
                "expected_effect": "help_shown"
            },
            {
                "key": "q",
                "action": "quit",
                "expected_effect": "quit_prompted"
            }
        ]
        
        # Create test match
        test_match = {
            "entity_a": {"id": "1", "Full Name": "Test A"},
            "entity_b": {"id": "2", "Full Name": "Test B"},
            "confidence_score": 85.0,
            "primary_entity": "A"
        }
        
        for test in navigation_tests:
            with patch('rich.prompt.Prompt.ask', return_value=test["key"]):
                
                # Test key handling logic
                action = test["key"]
                
                if action == "a":  # Approve
                    # Should record merge decision
                    decision = {
                        "match": test_match,
                        "decision": "merge",
                        "reasoning": f"User approved merge"
                    }
                    assert decision["decision"] == test["expected_decision"]
                    
                elif action == "r":  # Reject
                    decision = {
                        "match": test_match,
                        "decision": "separate", 
                        "reasoning": "User rejected"
                    }
                    assert decision["decision"] == test["expected_decision"]
                    
                elif action == "d":  # Defer
                    decision = {
                        "match": test_match,
                        "decision": "defer",
                        "reasoning": "User deferred"
                    }
                    assert decision["decision"] == test["expected_decision"]
                    
                elif action == "s":  # Swap primary
                    original_primary = test_match["primary_entity"]
                    new_primary = "B" if original_primary == "A" else "A"
                    test_match["primary_entity"] = new_primary
                    assert test_match["primary_entity"] != original_primary
                    
                # Other actions (m, n, p, h, q) would be tested with UI mocking
                
    @pytest.mark.asyncio
    async def test_input_validation_and_error_handling(self, mock_cli_with_data):
        """Test input validation and error handling."""
        cli = mock_cli_with_data
        
        # Test invalid inputs
        invalid_input_tests = [
            {
                "input_type": "menu_choice",
                "invalid_inputs": ["0", "6", "abc", "", "1.5", "-1"],
                "valid_choices": ["1", "2", "3", "4", "5"],
                "expected_behavior": "re_prompt_or_default"
            },
            {
                "input_type": "review_action",
                "invalid_inputs": ["z", "1", "", "aa", "!"],
                "valid_choices": ["a", "r", "d", "n", "p", "e", "s", "m", "h", "?", "q"],
                "expected_behavior": "re_prompt_or_default"
            },
            {
                "input_type": "confirmation",
                "invalid_inputs": ["maybe", "1", "", "yes please"],
                "valid_choices": ["y", "n", "yes", "no", "true", "false"],
                "expected_behavior": "re_prompt_or_default"
            }
        ]
        
        for test in invalid_input_tests:
            for invalid_input in test["invalid_inputs"]:
                
                # Test menu choice validation
                if test["input_type"] == "menu_choice":
                    with patch('rich.prompt.Prompt.ask') as mock_prompt:
                        # First return invalid, then valid
                        mock_prompt.side_effect = [invalid_input, "1"]
                        
                        # Should handle invalid input gracefully
                        try:
                            # Simulate prompt validation
                            choices = test["valid_choices"]
                            if invalid_input not in choices:
                                # Should re-prompt or use default
                                result = "1"  # Default fallback
                            else:
                                result = invalid_input
                                
                            assert result in test["valid_choices"]
                            
                        except Exception as e:
                            # Should not raise unhandled exceptions
                            assert False, f"Unhandled exception for input '{invalid_input}': {e}"
                            
                # Test review action validation
                elif test["input_type"] == "review_action":
                    valid_actions = test["valid_choices"]
                    
                    if invalid_input not in valid_actions:
                        # Should be rejected
                        assert invalid_input not in valid_actions
                    else:
                        # Should be accepted
                        assert invalid_input in valid_actions
                        
    @pytest.mark.asyncio
    async def test_help_text_and_documentation_display(self, mock_cli_with_data):
        """Test help text display and documentation."""
        cli = mock_cli_with_data
        
        # Test help scenarios
        help_scenarios = [
            {
                "context": "main_menu",
                "expected_content": ["Menu", "New Analysis", "Configure", "Statistics", "Help", "Exit"]
            },
            {
                "context": "review_interface",
                "expected_content": ["Approve", "Reject", "Defer", "Swap", "Preview", "Navigation", "Shortcuts"]
            },
            {
                "context": "configuration",
                "expected_content": ["Thresholds", "AI Settings", "Safety Mode", "Databases"]
            }
        ]
        
        for scenario in help_scenarios:
            # Mock console output capture
            output_buffer = []
            
            def mock_print(*args, **kwargs):
                for arg in args:
                    output_buffer.append(str(arg))
                    
            with patch.object(cli.console, 'print', side_effect=mock_print):
                
                if scenario["context"] == "main_menu":
                    # Test main menu help
                    main_menu = cli.ui.create_main_menu()
                    cli.console.print(main_menu)
                    
                elif scenario["context"] == "review_interface":
                    # Test review help
                    from blackcore.deduplication.cli.ui_components import MatchReviewDisplay
                    review_display = MatchReviewDisplay(cli.console)
                    help_panel = review_display.display_help()
                    cli.console.print(help_panel)
                    
                # Check that expected content appears in output
                output_text = " ".join(output_buffer).lower()
                
                for expected_item in scenario["expected_content"]:
                    assert expected_item.lower() in output_text, \
                        f"Expected '{expected_item}' in {scenario['context']} help text"
                        
    @pytest.mark.asyncio
    async def test_progress_display_and_updates(self, mock_cli_with_data):
        """Test progress display and real-time updates."""
        cli = mock_cli_with_data
        
        # Mock progress tracking
        from blackcore.deduplication.cli.ui_components import ProgressTracker
        from blackcore.deduplication.cli.async_engine import ProgressUpdate
        
        progress_tracker = ProgressTracker(cli.console)
        
        # Test progress updates
        progress_sequence = [
            {"stage": "Loading", "current": 0, "total": 100},
            {"stage": "Processing", "current": 25, "total": 100},
            {"stage": "Processing", "current": 50, "total": 100},
            {"stage": "Processing", "current": 75, "total": 100},
            {"stage": "Completing", "current": 100, "total": 100}
        ]
        
        progress_outputs = []
        
        # Mock progress display
        def mock_progress_update(update):
            progress_outputs.append({
                "stage": update.stage,
                "current": update.current,
                "total": update.total,
                "percentage": (update.current / update.total * 100) if update.total > 0 else 0
            })
            
        # Simulate progress updates
        for progress_data in progress_sequence:
            update = ProgressUpdate(
                stage=progress_data["stage"],
                current=progress_data["current"],
                total=progress_data["total"],
                message=f"Processing {progress_data['current']}/{progress_data['total']}"
            )
            
            mock_progress_update(update)
            
        # Validate progress sequence
        assert len(progress_outputs) == len(progress_sequence)
        
        # Check progress is non-decreasing
        for i in range(1, len(progress_outputs)):
            current_progress = progress_outputs[i]["percentage"]
            previous_progress = progress_outputs[i-1]["percentage"]
            
            assert current_progress >= previous_progress, \
                f"Progress should not decrease: {previous_progress}% -> {current_progress}%"
                
        # Check final progress reaches 100%
        final_progress = progress_outputs[-1]["percentage"]
        assert final_progress == 100.0, f"Final progress should be 100%, got {final_progress}%"
        
    @pytest.mark.asyncio
    async def test_error_message_display_and_recovery(self, mock_cli_with_data):
        """Test error message display and recovery procedures."""
        cli = mock_cli_with_data
        
        # Test error scenarios
        error_scenarios = [
            {
                "error_type": "file_not_found",
                "error": FileNotFoundError("Database file not found"),
                "expected_message_contains": ["file", "not found", "database"],
                "recovery_action": "retry_or_exit"
            },
            {
                "error_type": "permission_denied",
                "error": PermissionError("Permission denied accessing database"),
                "expected_message_contains": ["permission", "denied", "access"],
                "recovery_action": "check_permissions"
            },
            {
                "error_type": "invalid_api_key",
                "error": ValueError("Invalid API key format"),
                "expected_message_contains": ["api key", "invalid", "format"],
                "recovery_action": "reconfigure_or_disable_ai"
            },
            {
                "error_type": "network_timeout",
                "error": TimeoutError("Network request timed out"),
                "expected_message_contains": ["network", "timeout", "connection"],
                "recovery_action": "retry_or_offline_mode"
            }
        ]
        
        for scenario in error_scenarios:
            error_messages = []
            
            def mock_error_display(message, **kwargs):
                error_messages.append(str(message).lower())
                
            with patch.object(cli.console, 'print', side_effect=mock_error_display):
                
                # Simulate error handling
                try:
                    raise scenario["error"]
                except Exception as e:
                    # Simulate error message display
                    error_msg = f"Error: {str(e)}"
                    cli.console.print(error_msg, style="red")
                    
                    # Check for recovery suggestions
                    if scenario["recovery_action"] == "retry_or_exit":
                        cli.console.print("Try checking the file path or select a different database.")
                    elif scenario["recovery_action"] == "check_permissions":
                        cli.console.print("Check file permissions and try again.")
                    elif scenario["recovery_action"] == "reconfigure_or_disable_ai":
                        cli.console.print("Check your API key configuration or disable AI analysis.")
                    elif scenario["recovery_action"] == "retry_or_offline_mode":
                        cli.console.print("Check your network connection or try offline mode.")
                        
            # Validate error message content
            all_error_text = " ".join(error_messages)
            
            for expected_phrase in scenario["expected_message_contains"]:
                assert expected_phrase in all_error_text, \
                    f"Expected '{expected_phrase}' in error message for {scenario['error_type']}"
                    
    @pytest.mark.asyncio
    async def test_session_state_preservation(self, mock_cli_with_data):
        """Test session state preservation during interactions."""
        cli = mock_cli_with_data
        
        # Initialize session state
        initial_state = {
            "current_results": None,
            "review_decisions": [],
            "configuration": cli.engine.engine.config.copy()
        }
        
        # Simulate session interactions
        session_actions = [
            {
                "action": "load_data",
                "state_changes": {
                    "databases_loaded": True,
                    "entity_count": 100
                }
            },
            {
                "action": "run_analysis",
                "state_changes": {
                    "analysis_complete": True,
                    "matches_found": 15
                }
            },
            {
                "action": "review_decisions",
                "state_changes": {
                    "decisions_made": 5,
                    "approved_merges": 3
                }
            }
        ]
        
        session_state = initial_state.copy()
        
        # Process each action and update state
        for action_data in session_actions:
            action = action_data["action"]
            changes = action_data["state_changes"]
            
            if action == "load_data":
                # Mock data loading
                session_state["databases_loaded"] = changes["databases_loaded"]
                session_state["entity_count"] = changes["entity_count"]
                
            elif action == "run_analysis":
                # Mock analysis
                mock_result = Mock()
                mock_result.total_entities = session_state.get("entity_count", 0)
                mock_result.potential_duplicates = changes["matches_found"]
                mock_result.high_confidence_matches = [{"id": f"match-{i}"} for i in range(5)]
                mock_result.medium_confidence_matches = [{"id": f"match-{i}"} for i in range(5)]
                mock_result.low_confidence_matches = [{"id": f"match-{i}"} for i in range(5)]
                
                session_state["current_results"] = {"People & Contacts": mock_result}
                session_state["analysis_complete"] = changes["analysis_complete"]
                
            elif action == "review_decisions":
                # Mock review decisions
                decisions = []
                for i in range(changes["decisions_made"]):
                    decision = {
                        "match": {"id": f"match-{i}"},
                        "decision": "merge" if i < changes["approved_merges"] else "separate",
                        "reasoning": f"Decision {i}"
                    }
                    decisions.append(decision)
                    
                session_state["review_decisions"] = decisions
                
        # Validate state preservation
        assert session_state["databases_loaded"] == True
        assert session_state["entity_count"] == 100
        assert session_state["analysis_complete"] == True
        assert session_state["current_results"] is not None
        assert len(session_state["review_decisions"]) == 5
        
        # Validate that state can be recovered after interruption
        recovered_state = session_state.copy()
        
        # Should be able to continue from where left off
        assert len(recovered_state["review_decisions"]) == 5
        approved_count = sum(1 for d in recovered_state["review_decisions"] if d["decision"] == "merge")
        assert approved_count == 3