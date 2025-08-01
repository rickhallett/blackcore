"""Spell checking implementation for query correction.

This module provides spell checking and correction capabilities
for improving query accuracy.
"""

import re
from typing import List, Dict, Set, Optional, Tuple
from collections import Counter, defaultdict
from dataclasses import dataclass

from .interfaces import SpellChecker, SpellCorrection


class SimpleSpellChecker:
    """Basic spell checker using edit distance and frequency analysis."""
    
    def __init__(self):
        self.word_freq = self._load_default_dictionary()
        self.custom_words = set()
        self.alphabet = 'abcdefghijklmnopqrstuvwxyz'
    
    def check(self, text: str) -> List[SpellCorrection]:
        """Check spelling and suggest corrections."""
        corrections = []
        words = self._tokenize(text)
        
        for word, position in words:
            if not self._is_valid_word(word):
                # Find suggestions
                suggestions = self._get_suggestions(word)
                
                if suggestions:
                    correction = SpellCorrection(
                        original=word,
                        corrected=suggestions[0][0],
                        confidence=suggestions[0][1],
                        alternatives=suggestions[1:4]  # Top 3 alternatives
                    )
                    corrections.append(correction)
        
        return corrections
    
    def correct(self, text: str, auto_correct: bool = True) -> str:
        """Correct spelling in text."""
        if not auto_correct:
            return text
        
        corrections = self.check(text)
        corrected_text = text
        
        # Apply corrections from end to start to preserve positions
        for correction in reversed(corrections):
            if correction.confidence > 0.8:  # Only apply high-confidence corrections
                corrected_text = corrected_text.replace(
                    correction.original,
                    correction.corrected
                )
        
        return corrected_text
    
    def add_to_dictionary(self, words: List[str]) -> None:
        """Add words to custom dictionary."""
        for word in words:
            self.custom_words.add(word.lower())
    
    def _tokenize(self, text: str) -> List[Tuple[str, int]]:
        """Tokenize text into words with positions."""
        words = []
        
        # Find all word-like sequences
        for match in re.finditer(r'\b[a-zA-Z]+\b', text):
            words.append((match.group(), match.start()))
        
        return words
    
    def _is_valid_word(self, word: str) -> bool:
        """Check if word is valid (in dictionary or custom words)."""
        word_lower = word.lower()
        
        # Check custom dictionary
        if word_lower in self.custom_words:
            return True
        
        # Check main dictionary
        if word_lower in self.word_freq:
            return True
        
        # Check if it's a proper noun (capitalized)
        if word[0].isupper() and len(word) > 1:
            return True
        
        # Check if it's an acronym (all caps)
        if word.isupper() and len(word) > 1:
            return True
        
        return False
    
    def _get_suggestions(self, word: str) -> List[Tuple[str, float]]:
        """Get spelling suggestions for a word."""
        word_lower = word.lower()
        candidates = []
        
        # Generate candidates using edit distance
        candidates_1 = self._edits1(word_lower)
        candidates_2 = self._edits2(word_lower)
        
        # Score candidates
        scored_candidates = []
        
        for candidate in candidates_1:
            if candidate in self.word_freq:
                # Edit distance 1 - high confidence
                score = 0.9 * (self.word_freq[candidate] / 100000)  # Normalize frequency
                scored_candidates.append((candidate, min(score, 0.95)))
        
        for candidate in candidates_2:
            if candidate in self.word_freq and candidate not in candidates_1:
                # Edit distance 2 - lower confidence
                score = 0.7 * (self.word_freq[candidate] / 100000)
                scored_candidates.append((candidate, min(score, 0.85)))
        
        # Sort by score
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Preserve original capitalization
        if word[0].isupper():
            scored_candidates = [
                (cand.capitalize(), score) for cand, score in scored_candidates
            ]
        
        return scored_candidates
    
    def _edits1(self, word: str) -> Set[str]:
        """Generate all edits that are one edit away from word."""
        letters = self.alphabet
        splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
        
        # Deletions
        deletes = [L + R[1:] for L, R in splits if R]
        
        # Transpositions
        transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R) > 1]
        
        # Replacements
        replaces = [L + c + R[1:] for L, R in splits if R for c in letters]
        
        # Insertions
        inserts = [L + c + R for L, R in splits for c in letters]
        
        return set(deletes + transposes + replaces + inserts)
    
    def _edits2(self, word: str) -> Set[str]:
        """Generate all edits that are two edits away from word."""
        return {e2 for e1 in self._edits1(word) for e2 in self._edits1(e1)}
    
    def _load_default_dictionary(self) -> Dict[str, int]:
        """Load default word frequency dictionary."""
        # Common English words with approximate frequencies
        # In production, this would load from a file
        return {
            "the": 1000000,
            "be": 900000,
            "to": 850000,
            "of": 800000,
            "and": 750000,
            "a": 700000,
            "in": 650000,
            "that": 600000,
            "have": 550000,
            "i": 500000,
            "it": 450000,
            "for": 400000,
            "not": 350000,
            "on": 300000,
            "with": 250000,
            "he": 200000,
            "as": 190000,
            "you": 180000,
            "do": 170000,
            "at": 160000,
            "this": 150000,
            "but": 140000,
            "his": 130000,
            "by": 120000,
            "from": 110000,
            "they": 100000,
            "we": 95000,
            "say": 90000,
            "her": 85000,
            "she": 80000,
            "or": 75000,
            "an": 70000,
            "will": 65000,
            "my": 60000,
            "one": 55000,
            "all": 50000,
            "would": 45000,
            "there": 40000,
            "their": 35000,
            # Common query words
            "find": 30000,
            "search": 28000,
            "show": 26000,
            "get": 24000,
            "list": 22000,
            "where": 20000,
            "who": 18000,
            "what": 16000,
            "when": 14000,
            "how": 12000,
            "people": 10000,
            "person": 9000,
            "organization": 8000,
            "company": 7000,
            "task": 6000,
            "document": 5000,
            "event": 4000,
            "related": 3000,
            "connected": 2500,
            "between": 2000,
            "relationship": 1500,
            "status": 1000,
            "created": 900,
            "updated": 800,
            "name": 700,
            "title": 600,
            "description": 500,
            "type": 400,
            "category": 300,
            "tag": 200,
            "priority": 100
        }


class ContextualSpellChecker(SimpleSpellChecker):
    """Advanced spell checker that considers context."""
    
    def __init__(self):
        super().__init__()
        self.bigram_freq = self._load_bigram_frequencies()
        self.domain_vocabularies = self._load_domain_vocabularies()
    
    def check_with_context(
        self,
        text: str,
        domain: Optional[str] = None
    ) -> List[SpellCorrection]:
        """Check spelling considering context and domain."""
        corrections = []
        words = self._tokenize(text)
        
        # Add domain vocabulary if specified
        domain_vocab = self.domain_vocabularies.get(domain, set())
        
        for i, (word, position) in enumerate(words):
            if not self._is_valid_word(word) and word.lower() not in domain_vocab:
                # Get context
                prev_word = words[i-1][0] if i > 0 else None
                next_word = words[i+1][0] if i < len(words)-1 else None
                
                # Find context-aware suggestions
                suggestions = self._get_contextual_suggestions(
                    word, prev_word, next_word, domain
                )
                
                if suggestions:
                    correction = SpellCorrection(
                        original=word,
                        corrected=suggestions[0][0],
                        confidence=suggestions[0][1],
                        alternatives=suggestions[1:4]
                    )
                    corrections.append(correction)
        
        return corrections
    
    def _get_contextual_suggestions(
        self,
        word: str,
        prev_word: Optional[str],
        next_word: Optional[str],
        domain: Optional[str]
    ) -> List[Tuple[str, float]]:
        """Get suggestions considering context."""
        # Get basic suggestions
        basic_suggestions = super()._get_suggestions(word)
        
        if not prev_word and not next_word:
            return basic_suggestions
        
        # Re-score based on context
        contextual_suggestions = []
        
        for suggestion, base_score in basic_suggestions:
            context_score = base_score
            
            # Check bigram frequencies
            if prev_word:
                bigram = f"{prev_word.lower()} {suggestion.lower()}"
                if bigram in self.bigram_freq:
                    context_score *= 1.2  # Boost score
            
            if next_word:
                bigram = f"{suggestion.lower()} {next_word.lower()}"
                if bigram in self.bigram_freq:
                    context_score *= 1.2  # Boost score
            
            # Check domain relevance
            if domain and suggestion.lower() in self.domain_vocabularies.get(domain, set()):
                context_score *= 1.3  # Domain boost
            
            contextual_suggestions.append((suggestion, min(context_score, 0.99)))
        
        # Re-sort by contextual score
        contextual_suggestions.sort(key=lambda x: x[1], reverse=True)
        
        return contextual_suggestions
    
    def _load_bigram_frequencies(self) -> Set[str]:
        """Load common bigram frequencies."""
        # Common bigrams in queries
        return {
            "find all", "search for", "show me", "get all",
            "list all", "find people", "find person", "find organization",
            "created by", "updated by", "assigned to", "related to",
            "connected with", "associated with", "owned by", "managed by",
            "sort by", "order by", "group by", "filter by",
            "greater than", "less than", "equal to", "not equal",
            "in progress", "on hold", "high priority", "low priority"
        }
    
    def _load_domain_vocabularies(self) -> Dict[str, Set[str]]:
        """Load domain-specific vocabularies."""
        return {
            "intelligence": {
                "transcript", "intelligence", "transgression", "agenda",
                "epic", "actionable", "evidence", "analysis", "brief"
            },
            "business": {
                "organization", "company", "corporation", "enterprise",
                "stakeholder", "executive", "manager", "revenue", "profit"
            },
            "technical": {
                "database", "query", "filter", "aggregate", "relation",
                "entity", "attribute", "index", "cache", "performance"
            }
        }