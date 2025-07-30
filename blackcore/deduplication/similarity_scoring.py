"""
Similarity Scoring System

Advanced fuzzy matching and similarity calculation algorithms optimized for
intelligence data with support for multiple string similarity metrics.
"""

import re
import logging
from typing import Dict, List, Any
from dataclasses import dataclass
import difflib

# Try to import advanced string matching libraries
try:
    from fuzzywuzzy import fuzz
    from fuzzywuzzy import process

    FUZZYWUZZY_AVAILABLE = True
except ImportError:
    FUZZYWUZZY_AVAILABLE = False
    logging.warning("fuzzywuzzy not available - using basic string matching")

try:
    import jellyfish

    JELLYFISH_AVAILABLE = True
except ImportError:
    JELLYFISH_AVAILABLE = False
    logging.warning("jellyfish not available - some phonetic matching disabled")

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceThresholds:
    """Confidence thresholds for different match types."""

    exact_match: float = 100.0
    high_confidence: float = 90.0
    medium_confidence: float = 70.0
    low_confidence: float = 50.0
    no_match: float = 30.0


class SimilarityScorer:
    """
    Advanced similarity scoring with multiple algorithms.

    Combines various string similarity metrics to provide robust matching
    for intelligence data including names, organizations, and locations.
    """

    def __init__(self):
        """Initialize the similarity scorer."""
        self.name_patterns = self._load_name_patterns()
        self.org_abbreviations = self._load_organization_abbreviations()
        self.location_normalizations = self._load_location_normalizations()

    def _load_name_patterns(self) -> Dict[str, List[str]]:
        """Load common name variation patterns."""
        return {
            "nicknames": {
                "anthony": ["tony", "ant"],
                "david": ["dave", "davy"],
                "peter": ["pete", "pier"],
                "robert": ["rob", "bob", "bobby"],
                "william": ["will", "bill", "billy"],
                "richard": ["rick", "dick", "rich"],
                "elizabeth": ["liz", "beth", "betty"],
                "catherine": ["cat", "cath", "kate", "katie"],
                "michael": ["mike", "mick"],
                "christopher": ["chris"],
                "patricia": ["pat", "patty", "trish"],
            },
            "titles": ["mr", "mrs", "ms", "dr", "prof", "sir", "lady", "lord"],
            "suffixes": ["jr", "sr", "ii", "iii", "phd", "md", "esq"],
        }

    def _load_organization_abbreviations(self) -> Dict[str, List[str]]:
        """Load common organization abbreviation patterns."""
        return {
            "council": ["tc", "cc", "dc", "council"],
            "committee": ["cttee", "comm", "committee"],
            "association": ["assoc", "assn", "association"],
            "society": ["soc", "society"],
            "company": ["co", "corp", "ltd", "limited", "inc", "company"],
            "government": ["gov", "govt", "government"],
            "department": ["dept", "dep", "department"],
            "authority": ["auth", "authority"],
        }

    def _load_location_normalizations(self) -> Dict[str, List[str]]:
        """Load location normalization patterns."""
        return {
            "street": ["st", "street", "str"],
            "road": ["rd", "road"],
            "avenue": ["ave", "avenue"],
            "place": ["pl", "place"],
            "court": ["ct", "court"],
            "drive": ["dr", "drive"],
            "lane": ["ln", "lane"],
            "way": ["way"],
            "close": ["cl", "close"],
        }

    def calculate_similarity(
        self,
        entity_a: Dict[str, Any],
        entity_b: Dict[str, Any],
        comparison_fields: List[str],
    ) -> Dict[str, float]:
        """
        Calculate comprehensive similarity scores between two entities.

        Args:
            entity_a: First entity to compare
            entity_b: Second entity to compare
            comparison_fields: List of fields to compare

        Returns:
            Dictionary of similarity scores for each field and overall metrics
        """
        scores = {}

        for field in comparison_fields:
            value_a = str(entity_a.get(field, "")).strip().lower()
            value_b = str(entity_b.get(field, "")).strip().lower()

            if not value_a or not value_b:
                scores[field] = 0.0
                continue

            # Calculate multiple similarity metrics
            field_scores = self._calculate_field_similarity(value_a, value_b, field)
            scores[field] = field_scores

        # Calculate weighted overall score
        scores["overall"] = self._calculate_weighted_score(scores, comparison_fields)

        return scores

    def _calculate_field_similarity(
        self, value_a: str, value_b: str, field_name: str
    ) -> Dict[str, float]:
        """Calculate multiple similarity metrics for a single field."""
        scores = {}

        # Exact match
        scores["exact"] = 100.0 if value_a == value_b else 0.0

        # Basic string similarity
        scores["difflib"] = (
            difflib.SequenceMatcher(None, value_a, value_b).ratio() * 100
        )

        # Advanced fuzzy matching (if available)
        if FUZZYWUZZY_AVAILABLE:
            scores["ratio"] = fuzz.ratio(value_a, value_b)
            scores["partial_ratio"] = fuzz.partial_ratio(value_a, value_b)
            scores["token_sort_ratio"] = fuzz.token_sort_ratio(value_a, value_b)
            scores["token_set_ratio"] = fuzz.token_set_ratio(value_a, value_b)
        else:
            # Fallback implementations
            scores["ratio"] = scores["difflib"]
            scores["partial_ratio"] = self._partial_similarity(value_a, value_b)
            scores["token_sort_ratio"] = self._token_sort_similarity(value_a, value_b)
            scores["token_set_ratio"] = self._token_set_similarity(value_a, value_b)

        # Phonetic similarity (if available)
        if JELLYFISH_AVAILABLE:
            try:
                scores["soundex"] = (
                    100.0
                    if jellyfish.soundex(value_a) == jellyfish.soundex(value_b)
                    else 0.0
                )
                scores["metaphone"] = (
                    100.0
                    if jellyfish.metaphone(value_a) == jellyfish.metaphone(value_b)
                    else 0.0
                )
            except:
                scores["soundex"] = 0.0
                scores["metaphone"] = 0.0
        else:
            scores["soundex"] = self._basic_soundex_similarity(value_a, value_b)
            scores["metaphone"] = 0.0

        # Field-specific similarity
        if "name" in field_name.lower():
            scores["name_specific"] = self._calculate_name_similarity(value_a, value_b)
        elif "organization" in field_name.lower():
            scores["organization_specific"] = self._calculate_organization_similarity(
                value_a, value_b
            )
        elif any(loc in field_name.lower() for loc in ["address", "location", "place"]):
            scores["location_specific"] = self._calculate_location_similarity(
                value_a, value_b
            )
        else:
            scores["generic"] = scores["token_set_ratio"]

        # Calculate composite score for this field
        scores["composite"] = self._calculate_composite_field_score(scores, field_name)

        return scores

    def _partial_similarity(self, a: str, b: str) -> float:
        """Basic partial string similarity."""
        if not a or not b:
            return 0.0

        # Find longest common substring
        matcher = difflib.SequenceMatcher(None, a, b)
        match = matcher.find_longest_match(0, len(a), 0, len(b))

        if match.size == 0:
            return 0.0

        return (match.size * 2.0 / (len(a) + len(b))) * 100

    def _token_sort_similarity(self, a: str, b: str) -> float:
        """Token-based similarity with sorting."""
        tokens_a = sorted(a.split())
        tokens_b = sorted(b.split())

        return (
            difflib.SequenceMatcher(
                None, " ".join(tokens_a), " ".join(tokens_b)
            ).ratio()
            * 100
        )

    def _token_set_similarity(self, a: str, b: str) -> float:
        """Token set similarity."""
        tokens_a = set(a.split())
        tokens_b = set(b.split())

        intersection = len(tokens_a & tokens_b)
        union = len(tokens_a | tokens_b)

        return (intersection / union * 100) if union > 0 else 0.0

    def _basic_soundex_similarity(self, a: str, b: str) -> float:
        """Basic soundex-like similarity."""

        def simple_soundex(s):
            # Very basic soundex approximation
            s = re.sub(r"[^a-z]", "", s.lower())
            if not s:
                return ""
            result = s[0]
            for char in s[1:]:
                if char in "bfpv":
                    result += "1"
                elif char in "cgjkqsxz":
                    result += "2"
                elif char in "dt":
                    result += "3"
                elif char == "l":
                    result += "4"
                elif char in "mn":
                    result += "5"
                elif char == "r":
                    result += "6"
            return result[:4].ljust(4, "0")

        return 100.0 if simple_soundex(a) == simple_soundex(b) else 0.0

    def _calculate_name_similarity(self, name_a: str, name_b: str) -> float:
        """Calculate similarity specifically for person names."""
        # Handle common name variations
        normalized_a = self._normalize_name(name_a)
        normalized_b = self._normalize_name(name_b)

        if normalized_a == normalized_b:
            return 100.0

        # Check for nickname patterns
        if self._are_name_variants(normalized_a, normalized_b):
            return 95.0

        # Token-based comparison for names with different word orders
        tokens_a = set(normalized_a.split())
        tokens_b = set(normalized_b.split())

        if tokens_a & tokens_b:  # Any overlap
            overlap = len(tokens_a & tokens_b)
            total = len(tokens_a | tokens_b)
            return (overlap / total) * 100

        return 0.0

    def _normalize_name(self, name: str) -> str:
        """Normalize a person name for comparison."""
        name = name.lower().strip()

        # Remove titles and suffixes
        for title in self.name_patterns["titles"]:
            name = re.sub(rf"\b{title}\.?\b", "", name)

        for suffix in self.name_patterns["suffixes"]:
            name = re.sub(rf"\b{suffix}\.?\b", "", name)

        # Clean up whitespace
        name = re.sub(r"\s+", " ", name).strip()

        return name

    def _are_name_variants(self, name_a: str, name_b: str) -> bool:
        """Check if two names are likely variants (nicknames, etc.)."""
        tokens_a = name_a.split()
        tokens_b = name_b.split()

        for token_a in tokens_a:
            for token_b in tokens_b:
                # Check nickname patterns
                for full_name, nicknames in self.name_patterns["nicknames"].items():
                    if (
                        (token_a == full_name and token_b in nicknames)
                        or (token_b == full_name and token_a in nicknames)
                        or (token_a in nicknames and token_b in nicknames)
                    ):
                        return True

        return False

    def _calculate_organization_similarity(self, org_a: str, org_b: str) -> float:
        """Calculate similarity specifically for organization names."""
        # Handle abbreviations and common variations
        normalized_a = self._normalize_organization(org_a)
        normalized_b = self._normalize_organization(org_b)

        if normalized_a == normalized_b:
            return 100.0

        # Check for abbreviation patterns
        if self._are_organization_variants(normalized_a, normalized_b):
            return 90.0

        # Token-based comparison
        tokens_a = set(normalized_a.split())
        tokens_b = set(normalized_b.split())

        if tokens_a & tokens_b:
            overlap = len(tokens_a & tokens_b)
            total = len(tokens_a | tokens_b)
            return (overlap / total) * 100

        return 0.0

    def _normalize_organization(self, org: str) -> str:
        """Normalize organization name for comparison."""
        org = org.lower().strip()

        # Remove common punctuation
        org = re.sub(r"[.,\-()&]", " ", org)

        # Normalize common abbreviations
        for full_form, abbrevs in self.org_abbreviations.items():
            for abbrev in abbrevs:
                org = re.sub(rf"\b{re.escape(abbrev)}\b", full_form, org)

        # Clean up whitespace
        org = re.sub(r"\s+", " ", org).strip()

        return org

    def _are_organization_variants(self, org_a: str, org_b: str) -> bool:
        """Check if two organizations are likely the same entity."""
        # Check for abbreviation patterns
        words_a = org_a.split()
        words_b = org_b.split()

        # Check if one could be an abbreviation of the other
        if len(words_a) == 1 and len(words_b) > 1:
            return self._could_be_abbreviation(words_a[0], words_b)
        elif len(words_b) == 1 and len(words_a) > 1:
            return self._could_be_abbreviation(words_b[0], words_a)

        return False

    def _could_be_abbreviation(self, abbrev: str, full_words: List[str]) -> bool:
        """Check if a string could be an abbreviation of a list of words."""
        if len(abbrev) != len(full_words):
            return False

        for i, word in enumerate(full_words):
            if not word.startswith(abbrev[i].lower()):
                return False

        return True

    def _calculate_location_similarity(self, loc_a: str, loc_b: str) -> float:
        """Calculate similarity for location/address fields."""
        # Normalize addresses
        normalized_a = self._normalize_location(loc_a)
        normalized_b = self._normalize_location(loc_b)

        if normalized_a == normalized_b:
            return 100.0

        # Token-based comparison
        tokens_a = set(normalized_a.split())
        tokens_b = set(normalized_b.split())

        if tokens_a & tokens_b:
            overlap = len(tokens_a & tokens_b)
            total = len(tokens_a | tokens_b)
            return (overlap / total) * 100

        return 0.0

    def _normalize_location(self, location: str) -> str:
        """Normalize location/address for comparison."""
        location = location.lower().strip()

        # Normalize street types
        for full_form, abbrevs in self.location_normalizations.items():
            for abbrev in abbrevs:
                location = re.sub(rf"\b{re.escape(abbrev)}\.?\b", full_form, location)

        # Remove common punctuation
        location = re.sub(r"[.,\-#]", " ", location)

        # Clean up whitespace
        location = re.sub(r"\s+", " ", location).strip()

        return location

    def _calculate_composite_field_score(
        self, scores: Dict[str, float], field_name: str
    ) -> float:
        """Calculate composite similarity score for a field."""
        # Weight different similarity metrics based on field type
        if "name" in field_name.lower():
            weights = {
                "exact": 0.3,
                "name_specific": 0.3,
                "token_set_ratio": 0.2,
                "soundex": 0.1,
                "ratio": 0.1,
            }
        elif "organization" in field_name.lower():
            weights = {
                "exact": 0.25,
                "organization_specific": 0.35,
                "token_set_ratio": 0.25,
                "ratio": 0.15,
            }
        else:
            weights = {
                "exact": 0.2,
                "token_set_ratio": 0.3,
                "ratio": 0.3,
                "partial_ratio": 0.2,
            }

        # Calculate weighted average
        total_weight = 0
        weighted_sum = 0

        for metric, weight in weights.items():
            if metric in scores:
                weighted_sum += scores[metric] * weight
                total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def _calculate_weighted_score(
        self, field_scores: Dict[str, Any], comparison_fields: List[str]
    ) -> float:
        """Calculate overall weighted similarity score."""
        # Field importance weights
        field_weights = {
            "name": 0.4,
            "full_name": 0.4,
            "organization_name": 0.4,
            "email": 0.3,
            "phone": 0.2,
            "address": 0.15,
            "organization": 0.2,
            "description": 0.1,
            "notes": 0.05,
        }

        total_weight = 0
        weighted_sum = 0

        for field in comparison_fields:
            if field in field_scores and isinstance(field_scores[field], dict):
                composite_score = field_scores[field].get("composite", 0.0)

                # Determine field weight
                weight = 0.1  # default weight
                for pattern, w in field_weights.items():
                    if pattern in field.lower():
                        weight = w
                        break

                weighted_sum += composite_score * weight
                total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0
