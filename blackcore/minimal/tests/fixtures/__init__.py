"""Test fixtures for minimal module tests."""

# Explicitly import specific fixtures to avoid namespace pollution
from .transcript_fixtures import (
    SIMPLE_TRANSCRIPT,
    COMPLEX_TRANSCRIPT,
    EMPTY_TRANSCRIPT,
    LARGE_TRANSCRIPT,
    SPECIAL_CHARS_TRANSCRIPT,
    ERROR_TRANSCRIPT,
    TEST_TRANSCRIPTS,
    BATCH_TRANSCRIPTS,
)

# Import all exports from other fixture modules
from .notion_fixtures import *
from .ai_response_fixtures import *

# Make fixtures available at package level
__all__ = [
    'SIMPLE_TRANSCRIPT',
    'COMPLEX_TRANSCRIPT', 
    'EMPTY_TRANSCRIPT',
    'LARGE_TRANSCRIPT',
    'SPECIAL_CHARS_TRANSCRIPT',
    'ERROR_TRANSCRIPT',
    'TEST_TRANSCRIPTS',
    'BATCH_TRANSCRIPTS',
]
