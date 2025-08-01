"""Text search implementation for the query engine.

This module implements the core text search functionality with support for
exact, fuzzy, and weighted field searching.
"""

import re
import math
from typing import List, Dict, Any, Optional, Tuple, Set
from collections import defaultdict
from dataclasses import dataclass, field

from .interfaces import (
    TextSearchEngine,
    SearchConfig,
    SearchResult,
    SearchMode,
    SearchIndexer
)
from .fuzzy_matcher import FuzzyMatcher


class SimpleTextSearchEngine:
    """Basic text search implementation with fuzzy matching support."""
    
    def __init__(self):
        self.stop_words = self._load_stop_words()
        self.field_weights_default = {
            "title": 2.0,
            "name": 2.0,
            "description": 1.0,
            "content": 1.0,
            "tags": 1.5,
            "category": 1.2
        }
        self.fuzzy_matcher = FuzzyMatcher()
    
    def _load_stop_words(self) -> Set[str]:
        """Load common stop words."""
        return {
            "the", "is", "at", "which", "on", "and", "a", "an", "as", "are",
            "was", "were", "be", "have", "has", "had", "do", "does", "did",
            "will", "would", "should", "could", "may", "might", "can", "this",
            "that", "these", "those", "i", "you", "he", "she", "it", "we",
            "they", "what", "which", "who", "when", "where", "why", "how",
            "all", "each", "every", "some", "any", "many", "much", "few",
            "more", "most", "other", "another", "such", "no", "not", "only",
            "own", "same", "so", "than", "too", "very", "just", "but", "or",
            "if", "then", "else", "because", "while", "of", "for", "with",
            "about", "against", "between", "into", "through", "during", "before",
            "after", "above", "below", "to", "from", "up", "down", "in", "out",
            "off", "over", "under", "again", "further", "there", "here"
        }
    
    def search(
        self,
        query_text: str,
        data: List[Dict[str, Any]],
        config: SearchConfig
    ) -> List[SearchResult]:
        """Search through data with the given query."""
        if not query_text or not data:
            return []
        
        # Prepare query
        query_tokens = self.tokenize(query_text)
        if not query_tokens:
            return []
        
        # Score each item
        results = []
        for item in data:
            score = self.calculate_relevance_score(
                item,
                query_text,
                config.field_weights or self.field_weights_default
            )
            
            if score >= config.min_score:
                # Generate highlights if requested
                highlights = {}
                if config.highlight_matches:
                    for field, value in item.items():
                        if isinstance(value, str):
                            field_highlights = self.highlight_matches(
                                value, query_text
                            )
                            if field_highlights:
                                highlights[field] = field_highlights
                
                # Determine matched fields
                matched_fields = self._get_matched_fields(item, query_tokens)
                
                # Create result
                result = SearchResult(
                    entity=item,
                    score=score,
                    highlights=highlights,
                    explanation=self._generate_explanation(
                        score, matched_fields, config.mode
                    ),
                    matched_fields=matched_fields
                )
                results.append(result)
        
        # Sort by score (descending)
        results.sort()
        
        # Apply limit
        if config.max_results:
            results = results[:config.max_results]
        
        return results
    
    def calculate_relevance_score(
        self,
        item: Dict[str, Any],
        query_text: str,
        field_weights: Dict[str, float]
    ) -> float:
        """Calculate relevance score for a single item."""
        query_tokens = self.tokenize(query_text.lower())
        if not query_tokens:
            return 0.0
        
        total_score = 0.0
        matched_fields = 0
        
        for field, value in item.items():
            if not isinstance(value, str):
                continue
            
            field_weight = field_weights.get(field, 1.0)
            field_text = value.lower()
            field_tokens = self.tokenize(field_text)
            
            if not field_tokens:
                continue
            
            # Calculate field score
            field_score = self._calculate_field_score(
                query_tokens, field_tokens, field_text
            )
            
            if field_score > 0:
                total_score += field_score * field_weight
                matched_fields += 1
        
        # Normalize by number of matched fields
        if matched_fields > 0:
            total_score = total_score / math.sqrt(matched_fields)
        
        # Ensure score is between 0 and 1
        return min(1.0, total_score)
    
    def _calculate_field_score(
        self,
        query_tokens: List[str],
        field_tokens: List[str],
        field_text: str
    ) -> float:
        """Calculate score for a single field."""
        score = 0.0
        
        # Exact phrase match (highest score)
        query_phrase = " ".join(query_tokens)
        if query_phrase in field_text:
            score += 1.0
        
        # Token frequency scoring (TF-IDF simplified)
        token_freq = defaultdict(int)
        for token in field_tokens:
            token_freq[token] += 1
        
        matches = 0
        for query_token in query_tokens:
            if query_token in token_freq:
                # Basic TF scoring
                tf = token_freq[query_token] / len(field_tokens)
                score += tf * 0.5
                matches += 1
            else:
                # Check fuzzy matches
                for field_token in token_freq:
                    is_match, similarity = self.fuzzy_match(
                        query_token, field_token, 0.8
                    )
                    if is_match:
                        tf = token_freq[field_token] / len(field_tokens)
                        score += tf * similarity * 0.3
                        matches += 1
                        break
        
        # Boost score if all query tokens are found
        if matches == len(query_tokens):
            score *= 1.2
        
        return score
    
    def highlight_matches(
        self,
        text: str,
        query_text: str,
        context_chars: int = 50
    ) -> List[str]:
        """Generate highlighted snippets for matches."""
        if not text or not query_text:
            return []
        
        highlights = []
        query_tokens = self.tokenize(query_text.lower())
        text_lower = text.lower()
        
        # Find all match positions
        match_positions = []
        
        # Exact phrase matches
        query_phrase = " ".join(query_tokens)
        for match in re.finditer(re.escape(query_phrase), text_lower):
            match_positions.append((match.start(), match.end()))
        
        # Individual token matches
        for token in query_tokens:
            for match in re.finditer(r'\b' + re.escape(token) + r'\b', text_lower):
                match_positions.append((match.start(), match.end()))
        
        # Sort and merge overlapping positions
        match_positions.sort()
        merged_positions = self._merge_overlapping_positions(match_positions)
        
        # Generate snippets
        for start, end in merged_positions[:3]:  # Limit to 3 snippets
            snippet_start = max(0, start - context_chars)
            snippet_end = min(len(text), end + context_chars)
            
            # Find word boundaries
            if snippet_start > 0:
                while snippet_start < start and text[snippet_start] not in ' \n\t':
                    snippet_start += 1
            if snippet_end < len(text):
                while snippet_end > end and text[snippet_end - 1] not in ' \n\t':
                    snippet_end -= 1
            
            snippet = text[snippet_start:snippet_end].strip()
            if snippet:
                # Add ellipsis if needed
                if snippet_start > 0:
                    snippet = "..." + snippet
                if snippet_end < len(text):
                    snippet = snippet + "..."
                highlights.append(snippet)
        
        return highlights
    
    def tokenize(self, text: str) -> List[str]:
        """Tokenize text for searching."""
        if not text:
            return []
        
        # Convert to lowercase and split on non-alphanumeric characters
        tokens = re.findall(r'\b\w+\b', text.lower())
        
        # Remove stop words and short tokens
        tokens = [
            token for token in tokens
            if len(token) > 2 and token not in self.stop_words
        ]
        
        return tokens
    
    def fuzzy_match(
        self,
        query: str,
        text: str,
        threshold: float = 0.8
    ) -> Tuple[bool, float]:
        """Perform fuzzy string matching using advanced algorithms."""
        if not query or not text:
            return False, 0.0
        
        # Quick exact match check
        if query == text:
            return True, 1.0
        
        # Normalize text for better matching
        norm_query = self.fuzzy_matcher.normalize_text(query)
        norm_text = self.fuzzy_matcher.normalize_text(text)
        
        # Use combined similarity score
        scores = [
            self.fuzzy_matcher.levenshtein_similarity(norm_query, norm_text),
            self.fuzzy_matcher.jaro_winkler_similarity(norm_query, norm_text),
            self.fuzzy_matcher.ngram_similarity(norm_query, norm_text)
        ]
        
        # Check phonetic match
        if self.fuzzy_matcher.soundex(query) == self.fuzzy_matcher.soundex(text):
            scores.append(0.9)  # High score for phonetic match
        
        similarity = sum(scores) / len(scores)
        
        return similarity >= threshold, similarity
    
    
    def _get_matched_fields(
        self,
        item: Dict[str, Any],
        query_tokens: List[str]
    ) -> List[str]:
        """Get list of fields that match the query."""
        matched_fields = []
        
        for field, value in item.items():
            if not isinstance(value, str):
                continue
            
            field_text = value.lower()
            field_tokens = self.tokenize(field_text)
            
            # Check if any query token matches
            for query_token in query_tokens:
                if query_token in field_tokens:
                    matched_fields.append(field)
                    break
                else:
                    # Check fuzzy matches
                    for field_token in field_tokens:
                        is_match, _ = self.fuzzy_match(
                            query_token, field_token, 0.8
                        )
                        if is_match:
                            matched_fields.append(field)
                            break
        
        return matched_fields
    
    def _merge_overlapping_positions(
        self,
        positions: List[Tuple[int, int]]
    ) -> List[Tuple[int, int]]:
        """Merge overlapping position ranges."""
        if not positions:
            return []
        
        merged = [positions[0]]
        
        for start, end in positions[1:]:
            last_start, last_end = merged[-1]
            
            if start <= last_end:
                # Overlapping, merge them
                merged[-1] = (last_start, max(last_end, end))
            else:
                # Not overlapping, add as new range
                merged.append((start, end))
        
        return merged
    
    def _generate_explanation(
        self,
        score: float,
        matched_fields: List[str],
        mode: SearchMode
    ) -> str:
        """Generate explanation for search result."""
        if score >= 0.9:
            quality = "Excellent"
        elif score >= 0.7:
            quality = "Good"
        elif score >= 0.5:
            quality = "Fair"
        else:
            quality = "Weak"
        
        field_list = ", ".join(matched_fields) if matched_fields else "none"
        
        return (
            f"{quality} match (score: {score:.2f}) - "
            f"Matched fields: {field_list} - "
            f"Search mode: {mode.value}"
        )