"""
Interactive CLI for Blackcore Deduplication Engine

This module provides user-friendly command-line interfaces for the deduplication
system, with different modes for various user expertise levels.
"""

from .standard_mode import StandardModeCLI
from .ui_components import UIComponents, ProgressTracker, MatchReviewDisplay
from .config_wizard import ConfigurationWizard
from .async_engine import AsyncDeduplicationEngine

__all__ = [
    'StandardModeCLI',
    'UIComponents',
    'ProgressTracker',
    'MatchReviewDisplay',
    'ConfigurationWizard',
    'AsyncDeduplicationEngine',
]

__version__ = '1.0.0'