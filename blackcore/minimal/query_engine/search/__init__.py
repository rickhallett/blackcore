"""Search module for the query engine."""

from .interfaces import (
    SearchMode,
    SearchConfig,
    SearchResult,
    SearchContext,
    TextSearchEngine,
    SearchIndexer,
    SearchAnalyzer
)

from .text_search import SimpleTextSearchEngine
from .fuzzy_matcher import FuzzyMatcher
from .semantic_search import (
    SemanticSearchEngine,
    SemanticSearchResult,
    TokenInfo
)

__all__ = [
    # Enums
    "SearchMode",
    
    # Data classes
    "SearchConfig",
    "SearchResult",
    "SearchContext",
    
    # Protocols
    "TextSearchEngine",
    "SearchIndexer",
    "SearchAnalyzer",
    
    # Implementations
    "SimpleTextSearchEngine",
    "FuzzyMatcher",
    "SemanticSearchEngine",
    "SemanticSearchResult",
    "TokenInfo"
]