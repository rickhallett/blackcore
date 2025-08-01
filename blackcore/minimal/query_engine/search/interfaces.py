"""Search module interfaces for the query engine.

This module defines the protocols and data structures for text search functionality.
"""

from typing import List, Dict, Any, Optional, Protocol, Tuple
from dataclasses import dataclass, field
from enum import Enum


class SearchMode(Enum):
    """Different search modes supported by the engine."""
    EXACT = "exact"
    FUZZY = "fuzzy"
    SEMANTIC = "semantic"
    PHONETIC = "phonetic"


@dataclass
class SearchConfig:
    """Configuration for search operations."""
    mode: SearchMode = SearchMode.FUZZY
    max_results: int = 100
    min_score: float = 0.0
    field_weights: Dict[str, float] = field(default_factory=dict)
    fuzzy_threshold: float = 0.8
    highlight_matches: bool = True
    case_sensitive: bool = False
    use_stemming: bool = True
    use_synonyms: bool = False


@dataclass
class SearchResult:
    """Rich search result with relevance and highlighting."""
    entity: Dict[str, Any]
    score: float
    highlights: Dict[str, List[str]]
    explanation: str
    matched_fields: List[str]
    
    def __lt__(self, other: 'SearchResult') -> bool:
        """Enable sorting by score (descending)."""
        return self.score > other.score


@dataclass
class SearchContext:
    """Context information for search operations."""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    previous_queries: List[str] = field(default_factory=list)
    filters: Dict[str, Any] = field(default_factory=dict)
    locale: str = "en"


class TextSearchEngine(Protocol):
    """Protocol for text search implementations."""
    
    def search(
        self, 
        query_text: str, 
        data: List[Dict[str, Any]], 
        config: SearchConfig
    ) -> List[SearchResult]:
        """Search through data with the given query.
        
        Args:
            query_text: The search query
            data: List of entities to search through
            config: Search configuration
            
        Returns:
            List of search results sorted by relevance
        """
        ...
    
    def calculate_relevance_score(
        self, 
        item: Dict[str, Any], 
        query_text: str, 
        field_weights: Dict[str, float]
    ) -> float:
        """Calculate relevance score for a single item.
        
        Args:
            item: The entity to score
            query_text: The search query
            field_weights: Weights for different fields
            
        Returns:
            Relevance score between 0 and 1
        """
        ...
    
    def highlight_matches(
        self,
        text: str,
        query_text: str,
        context_chars: int = 50
    ) -> List[str]:
        """Generate highlighted snippets for matches.
        
        Args:
            text: The text to search in
            query_text: The search query
            context_chars: Number of context characters around match
            
        Returns:
            List of highlighted snippets
        """
        ...
    
    def tokenize(self, text: str) -> List[str]:
        """Tokenize text for searching.
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of tokens
        """
        ...
    
    def fuzzy_match(
        self,
        query: str,
        text: str,
        threshold: float = 0.8
    ) -> Tuple[bool, float]:
        """Perform fuzzy string matching.
        
        Args:
            query: Query string
            text: Text to match against
            threshold: Minimum similarity score
            
        Returns:
            Tuple of (is_match, similarity_score)
        """
        ...


class SearchIndexer(Protocol):
    """Protocol for search indexing implementations."""
    
    def build_index(self, data: List[Dict[str, Any]]) -> None:
        """Build search index from data.
        
        Args:
            data: List of entities to index
        """
        ...
    
    def update_index(self, entity: Dict[str, Any]) -> None:
        """Update index with a single entity.
        
        Args:
            entity: Entity to add or update in index
        """
        ...
    
    def remove_from_index(self, entity_id: str) -> None:
        """Remove entity from index.
        
        Args:
            entity_id: ID of entity to remove
        """
        ...
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the search index.
        
        Returns:
            Dictionary with index statistics
        """
        ...


class SearchAnalyzer(Protocol):
    """Protocol for search query analysis."""
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze search query for insights.
        
        Args:
            query: Search query to analyze
            
        Returns:
            Analysis results including tokens, intent, etc.
        """
        ...
    
    def suggest_queries(
        self,
        partial_query: str,
        context: Optional[SearchContext] = None
    ) -> List[str]:
        """Suggest query completions.
        
        Args:
            partial_query: Partial query string
            context: Search context
            
        Returns:
            List of suggested queries
        """
        ...
    
    def spell_correct(self, query: str) -> str:
        """Correct spelling in query.
        
        Args:
            query: Query with potential spelling errors
            
        Returns:
            Corrected query
        """
        ...