"""HTTP(S) API for Blackcore Minimal Transcript Processor.

This module provides a RESTful API interface to the transcript processing
functionality, enabling remote clients to submit transcripts and retrieve results.
"""

from .app import create_app
from .models import (
    TranscriptProcessRequest,
    ProcessingOptions,
    ProcessingResponse,
    ProcessingJob,
    JobStatus,
    APIError,
)

__all__ = [
    "create_app",
    "TranscriptProcessRequest",
    "ProcessingOptions",
    "ProcessingResponse",
    "ProcessingJob",
    "JobStatus",
    "APIError",
]
