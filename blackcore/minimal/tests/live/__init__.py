"""Live API integration tests.

These tests make actual API calls to external services and should be run sparingly.
They are controlled by environment variables and require proper API key configuration.

Usage:
    # Run all live tests
    ENABLE_LIVE_AI_TESTS=true pytest tests/live/
    
    # Run with spending limits  
    ENABLE_LIVE_AI_TESTS=true LIVE_TEST_SPEND_LIMIT=5.00 pytest tests/live/
    
    # Skip live tests (default)
    pytest tests/live/  # Will skip all tests
"""