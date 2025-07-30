"""Live test fixtures and configuration."""

import os
import pytest
from typing import Generator
from unittest.mock import patch

from .config import LiveTestConfig, CostTracker
from blackcore.minimal.ai_extractor import AIExtractor
from blackcore.minimal.models import Config, AIConfig, NotionConfig, ProcessingConfig


@pytest.fixture(scope="session")
def live_config() -> LiveTestConfig:
    """Load live test configuration from environment."""
    config = LiveTestConfig.from_env()
    
    # Validate configuration
    errors = config.validate()
    if errors:
        pytest.fail(f"Live test configuration errors: {'; '.join(errors)}")
    
    return config


@pytest.fixture(scope="session")
def cost_tracker(live_config: LiveTestConfig) -> CostTracker:
    """Create cost tracker for the test session."""
    return CostTracker(live_config.spend_limit)


@pytest.fixture(autouse=True)
def skip_if_live_tests_disabled(live_config: LiveTestConfig, request):
    """Auto-skip live tests if not enabled via environment variables."""
    test_name = request.node.name
    
    # Skip AI tests if not enabled
    if "ai" in test_name.lower() and not live_config.ai_tests_enabled:
        pytest.skip("Live AI tests disabled. Set ENABLE_LIVE_AI_TESTS=true to run.")
    
    # Skip Notion tests if not enabled  
    if "notion" in test_name.lower() and not live_config.notion_tests_enabled:
        pytest.skip("Live Notion tests disabled. Set ENABLE_LIVE_NOTION_TESTS=true to run.")


@pytest.fixture
def live_ai_extractor(live_config: LiveTestConfig, cost_tracker: CostTracker) -> Generator[AIExtractor, None, None]:
    """Create a real AI extractor for live testing."""
    if not live_config.ai_tests_enabled:
        pytest.skip("Live AI tests not enabled")
    
    # Create AI extractor with live API key
    extractor = AIExtractor(
        provider="claude",
        api_key=live_config.ai_api_key,
        model="claude-3-5-haiku-20241022",  # Use cost-effective model for testing
    )
    
    # Wrap the extract_entities method to track costs
    original_extract = extractor.extract_entities
    
    def cost_tracking_extract(text: str, prompt: str = None):
        # Rough token estimation (1 token ≈ 4 characters)
        input_tokens = len(text + (prompt or "")) // 4
        estimated_output_tokens = 500  # Conservative estimate
        
        if not cost_tracker.can_make_call(input_tokens, estimated_output_tokens):
            pytest.fail(f"Would exceed cost limit. Current: ${cost_tracker.estimated_cost}, Limit: ${cost_tracker.spend_limit}")
        
        result = original_extract(text, prompt)
        
        # Record actual cost (approximate)
        actual_output_tokens = len(str(result)) // 4
        cost_tracker.record_ai_call(input_tokens, actual_output_tokens)
        
        return result
    
    extractor.extract_entities = cost_tracking_extract
    
    yield extractor
    
    # Report costs at end of test
    summary = cost_tracker.get_summary()
    print(f"\nLive AI Test Cost Summary: ${summary['estimated_cost']:.3f} / ${summary['spend_limit']:.2f} "
          f"({summary['budget_used_percent']:.1f}%) - {summary['ai_calls_made']} calls")


@pytest.fixture
def live_test_config(live_config: LiveTestConfig) -> Config:
    """Create a Config object for live testing."""
    return Config(
        ai=AIConfig(
            provider="claude",
            api_key=live_config.ai_api_key,
            model="claude-3-5-haiku-20241022",  # Cost-effective model
            max_tokens=1000,  # Limit tokens to control costs
            temperature=0.1,  # Low temperature for consistent results
        ),
        notion=NotionConfig(
            api_key=live_config.notion_api_key or "dummy-key",
            databases={},  # Will be populated by specific tests
            rate_limit=1.0,  # Conservative rate limiting for live tests
        ),
        processing=ProcessingConfig(
            cache_dir=".live_test_cache",
            dry_run=False,
            verbose=True,
        ),
    )


@pytest.fixture(scope="session", autouse=True)
def live_test_session_summary(cost_tracker: CostTracker):
    """Print session summary at the end of all live tests."""
    yield
    
    summary = cost_tracker.get_summary()
    if summary["ai_calls_made"] > 0:
        print(f"\n{'='*60}")
        print("LIVE TEST SESSION SUMMARY")
        print(f"{'='*60}")
        print(f"Total estimated cost: ${summary['estimated_cost']:.3f}")
        print(f"Budget limit: ${summary['spend_limit']:.2f}")
        print(f"Budget used: {summary['budget_used_percent']:.1f}%")
        print(f"AI calls made: {summary['ai_calls_made']}")
        print(f"Remaining budget: ${summary['remaining_budget']:.3f}")
        
        if summary["budget_used_percent"] > 80:
            print("⚠️  WARNING: High budget usage!")
        print(f"{'='*60}")


@pytest.fixture
def prevent_accidental_production_calls():
    """Safety fixture to prevent accidental calls to production APIs."""
    production_keys = [
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY", 
        "NOTION_API_KEY"
    ]
    
    # Temporarily unset production API keys during live tests
    with patch.dict('os.environ', {}, clear=False):
        for key in production_keys:
            if key in os.environ:
                # Hide production keys during live tests
                os.environ[f"_BACKUP_{key}"] = os.environ[key]
                del os.environ[key]
        
        yield
        
        # Restore production keys
        for key in production_keys:
            backup_key = f"_BACKUP_{key}"
            if backup_key in os.environ:
                os.environ[key] = os.environ[backup_key]
                del os.environ[backup_key]