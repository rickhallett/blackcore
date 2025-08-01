"""Semantic search engine with NLP capabilities for the Query Engine."""

import re
import math
from typing import List, Dict, Any, Tuple, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict, Counter
import unicodedata
from difflib import SequenceMatcher
import logging

from ..interfaces import TextSearchEngine
from ..models import SearchConfig, SearchResult

logger = logging.getLogger(__name__)


@dataclass
class TokenInfo:
    """Information about a token for scoring."""
    text: str
    normalized: str
    position: int
    field: str
    is_entity: bool = False
    entity_type: Optional[str] = None


@dataclass
class SemanticSearchResult(SearchResult):
    """Enhanced search result with semantic information."""
    highlights: Dict[str, List[str]] = field(default_factory=dict)
    explanation: str = ""
    matched_tokens: List[TokenInfo] = field(default_factory=list)
    semantic_score: float = 0.0


class SemanticSearchEngine(TextSearchEngine):
    """Advanced text search with NLP and semantic capabilities."""
    
    def __init__(self):
        """Initialize the semantic search engine."""
        # Common stop words for filtering
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'under', 'again',
            'further', 'then', 'once', 'is', 'are', 'was', 'were', 'been', 'be',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these',
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'them', 'their',
            'what', 'which', 'who', 'when', 'where', 'why', 'how', 'all', 'each',
            'every', 'some', 'any', 'few', 'more', 'most', 'other', 'such', 'no',
            'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very'
        }
        
        # Entity patterns for recognition
        self.entity_patterns = {
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'phone': re.compile(r'\b(?:\+?1[-.]?)?\(?[0-9]{3}\)?[-.]?[0-9]{3}[-.]?[0-9]{4}\b'),
            'date': re.compile(r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b|\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b'),
            'url': re.compile(r'https?://[^\s]+'),
            'mention': re.compile(r'@[A-Za-z0-9_]+'),
            'hashtag': re.compile(r'#[A-Za-z0-9_]+'),
            'number': re.compile(r'\b\d+(?:\.\d+)?\b'),
            'currency': re.compile(r'\$\d+(?:,\d{3})*(?:\.\d{2})?|\b\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:USD|EUR|GBP)\b')
        }
        
        # Synonyms for query expansion
        self.synonyms = {
            'meeting': ['conference', 'session', 'gathering', 'assembly'],
            'task': ['todo', 'action', 'assignment', 'job'],
            'document': ['file', 'report', 'paper', 'record'],
            'person': ['contact', 'individual', 'member', 'user'],
            'organization': ['company', 'firm', 'entity', 'institution'],
            'project': ['initiative', 'program', 'venture', 'effort'],
            'issue': ['problem', 'concern', 'matter', 'topic'],
            'complete': ['finish', 'done', 'accomplish', 'achieve'],
            'create': ['make', 'build', 'generate', 'produce'],
            'update': ['modify', 'change', 'edit', 'revise']
        }
        
        # Field importance weights
        self.default_field_weights = {
            'properties.Title': 2.0,
            'properties.Name': 2.0,
            'properties.Description': 1.5,
            'properties.Content': 1.0,
            'properties.Tags': 1.8,
            'properties.Category': 1.5,
            'properties.Department': 1.3,
            'properties.Status': 1.2,
            'id': 0.5
        }
        
        # Compile patterns for performance
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for performance."""
        self.word_pattern = re.compile(r'\w+')
        self.sentence_pattern = re.compile(r'[.!?]+')
    
    def search(self, query_text: str, data: List[Dict[str, Any]], 
              config: Optional[SearchConfig] = None) -> List[SearchResult]:
        """Perform semantic search with NLP enhancements.
        
        Args:
            query_text: Natural language search query
            data: List of entities to search
            config: Search configuration
            
        Returns:
            List of search results ranked by relevance
        """
        if not query_text or not data:
            return []
        
        config = config or SearchConfig()
        
        # Parse and enhance query
        query_info = self._parse_query(query_text)
        
        # Score all items
        results = []
        for item in data:
            score, explanation, highlights = self._score_item(item, query_info, config)
            
            if score > config.min_score:
                results.append(SemanticSearchResult(
                    entity=item,
                    score=score,
                    database=item.get('_database', ''),
                    highlights=highlights,
                    explanation=explanation,
                    semantic_score=score
                ))
        
        # Sort by score
        results.sort(key=lambda x: x.score, reverse=True)
        
        # Apply limit
        if config.max_results:
            results = results[:config.max_results]
        
        return results
    
    def calculate_relevance_score(self, item: Dict[str, Any], query_text: str,
                                field_weights: Optional[Dict[str, float]] = None) -> float:
        """Calculate relevance score for a single item.
        
        Args:
            item: Entity to score
            query_text: Search query
            field_weights: Custom field importance weights
            
        Returns:
            Relevance score between 0 and 1
        """
        query_info = self._parse_query(query_text)
        score, _, _ = self._score_item(
            item, 
            query_info, 
            SearchConfig(field_weights=field_weights or self.default_field_weights)
        )
        return score
    
    def _parse_query(self, query_text: str) -> Dict[str, Any]:
        """Parse query with NLP techniques.
        
        Args:
            query_text: Raw query text
            
        Returns:
            Parsed query information
        """
        normalized = self._normalize_text(query_text)
        tokens = self._tokenize(normalized)
        
        # Extract entities
        entities = self._extract_entities(query_text)
        
        # Expand with synonyms
        expanded_tokens = self._expand_query(tokens)
        
        # Detect query intent
        intent = self._detect_intent(query_text, tokens, entities)
        
        # Extract key phrases
        phrases = self._extract_phrases(normalized)
        
        return {
            'original': query_text,
            'normalized': normalized,
            'tokens': tokens,
            'expanded_tokens': expanded_tokens,
            'entities': entities,
            'intent': intent,
            'phrases': phrases,
            'is_question': query_text.strip().endswith('?'),
            'has_quotes': '"' in query_text,
            'quoted_phrases': self._extract_quoted(query_text)
        }
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for consistent matching."""
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Normalize unicode
        text = unicodedata.normalize('NFKD', text)
        
        # Remove accents
        text = ''.join(c for c in text if not unicodedata.combining(c))
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        return text
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words."""
        tokens = self.word_pattern.findall(text)
        # Filter stop words but keep if they're the only tokens
        filtered = [t for t in tokens if t not in self.stop_words]
        return filtered if filtered else tokens
    
    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract named entities from text."""
        entities = defaultdict(list)
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = pattern.findall(text)
            if matches:
                entities[entity_type].extend(matches)
        
        return dict(entities)
    
    def _expand_query(self, tokens: List[str]) -> Set[str]:
        """Expand query with synonyms."""
        expanded = set(tokens)
        
        for token in tokens:
            if token in self.synonyms:
                expanded.update(self.synonyms[token])
        
        return expanded
    
    def _detect_intent(self, query: str, tokens: List[str], 
                      entities: Dict[str, List[str]]) -> str:
        """Detect query intent for better ranking."""
        query_lower = query.lower()
        
        # Question patterns
        if query.strip().endswith('?'):
            if any(q in query_lower for q in ['who', 'what person']):
                return 'find_person'
            elif any(q in query_lower for q in ['where', 'what place']):
                return 'find_location'
            elif any(q in query_lower for q in ['when', 'what time']):
                return 'find_time'
            elif 'how many' in query_lower:
                return 'count'
            elif 'why' in query_lower:
                return 'explain'
        
        # Command patterns
        if any(cmd in tokens for cmd in ['find', 'search', 'get', 'show']):
            if entities.get('email') or any(t in tokens for t in ['person', 'contact', 'user']):
                return 'find_person'
            elif any(t in tokens for t in ['task', 'todo', 'action']):
                return 'find_task'
            elif any(t in tokens for t in ['document', 'file', 'report']):
                return 'find_document'
        
        # Entity-based intent
        if entities.get('email') or entities.get('mention'):
            return 'find_person'
        elif entities.get('date'):
            return 'find_by_date'
        
        return 'general_search'
    
    def _extract_phrases(self, text: str) -> List[str]:
        """Extract meaningful phrases from text."""
        phrases = []
        
        # Extract n-grams (2-3 words)
        words = text.split()
        for n in [2, 3]:
            for i in range(len(words) - n + 1):
                phrase = ' '.join(words[i:i+n])
                if not any(w in self.stop_words for w in words[i:i+n]):
                    phrases.append(phrase)
        
        return phrases
    
    def _extract_quoted(self, text: str) -> List[str]:
        """Extract quoted phrases for exact matching."""
        quoted = re.findall(r'"([^"]+)"', text)
        return quoted
    
    def _score_item(self, item: Dict[str, Any], query_info: Dict[str, Any],
                   config: SearchConfig) -> Tuple[float, str, Dict[str, List[str]]]:
        """Score an item against the parsed query.
        
        Returns:
            Tuple of (score, explanation, highlights)
        """
        scores = defaultdict(float)
        highlights = defaultdict(list)
        explanations = []
        
        # Get field weights
        field_weights = config.field_weights or self.default_field_weights
        
        # Score each field
        for field_path, field_value in self._flatten_dict(item):
            if not isinstance(field_value, str):
                field_value = str(field_value)
            
            field_weight = field_weights.get(field_path, 1.0)
            
            # Exact match for quoted phrases
            for quoted in query_info['quoted_phrases']:
                if quoted.lower() in field_value.lower():
                    scores['exact'] += 5.0 * field_weight
                    highlights[field_path].append(quoted)
                    explanations.append(f"Exact match for '{quoted}'")
            
            # Token matching with position weighting
            field_tokens = self._tokenize(self._normalize_text(field_value))
            matched_tokens = set()
            
            for pos, token in enumerate(field_tokens):
                # Direct token match
                if token in query_info['tokens']:
                    position_weight = 1.0 / (1 + pos * 0.1)  # Earlier matches score higher
                    scores['token'] += field_weight * position_weight
                    matched_tokens.add(token)
                
                # Expanded token match (synonyms)
                elif token in query_info['expanded_tokens']:
                    position_weight = 1.0 / (1 + pos * 0.1)
                    scores['synonym'] += field_weight * position_weight * 0.8
                    matched_tokens.add(token)
            
            # Fuzzy matching
            for query_token in query_info['tokens']:
                best_ratio = 0
                best_match = None
                
                for field_token in field_tokens:
                    ratio = SequenceMatcher(None, query_token, field_token).ratio()
                    if ratio > best_ratio and ratio > 0.8:  # 80% similarity threshold
                        best_ratio = ratio
                        best_match = field_token
                
                if best_match and best_match not in matched_tokens:
                    scores['fuzzy'] += field_weight * best_ratio * 0.7
                    matched_tokens.add(best_match)
                    highlights[field_path].append(best_match)
            
            # Phrase matching
            field_text_lower = field_value.lower()
            for phrase in query_info['phrases']:
                if phrase in field_text_lower:
                    scores['phrase'] += field_weight * 2.0
                    highlights[field_path].append(phrase)
            
            # Add highlights
            if matched_tokens:
                # Create highlight snippets
                snippets = self._create_highlights(field_value, matched_tokens)
                highlights[field_path].extend(snippets)
        
        # Entity bonus
        for entity_type, entities in query_info['entities'].items():
            for entity in entities:
                if self._contains_entity(item, entity, entity_type):
                    scores['entity'] += 3.0
                    explanations.append(f"Contains {entity_type}: {entity}")
        
        # Intent-based scoring
        intent_score = self._score_by_intent(item, query_info['intent'])
        scores['intent'] = intent_score
        
        # Calculate final score
        total_score = sum(scores.values())
        
        # Normalize to 0-1 range
        max_possible_score = len(query_info['tokens']) * max(field_weights.values()) * 5
        normalized_score = min(1.0, total_score / max_possible_score)
        
        # Create explanation
        if explanations:
            explanation = '; '.join(explanations)
        else:
            explanation = f"Matched {len(scores)} criteria"
        
        return normalized_score, explanation, dict(highlights)
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '') -> List[Tuple[str, Any]]:
        """Flatten nested dictionary for field access."""
        items = []
        
        for k, v in d.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key))
            elif isinstance(v, list):
                # Convert list items to string
                items.append((new_key, ' '.join(str(i) for i in v)))
            else:
                items.append((new_key, v))
        
        return items
    
    def _create_highlights(self, text: str, matched_tokens: Set[str], 
                          context_size: int = 50) -> List[str]:
        """Create highlighted snippets around matched tokens."""
        highlights = []
        text_lower = text.lower()
        
        for token in matched_tokens:
            # Find all occurrences
            start = 0
            while True:
                pos = text_lower.find(token.lower(), start)
                if pos == -1:
                    break
                
                # Extract context
                context_start = max(0, pos - context_size)
                context_end = min(len(text), pos + len(token) + context_size)
                
                # Find word boundaries
                if context_start > 0:
                    while context_start < pos and text[context_start] not in ' \n\t':
                        context_start += 1
                
                if context_end < len(text):
                    while context_end > pos + len(token) and text[context_end - 1] not in ' \n\t':
                        context_end -= 1
                
                snippet = text[context_start:context_end].strip()
                if context_start > 0:
                    snippet = '...' + snippet
                if context_end < len(text):
                    snippet = snippet + '...'
                
                highlights.append(snippet)
                start = pos + 1
        
        return highlights[:3]  # Limit to 3 highlights per field
    
    def _contains_entity(self, item: Dict[str, Any], entity: str, 
                        entity_type: str) -> bool:
        """Check if item contains a specific entity."""
        entity_lower = entity.lower()
        
        for _, value in self._flatten_dict(item):
            if not isinstance(value, str):
                value = str(value)
            
            if entity_type in ['email', 'phone', 'url']:
                # Exact match for structured data
                if entity_lower == value.lower():
                    return True
            else:
                # Substring match for other entities
                if entity_lower in value.lower():
                    return True
        
        return False
    
    def _score_by_intent(self, item: Dict[str, Any], intent: str) -> float:
        """Apply intent-specific scoring bonuses."""
        score = 0.0
        
        if intent == 'find_person':
            # Boost items with person-related fields
            if any(field in str(item) for field in ['Name', 'Email', 'Contact', 'Person']):
                score += 2.0
            if item.get('_database') == 'People & Contacts':
                score += 3.0
                
        elif intent == 'find_task':
            # Boost task-related items
            if any(field in str(item) for field in ['Task', 'Todo', 'Action', 'Status']):
                score += 2.0
            if item.get('_database') == 'Actionable Tasks':
                score += 3.0
                
        elif intent == 'find_document':
            # Boost document-related items
            if any(field in str(item) for field in ['Document', 'File', 'Report', 'Content']):
                score += 2.0
            if item.get('_database') == 'Documents & Evidence':
                score += 3.0
                
        elif intent == 'find_by_date':
            # Boost items with date fields
            for _, value in self._flatten_dict(item):
                if isinstance(value, str) and self.entity_patterns['date'].search(value):
                    score += 1.5
        
        return score
    
    def get_search_suggestions(self, partial_query: str, 
                             data: List[Dict[str, Any]], 
                             max_suggestions: int = 10) -> List[str]:
        """Generate search suggestions based on partial query.
        
        Args:
            partial_query: Partial search query
            data: Available data to analyze
            max_suggestions: Maximum suggestions to return
            
        Returns:
            List of suggested complete queries
        """
        if len(partial_query) < 2:
            return []
        
        normalized = self._normalize_text(partial_query)
        suggestions = []
        
        # Collect all searchable text
        all_text = []
        for item in data[:1000]:  # Sample for performance
            for _, value in self._flatten_dict(item):
                if isinstance(value, str):
                    all_text.append(value)
        
        # Find matching phrases
        seen = set()
        for text in all_text:
            text_lower = text.lower()
            if normalized in text_lower:
                # Extract the phrase around the match
                words = text.split()
                for i, word in enumerate(words):
                    if normalized in word.lower():
                        # Get surrounding words
                        start = max(0, i - 1)
                        end = min(len(words), i + 3)
                        suggestion = ' '.join(words[start:end])
                        
                        if suggestion not in seen and len(suggestion) < 100:
                            seen.add(suggestion)
                            suggestions.append(suggestion)
                            
                            if len(suggestions) >= max_suggestions:
                                return suggestions
        
        return suggestions