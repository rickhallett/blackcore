"""Configuration for live API integration tests."""

import os
from typing import Optional
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class LiveTestConfig:
    """Configuration for live API tests."""
    
    # Feature flags
    ai_tests_enabled: bool = False
    notion_tests_enabled: bool = False
    
    # API Keys (separate from production)
    ai_api_key: Optional[str] = None  
    notion_api_key: Optional[str] = None
    
    # Cost controls
    spend_limit: Decimal = Decimal("10.00")  # USD limit per test run
    max_ai_calls: int = 50  # Maximum AI API calls per test run
    
    # Test isolation
    notion_workspace_id: Optional[str] = None  # Dedicated test workspace
    test_data_prefix: str = "LIVETEST_"  # Prefix for test data
    
    # Timeouts and retries
    api_timeout: float = 30.0  # Seconds
    max_retries: int = 3
    
    @classmethod
    def from_env(cls) -> "LiveTestConfig":
        """Create configuration from environment variables."""
        return cls(
            ai_tests_enabled=os.getenv("ENABLE_LIVE_AI_TESTS", "false").lower() == "true",
            notion_tests_enabled=os.getenv("ENABLE_LIVE_NOTION_TESTS", "false").lower() == "true",
            ai_api_key=os.getenv("LIVE_TEST_AI_API_KEY"),  # Separate from ANTHROPIC_API_KEY
            notion_api_key=os.getenv("LIVE_TEST_NOTION_API_KEY"),  # Separate from NOTION_API_KEY
            spend_limit=Decimal(os.getenv("LIVE_TEST_SPEND_LIMIT", "10.00")),
            max_ai_calls=int(os.getenv("LIVE_TEST_MAX_AI_CALLS", "50")),
            notion_workspace_id=os.getenv("LIVE_TEST_NOTION_WORKSPACE"),
            test_data_prefix=os.getenv("LIVE_TEST_DATA_PREFIX", "LIVETEST_"),
            api_timeout=float(os.getenv("LIVE_TEST_API_TIMEOUT", "30.0")),
            max_retries=int(os.getenv("LIVE_TEST_MAX_RETRIES", "3")),
        )
    
    def validate(self) -> list[str]:
        """Validate configuration and return any errors."""
        errors = []
        
        if self.ai_tests_enabled and not self.ai_api_key:
            errors.append("LIVE_TEST_AI_API_KEY required when ENABLE_LIVE_AI_TESTS=true")
            
        if self.notion_tests_enabled and not self.notion_api_key:
            errors.append("LIVE_TEST_NOTION_API_KEY required when ENABLE_LIVE_NOTION_TESTS=true")
            
        if self.spend_limit <= 0:
            errors.append("LIVE_TEST_SPEND_LIMIT must be positive")
            
        if self.max_ai_calls <= 0:
            errors.append("LIVE_TEST_MAX_AI_CALLS must be positive")
            
        return errors


class CostTracker:
    """Tracks estimated costs during live test runs."""
    
    def __init__(self, spend_limit: Decimal):
        self.spend_limit = spend_limit
        self.estimated_cost = Decimal("0.00")
        self.ai_calls_made = 0
        
        # Rough cost estimates (as of 2025)
        self.claude_cost_per_1k_tokens = Decimal("0.008")  # Input tokens
        self.claude_output_cost_per_1k_tokens = Decimal("0.024")  # Output tokens
        
    def estimate_ai_call_cost(self, input_tokens: int, output_tokens: int) -> Decimal:
        """Estimate cost of an AI API call."""
        input_cost = (Decimal(input_tokens) / 1000) * self.claude_cost_per_1k_tokens
        output_cost = (Decimal(output_tokens) / 1000) * self.claude_output_cost_per_1k_tokens
        return input_cost + output_cost
    
    def record_ai_call(self, input_tokens: int, output_tokens: int) -> bool:
        """Record an AI call and return False if over budget."""
        call_cost = self.estimate_ai_call_cost(input_tokens, output_tokens)
        
        if self.estimated_cost + call_cost > self.spend_limit:
            return False  # Would exceed budget
            
        self.estimated_cost += call_cost
        self.ai_calls_made += 1
        return True
    
    def can_make_call(self, estimated_input_tokens: int = 1000, estimated_output_tokens: int = 500) -> bool:
        """Check if we can make another call without exceeding budget."""
        estimated_cost = self.estimate_ai_call_cost(estimated_input_tokens, estimated_output_tokens)
        return self.estimated_cost + estimated_cost <= self.spend_limit
    
    def get_summary(self) -> dict:
        """Get cost tracking summary."""
        return {
            "estimated_cost": float(self.estimated_cost),
            "spend_limit": float(self.spend_limit),  
            "remaining_budget": float(self.spend_limit - self.estimated_cost),
            "ai_calls_made": self.ai_calls_made,
            "budget_used_percent": float((self.estimated_cost / self.spend_limit) * 100),
        }