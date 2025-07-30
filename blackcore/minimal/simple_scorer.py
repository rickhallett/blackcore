"""
Simple Similarity Scorer for MVP Deduplication

A lightweight similarity scoring module for the MVP that provides basic
name and entity matching without complex dependencies.
"""

import re
from typing import Dict, Tuple
import difflib


class SimpleScorer:
    """Simple similarity scoring for MVP deduplication."""

    def __init__(self):
        """Initialize the simple scorer with basic patterns."""
        # Common nickname mappings
        self.nicknames = {
            "anthony": ["tony", "ant"],
            "david": ["dave", "davy"],
            "peter": ["pete"],
            "robert": ["rob", "bob", "bobby"],
            "william": ["will", "bill", "billy"],
            "richard": ["rick", "dick", "rich"],
            "elizabeth": ["liz", "beth", "betty"],
            "catherine": ["cat", "cath", "kate", "katie"],
            "michael": ["mike", "mick"],
            "christopher": ["chris"],
            "patricia": ["pat", "patty", "trish"],
            "james": ["jim", "jimmy"],
            "john": ["johnny", "jack"],
            "jennifer": ["jen", "jenny"],
            "jessica": ["jess", "jessie"],
            "samuel": ["sam", "sammy"],
            "alexander": ["alex", "al"],
            "benjamin": ["ben", "benny"],
            "nicholas": ["nick", "nicky"],
            "matthew": ["matt", "matty"],
            "joseph": ["joe", "joey"],
            "daniel": ["dan", "danny"],
            "thomas": ["tom", "tommy"],
            "charles": ["charlie", "chuck"],
            "andrew": ["andy", "drew"],
        }

        # Build reverse mapping
        self.nickname_to_full = {}
        for full_name, nicknames in self.nicknames.items():
            for nickname in nicknames:
                self.nickname_to_full[nickname] = full_name

        # Common titles to remove
        self.titles = {"mr", "mrs", "ms", "dr", "prof", "sir", "lady", "lord"}

        # Common suffixes to remove
        self.suffixes = {"jr", "sr", "ii", "iii", "iv", "phd", "md", "esq"}

    def normalize_name(self, name: str) -> str:
        """Normalize a name for comparison.

        Args:
            name: Name to normalize

        Returns:
            Normalized name (lowercase, no punctuation, no titles)
        """
        # Convert to lowercase
        normalized = name.lower().strip()

        # Remove punctuation
        normalized = re.sub(r"[^\w\s]", " ", normalized)

        # Split into parts
        parts = normalized.split()

        # Remove titles and suffixes
        parts = [p for p in parts if p not in self.titles and p not in self.suffixes]

        # Join back
        return " ".join(parts)

    def score_names(self, name1: str, name2: str) -> float:
        """Calculate similarity score between two names.

        Args:
            name1: First name
            name2: Second name

        Returns:
            Similarity score (0-100)
        """
        # Exact match
        if name1.lower().strip() == name2.lower().strip():
            return 100.0

        # Normalize names
        norm1 = self.normalize_name(name1)
        norm2 = self.normalize_name(name2)

        # Normalized exact match
        if norm1 == norm2:
            return 95.0

        # Check nickname matches
        nickname_score = self._check_nickname_match(norm1, norm2)
        if nickname_score > 0:
            return nickname_score

        # Check partial matches (last name match with different first name)
        partial_score = self._check_partial_match(norm1, norm2)
        if partial_score > 0:
            return partial_score

        # Fuzzy match using difflib
        ratio = difflib.SequenceMatcher(None, norm1, norm2).ratio()
        return ratio * 100

    def _check_nickname_match(self, name1: str, name2: str) -> float:
        """Check if names match via nickname mapping.

        Args:
            name1: First normalized name
            name2: Second normalized name

        Returns:
            Score (90 if nickname match, 0 otherwise)
        """
        parts1 = name1.split()
        parts2 = name2.split()

        if not parts1 or not parts2:
            return 0.0

        # Check first name nickname match
        first1, first2 = parts1[0], parts2[0]

        # Direct nickname match
        if first1 in self.nicknames and first2 in self.nicknames[first1]:
            # Check if rest of name matches
            if " ".join(parts1[1:]) == " ".join(parts2[1:]):
                return 90.0

        # Reverse nickname match
        if first2 in self.nicknames and first1 in self.nicknames[first2]:
            if " ".join(parts1[1:]) == " ".join(parts2[1:]):
                return 90.0

        # Check if one is nickname of the other
        if first1 in self.nickname_to_full and self.nickname_to_full[first1] == first2:
            if " ".join(parts1[1:]) == " ".join(parts2[1:]):
                return 90.0

        if first2 in self.nickname_to_full and self.nickname_to_full[first2] == first1:
            if " ".join(parts1[1:]) == " ".join(parts2[1:]):
                return 90.0

        return 0.0

    def _check_partial_match(self, name1: str, name2: str) -> float:
        """Check for partial name matches (e.g., same last name).

        Args:
            name1: First normalized name
            name2: Second normalized name

        Returns:
            Score based on partial match strength
        """
        parts1 = name1.split()
        parts2 = name2.split()

        # Need at least 2 parts for meaningful comparison
        if len(parts1) < 2 or len(parts2) < 2:
            return 0.0

        # Check last name match
        if parts1[-1] == parts2[-1]:
            # Same last name, different first name
            # Could be family members - lower confidence
            return 60.0

        return 0.0

    def score_entities(
        self, entity1: Dict, entity2: Dict, entity_type: str = "person"
    ) -> Tuple[float, str]:
        """Score similarity between two entities.

        Args:
            entity1: First entity properties
            entity2: Second entity properties
            entity_type: Type of entity (person, organization)

        Returns:
            Tuple of (score, match_reason)
        """
        if entity_type == "person":
            return self._score_person_entities(entity1, entity2)
        elif entity_type == "organization":
            return self._score_organization_entities(entity1, entity2)
        else:
            # Generic name comparison
            name1 = entity1.get("name", "")
            name2 = entity2.get("name", "")
            score = self.score_names(name1, name2)
            return score, "name match"

    def _score_person_entities(self, person1: Dict, person2: Dict) -> Tuple[float, str]:
        """Score similarity between two person entities.

        Args:
            person1: First person's properties
            person2: Second person's properties

        Returns:
            Tuple of (score, match_reason)
        """
        # Start with name comparison
        name1 = person1.get("name", "")
        name2 = person2.get("name", "")
        name_score = self.score_names(name1, name2)

        # Check for exact email match
        email1 = person1.get("email", "").lower().strip()
        email2 = person2.get("email", "").lower().strip()
        if email1 and email2 and email1 == email2:
            # Email match is very strong signal
            return 95.0, "email match"

        # Check for exact phone match
        phone1 = self._normalize_phone(person1.get("phone", ""))
        phone2 = self._normalize_phone(person2.get("phone", ""))
        if phone1 and phone2 and phone1 == phone2:
            # Phone match is strong signal
            return 92.0, "phone match"

        # High name match
        if name_score >= 90:
            return name_score, "name match"

        # Medium name match with same organization
        if name_score >= 60:
            org1 = person1.get("organization", "").lower().strip()
            org2 = person2.get("organization", "").lower().strip()
            if org1 and org2 and org1 == org2:
                # Boost score for same organization
                return min(name_score + 15, 90.0), "name + organization match"

        return name_score, "name similarity"

    def _score_organization_entities(self, org1: Dict, org2: Dict) -> Tuple[float, str]:
        """Score similarity between two organization entities.

        Args:
            org1: First organization's properties
            org2: Second organization's properties

        Returns:
            Tuple of (score, match_reason)
        """
        name1 = org1.get("name", "")
        name2 = org2.get("name", "")

        # Exact match before normalization
        if name1.lower().strip() == name2.lower().strip():
            return 100.0, "exact name match"

        # Normalize organization names
        norm1 = self._normalize_org_name(name1)
        norm2 = self._normalize_org_name(name2)

        # Exact match after normalization
        if norm1 == norm2:
            return 95.0, "normalized name match"

        # Check website match
        website1 = self._normalize_url(org1.get("website", ""))
        website2 = self._normalize_url(org2.get("website", ""))
        if website1 and website2 and website1 == website2:
            return 93.0, "website match"

        # Fuzzy match
        ratio = difflib.SequenceMatcher(None, norm1, norm2).ratio()
        return ratio * 100, "name similarity"

    def _normalize_org_name(self, name: str) -> str:
        """Normalize organization name for comparison.

        Args:
            name: Organization name

        Returns:
            Normalized name
        """
        normalized = name.lower().strip()

        # Remove common suffixes
        suffixes = [
            "inc",
            "incorporated",
            "corp",
            "corporation",
            "co",
            "company",
            "ltd",
            "limited",
            "llc",
            "plc",
            "gmbh",
        ]

        for suffix in suffixes:
            normalized = re.sub(rf"\b{suffix}\b\.?", "", normalized)

        # Remove punctuation
        normalized = re.sub(r"[^\w\s]", " ", normalized)

        # Remove extra spaces
        normalized = " ".join(normalized.split())

        return normalized

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number for comparison.

        Args:
            phone: Phone number

        Returns:
            Normalized phone (digits only)
        """
        return re.sub(r"[^\d]", "", phone)

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for comparison.

        Args:
            url: Website URL

        Returns:
            Normalized URL (domain only)
        """
        # Remove protocol
        url = re.sub(r"^https?://", "", url.lower())
        # Remove www
        url = re.sub(r"^www\.", "", url)
        # Remove trailing slash
        url = url.rstrip("/")
        # Extract domain only
        url = url.split("/")[0]
        return url
