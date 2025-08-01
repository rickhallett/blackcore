"""Natural Language Processing module for the query engine."""

from .interfaces import (
    QueryIntent,
    EntityType,
    ExtractedEntity,
    ParsedQuery,
    QuerySuggestion,
    SpellCorrection,
    NLPConfig,
    QueryParser,
    QuerySuggester,
    SpellChecker,
    SynonymResolver,
    QueryTranslator,
    ContextAnalyzer
)

from .query_parser import SimpleQueryParser
from .spell_checker import SimpleSpellChecker, ContextualSpellChecker
from .query_suggester import IntelligentQuerySuggester

__all__ = [
    # Enums
    "QueryIntent",
    "EntityType",
    
    # Data classes
    "ExtractedEntity",
    "ParsedQuery",
    "QuerySuggestion",
    "SpellCorrection",
    "NLPConfig",
    
    # Protocols
    "QueryParser",
    "QuerySuggester",
    "SpellChecker",
    "SynonymResolver",
    "QueryTranslator",
    "ContextAnalyzer",
    
    # Implementations
    "SimpleQueryParser",
    "SimpleSpellChecker",
    "ContextualSpellChecker",
    "IntelligentQuerySuggester"
]