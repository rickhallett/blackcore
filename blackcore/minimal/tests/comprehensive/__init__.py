"""Comprehensive test suite for robust production validation.

This package contains high-ROI tests designed to catch critical issues with
minimal complexity. Tests are organized by value and implementation difficulty.
"""

# Test categories by ROI (Return on Investment)
HIGH_ROI_TESTS = [
    "test_realistic_workflows",     # End-to-end scenarios with real data
    "test_network_resilience",      # Network failures and timeouts
    "test_performance_baselines",   # Performance regression prevention
    "test_error_recovery",          # Error handling and recovery flows
    "test_security_basics",         # Essential security validations
]

MEDIUM_ROI_TESTS = [
    "test_large_scale",            # Batch processing and memory
    "test_configuration",          # Config validation and edge cases  
    "test_concurrency",            # Thread safety and race conditions
]

FUTURE_TESTS = [
    "test_chaos_engineering",      # Advanced failure injection (complex)
    "test_cross_platform",         # Platform compatibility (high maintenance)
    "test_advanced_monitoring",    # Operational excellence (complex setup)
]