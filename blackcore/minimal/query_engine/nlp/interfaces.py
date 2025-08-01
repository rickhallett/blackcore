"""Natural Language Processing module interfaces for the query engine.

This module defines the protocols and data structures for NLP functionality.
"""

from typing import List, Dict, Any, Optional, Protocol, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum


class QueryIntent(Enum):
    """Types of query intents."""
    SEARCH_ENTITY = "search_entity"
    FIND_RELATIONSHIP = "find_relationship"
    AGGREGATE_DATA = "aggregate_data"
    FILTER_RESULTS = "filter_results"
    SORT_RESULTS = "sort_results"
    EXPLAIN_ENTITY = "explain_entity"
    COMPARE_ENTITIES = "compare_entities"
    UNKNOWN = "unknown"


class EntityType(Enum):
    """Types of entities that can be extracted."""
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    DATE = "date"
    EVENT = "event"
    TASK = "task"
    DOCUMENT = "document"
    TRANSGRESSION = "transgression"
    OTHER = "other"


@dataclass
class ExtractedEntity:
    """Entity extracted from natural language."""
    text: str
    entity_type: EntityType
    confidence: float
    start_pos: int
    end_pos: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedQuery:
    """Parsed natural language query."""
    original_text: str
    intent: QueryIntent
    entities: List[ExtractedEntity]
    filters: Dict[str, Any]
    sort_criteria: List[Tuple[str, str]]  # (field, direction)
    limit: Optional[int]
    relationships_to_include: List[str]
    aggregations: List[Dict[str, Any]]
    confidence: float
    
    def to_structured_query(self) -> Dict[str, Any]:
        """Convert to structured query format."""
        return {
            "intent": self.intent.value,
            "entities": [
                {
                    "text": e.text,
                    "type": e.entity_type.value,
                    "confidence": e.confidence
                }
                for e in self.entities
            ],
            "filters": self.filters,
            "sort": self.sort_criteria,
            "limit": self.limit,
            "include": self.relationships_to_include,
            "aggregations": self.aggregations
        }


@dataclass
class QuerySuggestion:
    """Query suggestion with metadata."""
    text: str
    score: float
    category: str
    explanation: str
    example_results: int


@dataclass
class SpellCorrection:
    """Spelling correction suggestion."""
    original: str
    corrected: str
    confidence: float
    alternatives: List[Tuple[str, float]] = field(default_factory=list)


@dataclass
class NLPConfig:
    """Configuration for NLP processing."""
    language: str = "en"
    enable_spell_correction: bool = True
    enable_entity_extraction: bool = True
    enable_intent_classification: bool = True
    min_confidence: float = 0.5
    max_suggestions: int = 10
    use_context: bool = True
    model_name: Optional[str] = None


class QueryParser(Protocol):
    """Protocol for natural language query parsing."""
    
    def parse(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ParsedQuery:
        """Parse natural language query into structured format.
        
        Args:
            query: Natural language query
            context: Optional context for parsing
            
        Returns:
            Parsed query structure
        """
        ...
    
    def extract_entities(self, text: str) -> List[ExtractedEntity]:
        """Extract entities from text.
        
        Args:
            text: Text to extract entities from
            
        Returns:
            List of extracted entities
        """
        ...
    
    def classify_intent(
        self,
        query: str,
        entities: List[ExtractedEntity]
    ) -> Tuple[QueryIntent, float]:
        """Classify query intent.
        
        Args:
            query: Query text
            entities: Extracted entities
            
        Returns:
            Tuple of (intent, confidence)
        """
        ...
    
    def extract_filters(
        self,
        query: str,
        entities: List[ExtractedEntity]
    ) -> Dict[str, Any]:
        """Extract filter conditions from query.
        
        Args:
            query: Query text
            entities: Extracted entities
            
        Returns:
            Dictionary of filter conditions
        """
        ...


class QuerySuggester(Protocol):
    """Protocol for query suggestion functionality."""
    
    def suggest(
        self,
        partial_query: str,
        search_history: List[str],
        available_data: Optional[List[Dict[str, Any]]] = None
    ) -> List[QuerySuggestion]:
        """Generate query suggestions.
        
        Args:
            partial_query: Partial query text
            search_history: Previous queries
            available_data: Optional data for context
            
        Returns:
            List of query suggestions
        """
        ...
    
    def learn_from_selection(
        self,
        query: str,
        selected_suggestion: str,
        results_clicked: List[str]
    ) -> None:
        """Learn from user's suggestion selection.
        
        Args:
            query: Original query
            selected_suggestion: Suggestion that was selected
            results_clicked: IDs of results user clicked
        """
        ...


class SpellChecker(Protocol):
    """Protocol for spell checking functionality."""
    
    def check(self, text: str) -> List[SpellCorrection]:
        """Check spelling and suggest corrections.
        
        Args:
            text: Text to check
            
        Returns:
            List of corrections
        """
        ...
    
    def correct(self, text: str, auto_correct: bool = True) -> str:
        """Correct spelling in text.
        
        Args:
            text: Text to correct
            auto_correct: Whether to automatically apply corrections
            
        Returns:
            Corrected text
        """
        ...
    
    def add_to_dictionary(self, words: List[str]) -> None:
        """Add words to custom dictionary.
        
        Args:
            words: Words to add
        """
        ...


class SynonymResolver(Protocol):
    """Protocol for synonym resolution."""
    
    def get_synonyms(self, word: str) -> List[str]:
        """Get synonyms for a word.
        
        Args:
            word: Word to find synonyms for
            
        Returns:
            List of synonyms
        """
        ...
    
    def expand_query(self, query: str) -> List[str]:
        """Expand query with synonyms.
        
        Args:
            query: Original query
            
        Returns:
            List of expanded queries
        """
        ...
    
    def add_synonym_mapping(self, word: str, synonyms: List[str]) -> None:
        """Add custom synonym mapping.
        
        Args:
            word: Base word
            synonyms: List of synonyms
        """
        ...


class QueryTranslator(Protocol):
    """Protocol for translating natural language to query language."""
    
    def translate_to_filter(
        self,
        natural_language: str,
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Translate natural language to filter conditions.
        
        Args:
            natural_language: Natural language description
            schema: Data schema for validation
            
        Returns:
            Filter conditions
        """
        ...
    
    def translate_to_aggregation(
        self,
        natural_language: str,
        available_fields: List[str]
    ) -> Dict[str, Any]:
        """Translate natural language to aggregation query.
        
        Args:
            natural_language: Natural language description
            available_fields: Available fields for aggregation
            
        Returns:
            Aggregation specification
        """
        ...
    
    def explain_query(
        self,
        structured_query: Dict[str, Any]
    ) -> str:
        """Explain structured query in natural language.
        
        Args:
            structured_query: Structured query to explain
            
        Returns:
            Natural language explanation
        """
        ...


class ContextAnalyzer(Protocol):
    """Protocol for analyzing query context."""
    
    def analyze_context(
        self,
        current_query: str,
        previous_queries: List[str],
        session_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze query context for better understanding.
        
        Args:
            current_query: Current query
            previous_queries: Previous queries in session
            session_data: Session metadata
            
        Returns:
            Context analysis results
        """
        ...
    
    def resolve_references(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> str:
        """Resolve contextual references in query.
        
        Args:
            query: Query with potential references
            context: Context for resolution
            
        Returns:
            Query with resolved references
        """
        ...
    
    def track_topic_shift(
        self,
        queries: List[str]
    ) -> List[Tuple[int, str]]:
        """Track topic shifts in query sequence.
        
        Args:
            queries: Sequence of queries
            
        Returns:
            List of (index, topic) tuples indicating shifts
        """
        ...