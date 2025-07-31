"""Repository pattern implementation for minimal module."""

from .base import BaseRepository, RepositoryError
from .page import PageRepository
from .database import DatabaseRepository

__all__ = [
    "BaseRepository",
    "RepositoryError", 
    "PageRepository",
    "DatabaseRepository",
]