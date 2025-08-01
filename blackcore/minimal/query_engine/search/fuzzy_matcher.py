"""Advanced fuzzy matching algorithms for text search.

This module implements various fuzzy matching techniques including:
- Levenshtein distance
- Jaro-Winkler similarity
- Soundex phonetic matching
- Metaphone phonetic matching
- N-gram similarity
"""

import re
from typing import List, Tuple, Optional, Set
from collections import Counter
import unicodedata


class FuzzyMatcher:
    """Advanced fuzzy string matching algorithms."""
    
    def __init__(self):
        self.soundex_cache = {}
        self.metaphone_cache = {}
    
    def levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return self.levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def levenshtein_similarity(self, s1: str, s2: str) -> float:
        """Calculate Levenshtein similarity (0 to 1)."""
        if not s1 and not s2:
            return 1.0
        max_len = max(len(s1), len(s2))
        if max_len == 0:
            return 1.0
        distance = self.levenshtein_distance(s1, s2)
        return 1 - (distance / max_len)
    
    def jaro_similarity(self, s1: str, s2: str) -> float:
        """Calculate Jaro similarity between two strings."""
        if s1 == s2:
            return 1.0
        
        len1, len2 = len(s1), len(s2)
        if len1 == 0 or len2 == 0:
            return 0.0
        
        # Maximum allowed distance
        match_distance = max(len1, len2) // 2 - 1
        if match_distance < 0:
            match_distance = 0
        
        # Initialize arrays
        s1_matches = [False] * len1
        s2_matches = [False] * len2
        
        matches = 0
        transpositions = 0
        
        # Find matches
        for i in range(len1):
            start = max(0, i - match_distance)
            end = min(i + match_distance + 1, len2)
            
            for j in range(start, end):
                if s2_matches[j] or s1[i] != s2[j]:
                    continue
                s1_matches[i] = True
                s2_matches[j] = True
                matches += 1
                break
        
        if matches == 0:
            return 0.0
        
        # Count transpositions
        k = 0
        for i in range(len1):
            if not s1_matches[i]:
                continue
            while not s2_matches[k]:
                k += 1
            if s1[i] != s2[k]:
                transpositions += 1
            k += 1
        
        return (matches / len1 + matches / len2 + 
                (matches - transpositions / 2) / matches) / 3
    
    def jaro_winkler_similarity(
        self, 
        s1: str, 
        s2: str, 
        prefix_scale: float = 0.1
    ) -> float:
        """Calculate Jaro-Winkler similarity with prefix bonus."""
        jaro_sim = self.jaro_similarity(s1, s2)
        
        # Find common prefix length (up to 4 chars)
        prefix_len = 0
        for i in range(min(len(s1), len(s2), 4)):
            if s1[i] == s2[i]:
                prefix_len += 1
            else:
                break
        
        return jaro_sim + prefix_len * prefix_scale * (1 - jaro_sim)
    
    def soundex(self, word: str) -> str:
        """Generate Soundex code for phonetic matching."""
        if not word:
            return ""
        
        # Check cache
        if word in self.soundex_cache:
            return self.soundex_cache[word]
        
        # Convert to uppercase and keep only letters
        word = ''.join(c for c in word.upper() if c.isalpha())
        if not word:
            return ""
        
        # Soundex mappings
        soundex_map = {
            'B': '1', 'F': '1', 'P': '1', 'V': '1',
            'C': '2', 'G': '2', 'J': '2', 'K': '2', 
            'Q': '2', 'S': '2', 'X': '2', 'Z': '2',
            'D': '3', 'T': '3',
            'L': '4',
            'M': '5', 'N': '5',
            'R': '6'
        }
        
        # Keep first letter
        code = word[0]
        
        # Map remaining letters
        for char in word[1:]:
            if char in soundex_map:
                digit = soundex_map[char]
                # Avoid consecutive duplicates
                if not code or code[-1] != digit:
                    code += digit
        
        # Remove vowels except first letter
        if len(code) > 1:
            code = code[0] + ''.join(c for c in code[1:] if c != '0')
        
        # Pad with zeros or truncate to 4 characters
        code = (code + '000')[:4]
        
        self.soundex_cache[word] = code
        return code
    
    def metaphone(self, word: str, max_length: int = 4) -> str:
        """Generate Metaphone code for phonetic matching."""
        if not word:
            return ""
        
        # Check cache
        if word in self.metaphone_cache:
            return self.metaphone_cache[word]
        
        # Preprocess
        word = word.upper()
        word = ''.join(c for c in word if c.isalpha())
        
        if not word:
            return ""
        
        # Metaphone rules (simplified)
        result = []
        i = 0
        
        while i < len(word) and len(result) < max_length:
            char = word[i]
            next_char = word[i + 1] if i + 1 < len(word) else ''
            prev_char = word[i - 1] if i > 0 else ''
            
            # Apply Metaphone rules
            if char in 'AEIOU':
                if i == 0:
                    result.append(char)
            elif char == 'B':
                if i + 1 < len(word) or word[i - 1] != 'M':
                    result.append('B')
            elif char == 'C':
                if next_char == 'H':
                    result.append('X')
                    i += 1
                elif next_char in 'IEY':
                    result.append('S')
                else:
                    result.append('K')
            elif char == 'D':
                if next_char == 'G' and i + 2 < len(word) and word[i + 2] in 'IEY':
                    result.append('J')
                    i += 1
                else:
                    result.append('T')
            elif char == 'G':
                if next_char == 'H':
                    if i > 0 and word[i - 1] not in 'AEIOU':
                        result.append('K')
                    i += 1
                elif next_char in 'IEY':
                    result.append('J')
                else:
                    result.append('K')
            elif char == 'H':
                if i == 0 or word[i - 1] in 'AEIOU':
                    result.append('H')
            elif char in 'FJLMNR':
                result.append(char)
            elif char == 'K':
                if i == 0 or word[i - 1] != 'C':
                    result.append('K')
            elif char == 'P':
                if next_char == 'H':
                    result.append('F')
                    i += 1
                else:
                    result.append('P')
            elif char == 'Q':
                result.append('K')
            elif char == 'S':
                if next_char == 'H':
                    result.append('X')
                    i += 1
                elif next_char == 'I' and i + 2 < len(word) and word[i + 2] in 'AO':
                    result.append('X')
                else:
                    result.append('S')
            elif char == 'T':
                if next_char == 'H':
                    result.append('0')  # Theta
                    i += 1
                elif next_char == 'I' and i + 2 < len(word) and word[i + 2] in 'AO':
                    result.append('X')
                else:
                    result.append('T')
            elif char == 'V':
                result.append('F')
            elif char == 'W':
                if prev_char in 'AEIOU':
                    result.append('W')
            elif char == 'X':
                result.append('KS')
            elif char == 'Y':
                if prev_char in 'AEIOU':
                    result.append('Y')
            elif char == 'Z':
                result.append('S')
            
            i += 1
        
        code = ''.join(result[:max_length])
        self.metaphone_cache[word] = code
        return code
    
    def ngram_similarity(self, s1: str, s2: str, n: int = 2) -> float:
        """Calculate n-gram similarity between two strings."""
        if not s1 or not s2:
            return 0.0
        if s1 == s2:
            return 1.0
        
        # Generate n-grams
        ngrams1 = self._generate_ngrams(s1, n)
        ngrams2 = self._generate_ngrams(s2, n)
        
        if not ngrams1 or not ngrams2:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = len(ngrams1 & ngrams2)
        union = len(ngrams1 | ngrams2)
        
        return intersection / union if union > 0 else 0.0
    
    def _generate_ngrams(self, text: str, n: int) -> Set[str]:
        """Generate n-grams from text."""
        if len(text) < n:
            return {text}
        
        ngrams = set()
        for i in range(len(text) - n + 1):
            ngrams.add(text[i:i + n])
        
        return ngrams
    
    def cosine_similarity(self, s1: str, s2: str) -> float:
        """Calculate cosine similarity between two strings based on character frequency."""
        if not s1 or not s2:
            return 0.0
        if s1 == s2:
            return 1.0
        
        # Count character frequencies
        counter1 = Counter(s1.lower())
        counter2 = Counter(s2.lower())
        
        # Calculate dot product
        dot_product = sum(counter1[char] * counter2[char] 
                         for char in counter1 if char in counter2)
        
        # Calculate magnitudes
        magnitude1 = sum(count ** 2 for count in counter1.values()) ** 0.5
        magnitude2 = sum(count ** 2 for count in counter2.values()) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def best_match(
        self, 
        query: str, 
        candidates: List[str], 
        threshold: float = 0.6,
        method: str = "combined"
    ) -> Optional[Tuple[str, float]]:
        """Find best matching candidate for query.
        
        Args:
            query: Query string
            candidates: List of candidate strings
            threshold: Minimum similarity threshold
            method: Matching method (levenshtein, jaro_winkler, soundex, combined)
            
        Returns:
            Tuple of (best_match, similarity) or None if no match above threshold
        """
        if not query or not candidates:
            return None
        
        best_candidate = None
        best_score = 0.0
        
        for candidate in candidates:
            if method == "levenshtein":
                score = self.levenshtein_similarity(query, candidate)
            elif method == "jaro_winkler":
                score = self.jaro_winkler_similarity(query, candidate)
            elif method == "soundex":
                score = 1.0 if self.soundex(query) == self.soundex(candidate) else 0.0
            else:  # combined
                scores = [
                    self.levenshtein_similarity(query, candidate),
                    self.jaro_winkler_similarity(query, candidate),
                    self.ngram_similarity(query, candidate),
                    1.0 if self.soundex(query) == self.soundex(candidate) else 0.0
                ]
                score = sum(scores) / len(scores)
            
            if score > best_score and score >= threshold:
                best_score = score
                best_candidate = candidate
        
        return (best_candidate, best_score) if best_candidate else None
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for better matching."""
        # Remove accents
        text = ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
        
        # Lowercase and remove extra whitespace
        text = ' '.join(text.lower().split())
        
        # Remove punctuation except apostrophes in words
        text = re.sub(r"[^\w\s'-]", ' ', text)
        text = re.sub(r"\s+'|'\s+", ' ', text)  # Remove standalone apostrophes
        
        return text.strip()