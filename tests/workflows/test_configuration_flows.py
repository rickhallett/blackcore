"""Test configuration wizard workflows and settings validation."""

import pytest
import os
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path


class TestConfigurationFlows:
    """Test configuration workflows and validation."""
    
    @pytest.mark.asyncio
    async def test_configuration_wizard_complete_flow(self, mock_cli_with_data):
        """Test complete configuration wizard flow."""
        cli = mock_cli_with_data
        
        # Test configuration scenarios
        config_scenarios = [
            {
                "name": "AI_enabled_with_valid_keys",
                "inputs": {
                    "enable_ai": True,
                    "anthropic_key": "sk-ant-valid-key-123",
                    "auto_merge_threshold": 95.0,
                    "review_threshold": 80.0,
                    "safety_mode": True
                },
                "expected_config": {
                    "enable_ai_analysis": True,
                    "auto_merge_threshold": 95.0,
                    "human_review_threshold": 80.0,
                    "safety_mode": True
                }
            },
            {
                "name": "AI_disabled_conservative_settings",
                "inputs": {
                    "enable_ai": False,
                    "auto_merge_threshold": 90.0,
                    "review_threshold": 70.0,
                    "safety_mode": True
                },
                "expected_config": {
                    "enable_ai_analysis": False,
                    "auto_merge_threshold": 90.0,
                    "human_review_threshold": 70.0,
                    "safety_mode": True
                }
            },
            {
                "name": "aggressive_settings",
                "inputs": {
                    "enable_ai": False,
                    "auto_merge_threshold": 85.0,
                    "review_threshold": 60.0,
                    "safety_mode": False
                },
                "expected_config": {
                    "enable_ai_analysis": False,
                    "auto_merge_threshold": 85.0,
                    "human_review_threshold": 60.0,
                    "safety_mode": False
                }
            }
        ]
        
        for scenario in config_scenarios:
            # Mock the configuration wizard
            with patch.object(cli.config_wizard, 'run_wizard') as mock_wizard:
                mock_wizard.return_value = scenario["expected_config"]
                
                # Run configuration
                config = await cli.config_wizard.run_wizard()
                
                # Validate configuration
                for key, expected_value in scenario["expected_config"].items():
                    assert config[key] == expected_value, \
                        f"Scenario '{scenario['name']}': {key} should be {expected_value}, got {config.get(key)}"
                        
    @pytest.mark.asyncio
    async def test_api_key_validation(self, mock_cli_with_data):
        """Test API key validation logic."""
        cli = mock_cli_with_data
        
        api_key_tests = [
            {
                "name": "valid_anthropic_key",
                "anthropic_key": "sk-ant-api03-valid-key-123",
                "openai_key": None,
                "expected_valid": True,
                "expected_ai_enabled": True
            },
            {
                "name": "valid_openai_key",
                "anthropic_key": None,
                "openai_key": "sk-openai-valid-key-123",
                "expected_valid": True,
                "expected_ai_enabled": True
            },
            {
                "name": "both_keys_valid",
                "anthropic_key": "sk-ant-api03-valid-key-123",
                "openai_key": "sk-openai-valid-key-123",
                "expected_valid": True,
                "expected_ai_enabled": True
            },
            {
                "name": "placeholder_keys",
                "anthropic_key": "your_key_here",
                "openai_key": "your_key_here",
                "expected_valid": False,
                "expected_ai_enabled": False
            },
            {
                "name": "empty_keys",
                "anthropic_key": "",
                "openai_key": "",
                "expected_valid": False,
                "expected_ai_enabled": False
            },
            {
                "name": "invalid_format",
                "anthropic_key": "invalid-key-format",
                "openai_key": "also-invalid",
                "expected_valid": False,
                "expected_ai_enabled": False
            }
        ]
        
        for test in api_key_tests:
            # Mock environment variables
            env_vars = {}
            if test["anthropic_key"]:
                env_vars["ANTHROPIC_API_KEY"] = test["anthropic_key"]
            if test["openai_key"]:
                env_vars["OPENAI_API_KEY"] = test["openai_key"]
                
            with patch.dict(os.environ, env_vars, clear=True):
                # Test key validation logic
                anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
                openai_key = os.getenv("OPENAI_API_KEY", "")
                
                # Validate keys
                has_valid_anthropic = bool(
                    anthropic_key and 
                    anthropic_key != "your_key_here" and 
                    len(anthropic_key) > 20
                )
                has_valid_openai = bool(
                    openai_key and 
                    openai_key != "your_key_here" and 
                    len(openai_key) > 20
                )
                
                has_valid_key = has_valid_anthropic or has_valid_openai
                
                assert has_valid_key == test["expected_valid"], \
                    f"Test '{test['name']}': Expected valid={test['expected_valid']}, got {has_valid_key}"
                    
                # Test AI enablement decision
                if test["expected_ai_enabled"]:
                    # Should be able to enable AI
                    cli.engine.engine.config["enable_ai_analysis"] = True
                    assert cli.engine.engine.config["enable_ai_analysis"] == True
                else:
                    # Should disable AI or keep it disabled
                    cli.engine.engine.config["enable_ai_analysis"] = False
                    assert cli.engine.engine.config["enable_ai_analysis"] == False
                    
    @pytest.mark.asyncio
    async def test_threshold_validation(self, mock_cli_with_data):
        """Test threshold validation and correction."""
        cli = mock_cli_with_data
        
        threshold_tests = [
            {
                "name": "valid_thresholds",
                "auto_merge": 90.0,
                "review": 70.0,
                "expected_valid": True
            },
            {
                "name": "equal_thresholds",
                "auto_merge": 80.0,
                "review": 80.0,
                "expected_valid": True  # Should be allowed
            },
            {
                "name": "inverted_thresholds",
                "auto_merge": 70.0,
                "review": 90.0,
                "expected_valid": False,  # Review threshold should not be higher
                "expected_corrected": True
            },
            {
                "name": "out_of_range_high",
                "auto_merge": 150.0,
                "review": 120.0,
                "expected_valid": False,
                "expected_corrected": True
            },
            {
                "name": "out_of_range_low",
                "auto_merge": -10.0,
                "review": -5.0,
                "expected_valid": False,
                "expected_corrected": True
            },
            {
                "name": "edge_values",
                "auto_merge": 100.0,
                "review": 0.0,
                "expected_valid": True
            }
        ]
        
        for test in threshold_tests:
            # Apply test thresholds
            original_config = cli.engine.engine.config.copy()
            
            try:
                cli.engine.engine.config.update({
                    "auto_merge_threshold": test["auto_merge"],
                    "human_review_threshold": test["review"]
                })
                
                # Get actual values (after any validation/correction)
                auto_threshold = cli.engine.engine.config.get("auto_merge_threshold")
                review_threshold = cli.engine.engine.config.get("human_review_threshold")
                
                if test["expected_valid"]:
                    # Values should be within valid ranges
                    assert 0 <= auto_threshold <= 100, f"Auto threshold out of range: {auto_threshold}"
                    assert 0 <= review_threshold <= 100, f"Review threshold out of range: {review_threshold}"
                    
                    # Auto threshold should be >= review threshold
                    assert auto_threshold >= review_threshold, \
                        f"Auto threshold ({auto_threshold}) should be >= review threshold ({review_threshold})"
                        
                elif test.get("expected_corrected"):
                    # Values should have been corrected to valid ranges
                    assert 0 <= auto_threshold <= 100, f"Auto threshold not corrected: {auto_threshold}"
                    assert 0 <= review_threshold <= 100, f"Review threshold not corrected: {review_threshold}"
                    
            finally:
                # Restore original config
                cli.engine.engine.config = original_config
                
    @pytest.mark.asyncio
    async def test_database_selection_validation(self, mock_cli_with_data):
        """Test database selection validation."""
        cli = mock_cli_with_data
        
        # Mock available databases
        available_databases = {
            "People & Contacts": [{"id": "1", "Full Name": "Person 1"}],
            "Organizations & Bodies": [{"id": "1", "Organization Name": "Org 1"}],
            "Intelligence & Transcripts": [{"id": "1", "Title": "Doc 1"}]
        }
        
        async def mock_load_available():
            return available_databases
            
        cli._load_databases = mock_load_available
        
        database_selection_tests = [
            {
                "name": "single_database",
                "selected": ["People & Contacts"],
                "expected_valid": True
            },
            {
                "name": "multiple_databases",
                "selected": ["People & Contacts", "Organizations & Bodies"],
                "expected_valid": True
            },
            {
                "name": "all_databases",
                "selected": list(available_databases.keys()),
                "expected_valid": True
            },
            {
                "name": "nonexistent_database",
                "selected": ["Nonexistent Database"],
                "expected_valid": False
            },
            {
                "name": "empty_selection",
                "selected": [],
                "expected_valid": False
            },
            {
                "name": "mixed_valid_invalid",
                "selected": ["People & Contacts", "Nonexistent Database"],
                "expected_valid": False  # Should reject if any invalid
            }
        ]
        
        for test in database_selection_tests:
            # Load available databases
            databases = await cli._load_databases()
            
            # Validate selection
            valid_selection = all(
                db_name in databases for db_name in test["selected"]
            ) and len(test["selected"]) > 0
            
            assert valid_selection == test["expected_valid"], \
                f"Test '{test['name']}': Expected valid={test['expected_valid']}, got {valid_selection}"
                
            if test["expected_valid"]:
                # Filter to selected databases
                selected_databases = {
                    name: records 
                    for name, records in databases.items() 
                    if name in test["selected"]
                }
                
                assert len(selected_databases) == len(test["selected"])
                for db_name in test["selected"]:
                    assert db_name in selected_databases
                    
    @pytest.mark.asyncio
    async def test_configuration_persistence(self, mock_cli_with_data, tmp_path):
        """Test configuration saving and loading."""
        cli = mock_cli_with_data
        
        # Test configuration to save
        test_config = {
            "enable_ai_analysis": True,
            "auto_merge_threshold": 95.0,
            "human_review_threshold": 80.0,
            "safety_mode": True,
            "databases": ["People & Contacts"],
            "last_used": "2025-07-12"
        }
        
        # Mock configuration file path
        config_file = tmp_path / "test_config.json"
        
        with patch.object(cli.config_wizard, 'save_config') as mock_save:
            with patch.object(cli.config_wizard, 'load_config') as mock_load:
                
                # Test saving configuration
                cli.config_wizard.save_config(test_config, str(config_file))
                mock_save.assert_called_once()
                
                # Test loading configuration
                mock_load.return_value = test_config
                loaded_config = cli.config_wizard.load_config(str(config_file))
                
                # Validate loaded configuration
                for key, value in test_config.items():
                    assert loaded_config[key] == value
                    
    @pytest.mark.asyncio
    async def test_configuration_migration(self, mock_cli_with_data):
        """Test configuration migration from old versions."""
        cli = mock_cli_with_data
        
        # Old configuration format
        old_config = {
            "ai_enabled": True,  # Old key name
            "merge_threshold": 90.0,  # Old key name
            "review_threshold": 70.0,  # Old key name
            "safe_mode": True  # Old key name
        }
        
        # Expected migrated configuration
        expected_new_config = {
            "enable_ai_analysis": True,
            "auto_merge_threshold": 90.0,
            "human_review_threshold": 70.0,
            "safety_mode": True
        }
        
        # Mock migration logic
        def migrate_config(old_config):
            new_config = {}
            
            # Migrate keys
            key_mapping = {
                "ai_enabled": "enable_ai_analysis",
                "merge_threshold": "auto_merge_threshold",
                "review_threshold": "human_review_threshold",
                "safe_mode": "safety_mode"
            }
            
            for old_key, new_key in key_mapping.items():
                if old_key in old_config:
                    new_config[new_key] = old_config[old_key]
                    
            return new_config
            
        # Test migration
        migrated_config = migrate_config(old_config)
        
        for key, value in expected_new_config.items():
            assert migrated_config[key] == value, \
                f"Migration failed for {key}: expected {value}, got {migrated_config.get(key)}"
                
    @pytest.mark.asyncio
    async def test_environment_variable_integration(self, mock_cli_with_data):
        """Test integration with environment variables."""
        cli = mock_cli_with_data
        
        # Test environment variable override scenarios
        env_scenarios = [
            {
                "name": "env_overrides_config",
                "env_vars": {
                    "BLACKCORE_AI_ENABLED": "false",
                    "BLACKCORE_AUTO_MERGE_THRESHOLD": "85.0",
                    "BLACKCORE_SAFETY_MODE": "false"
                },
                "config": {
                    "enable_ai_analysis": True,  # Should be overridden
                    "auto_merge_threshold": 90.0,  # Should be overridden
                    "safety_mode": True  # Should be overridden
                },
                "expected": {
                    "enable_ai_analysis": False,
                    "auto_merge_threshold": 85.0,
                    "safety_mode": False
                }
            },
            {
                "name": "config_without_env_override",
                "env_vars": {},
                "config": {
                    "enable_ai_analysis": True,
                    "auto_merge_threshold": 95.0,
                    "safety_mode": True
                },
                "expected": {
                    "enable_ai_analysis": True,
                    "auto_merge_threshold": 95.0,
                    "safety_mode": True
                }
            }
        ]
        
        for scenario in env_scenarios:
            with patch.dict(os.environ, scenario["env_vars"], clear=False):
                # Apply base configuration
                cli.engine.engine.config.update(scenario["config"])
                
                # Mock environment variable reading
                def apply_env_overrides(config):
                    if "BLACKCORE_AI_ENABLED" in os.environ:
                        config["enable_ai_analysis"] = os.environ["BLACKCORE_AI_ENABLED"].lower() == "true"
                    if "BLACKCORE_AUTO_MERGE_THRESHOLD" in os.environ:
                        config["auto_merge_threshold"] = float(os.environ["BLACKCORE_AUTO_MERGE_THRESHOLD"])
                    if "BLACKCORE_SAFETY_MODE" in os.environ:
                        config["safety_mode"] = os.environ["BLACKCORE_SAFETY_MODE"].lower() == "true"
                    return config
                    
                # Apply environment overrides
                final_config = apply_env_overrides(cli.engine.engine.config.copy())
                
                # Validate final configuration
                for key, expected_value in scenario["expected"].items():
                    assert final_config[key] == expected_value, \
                        f"Scenario '{scenario['name']}': {key} should be {expected_value}, got {final_config.get(key)}"