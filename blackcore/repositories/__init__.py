"""Repository pattern implementation for data access."""

from .base import BaseRepository, RepositoryError
from .page import PageRepository
from .database import DatabaseRepository
from .search import SearchRepository

__all__ = [
    "BaseRepository",
    "RepositoryError",
    "PageRepository",
    "DatabaseRepository",
    "SearchRepository",
]