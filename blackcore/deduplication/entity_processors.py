"""
Entity-Specific Processors

Specialized processors for different entity types (People, Organizations, Events, etc.)
with domain-specific logic for identifying potential duplicates and calculating confidence scores.
"""

import logging
from typing import Dict, List, Any, Optional, Set
from abc import ABC, abstractmethod
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class BaseEntityProcessor(ABC):
    """Base class for entity-specific processors."""
    
    def __init__(self, entity_type: str):
        """Initialize the processor."""
        self.entity_type = entity_type
        self.comparison_fields = self.get_comparison_fields()
        self.primary_fields = self.get_primary_fields()
        
    @abstractmethod
    def get_comparison_fields(self) -> List[str]:
        """Get list of fields to compare for this entity type."""
        pass
        
    @abstractmethod
    def get_primary_fields(self) -> List[str]:
        """Get list of primary identifying fields."""
        pass
        
    @abstractmethod
    def is_potential_duplicate(self, entity_a: Dict[str, Any], entity_b: Dict[str, Any]) -> bool:
        """Quick pre-screening to identify potential duplicates."""
        pass
        
    @abstractmethod
    def calculate_confidence(self, similarity_scores: Dict[str, Any], entity_a: Dict[str, Any] = None, entity_b: Dict[str, Any] = None) -> float:
        """Calculate confidence score based on similarity scores."""
        pass
        
    def extract_key_tokens(self, text: str) -> Set[str]:
        """Extract key tokens from text for comparison."""
        if not text:
            return set()
            
        # Basic tokenization and cleaning
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        tokens = set(text.split())
        
        # Remove common stop words
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        tokens = tokens - stop_words
        
        return tokens


class PersonProcessor(BaseEntityProcessor):
    """Processor for People & Contacts entities."""
    
    def __init__(self):
        super().__init__("People & Contacts")
        
    def get_comparison_fields(self) -> List[str]:
        """Get fields to compare for people."""
        return [
            "Full Name",
            "Email", 
            "Phone",
            "Organization",
            "Role",
            "Address",
            "Notes"
        ]
        
    def get_primary_fields(self) -> List[str]:
        """Get primary identifying fields for people."""
        return ["Full Name", "Email", "Phone"]
        
    def is_potential_duplicate(self, person_a: Dict[str, Any], person_b: Dict[str, Any]) -> bool:
        """Quick pre-screening for potential person duplicates."""
        # Exact email match
        email_a = person_a.get("Email", "").strip().lower()
        email_b = person_b.get("Email", "").strip().lower()
        if email_a and email_b and email_a == email_b:
            return True
            
        # Phone number match
        phone_a = self._normalize_phone(person_a.get("Phone", ""))
        phone_b = self._normalize_phone(person_b.get("Phone", ""))
        if phone_a and phone_b and phone_a == phone_b:
            return True
            
        # Name similarity check
        name_a = person_a.get("Full Name", "").strip().lower()
        name_b = person_b.get("Full Name", "").strip().lower()
        
        if not name_a or not name_b:
            return False
            
        # Check for substantial name overlap
        tokens_a = self.extract_key_tokens(name_a)
        tokens_b = self.extract_key_tokens(name_b)
        
        if len(tokens_a) == 0 or len(tokens_b) == 0:
            return False
            
        overlap = len(tokens_a & tokens_b)
        min_tokens = min(len(tokens_a), len(tokens_b))
        
        # If substantial overlap, worth detailed analysis
        return overlap / min_tokens >= 0.6
        
    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number for comparison."""
        if not phone:
            return ""
            
        # Remove all non-digits
        digits = re.sub(r'\D', '', phone)
        
        # Handle UK numbers - remove country code if present
        if digits.startswith('44') and len(digits) == 13:
            digits = '0' + digits[2:]
        elif digits.startswith('0') and len(digits) == 11:
            pass  # Already in correct format
        elif len(digits) == 10:
            digits = '0' + digits  # Add leading zero
            
        return digits if len(digits) == 11 else ""
        
    def calculate_confidence(self, similarity_scores: Dict[str, Any], entity_a: Dict[str, Any] = None, entity_b: Dict[str, Any] = None) -> float:
        """Calculate confidence score for person matching."""
        # High weight on exact matches for key identifiers
        if self._has_exact_match(similarity_scores, ["Email", "Phone"]):
            return 95.0
            
        # Name-based confidence calculation
        name_score = self._get_field_score(similarity_scores, "Full Name")
        
        # Supporting evidence from other fields
        org_score = self._get_field_score(similarity_scores, "Organization")
        role_score = self._get_field_score(similarity_scores, "Role")
        
        # Weighted combination
        confidence = (name_score * 0.6) + (org_score * 0.2) + (role_score * 0.2)
        
        # Boost confidence if multiple supporting fields match
        supporting_matches = sum(1 for field in ["Organization", "Role", "Address"] 
                               if self._get_field_score(similarity_scores, field) > 70)
        
        if supporting_matches >= 2:
            confidence = min(confidence + 15, 100)
        elif supporting_matches == 1:
            confidence = min(confidence + 5, 100)
            
        return confidence
        
    def _has_exact_match(self, scores: Dict[str, Any], fields: List[str]) -> bool:
        """Check if any of the specified fields has an exact match."""
        for field in fields:
            if field in scores and isinstance(scores[field], dict):
                if scores[field].get("exact", 0) == 100:
                    return True
        return False
        
    def _get_field_score(self, scores: Dict[str, Any], field: str) -> float:
        """Get composite score for a specific field."""
        if field not in scores or not isinstance(scores[field], dict):
            return 0.0
        return scores[field].get("composite", 0.0)


class OrganizationProcessor(BaseEntityProcessor):
    """Processor for Organizations & Bodies entities."""
    
    def __init__(self):
        super().__init__("Organizations & Bodies")
        
    def get_comparison_fields(self) -> List[str]:
        """Get fields to compare for organizations."""
        return [
            "Organization Name",
            "Website",
            "Email",
            "Phone", 
            "Address",
            "Category",
            "Key People",
            "Notes"
        ]
        
    def get_primary_fields(self) -> List[str]:
        """Get primary identifying fields for organizations."""
        return ["Organization Name", "Website", "Email"]
        
    def is_potential_duplicate(self, org_a: Dict[str, Any], org_b: Dict[str, Any]) -> bool:
        """Quick pre-screening for potential organization duplicates."""
        # Exact website match
        website_a = self._normalize_website(org_a.get("Website", ""))
        website_b = self._normalize_website(org_b.get("Website", ""))
        if website_a and website_b and website_a == website_b:
            return True
            
        # Email domain match
        email_a = org_a.get("Email", "").strip().lower()
        email_b = org_b.get("Email", "").strip().lower()
        if email_a and email_b:
            domain_a = email_a.split('@')[-1] if '@' in email_a else ""
            domain_b = email_b.split('@')[-1] if '@' in email_b else ""
            if domain_a and domain_b and domain_a == domain_b:
                return True
                
        # Organization name similarity
        name_a = org_a.get("Organization Name", "").strip().lower()
        name_b = org_b.get("Organization Name", "").strip().lower()
        
        if not name_a or not name_b:
            return False
            
        # Check for abbreviation patterns
        if self._could_be_abbreviation(name_a, name_b):
            return True
            
        # Token overlap check
        tokens_a = self.extract_key_tokens(name_a)
        tokens_b = self.extract_key_tokens(name_b)
        
        if len(tokens_a) == 0 or len(tokens_b) == 0:
            return False
            
        overlap = len(tokens_a & tokens_b)
        union = len(tokens_a | tokens_b)
        
        return overlap / union >= 0.5
        
    def _normalize_website(self, website: str) -> str:
        """Normalize website URL for comparison."""
        if not website:
            return ""
            
        website = website.lower().strip()
        
        # Remove protocol
        website = re.sub(r'^https?://', '', website)
        
        # Remove www
        website = re.sub(r'^www\.', '', website)
        
        # Remove trailing slash
        website = website.rstrip('/')
        
        return website
        
    def _could_be_abbreviation(self, name_a: str, name_b: str) -> bool:
        """Check if one organization name could be an abbreviation of another."""
        words_a = name_a.split()
        words_b = name_b.split()
        
        # Check if one is much shorter (potential abbreviation)
        if len(words_a) == 1 and len(words_b) >= 2:
            return self._check_abbreviation_match(words_a[0], words_b)
        elif len(words_b) == 1 and len(words_a) >= 2:
            return self._check_abbreviation_match(words_b[0], words_a)
        
        # Check for common abbreviation patterns
        if self._check_common_abbreviations(name_a, name_b):
            return True
            
        return False
        
    def _check_abbreviation_match(self, abbrev: str, full_words: List[str]) -> bool:
        """Check if abbreviation matches full organization name."""
        if len(abbrev) < 2 or len(abbrev) > len(full_words):
            return False
            
        # Simple check: first letters of words
        first_letters = ''.join(word[0] for word in full_words if word)
        return abbrev.lower() == first_letters.lower()
        
    def _check_common_abbreviations(self, name_a: str, name_b: str) -> bool:
        """Check for common abbreviation patterns."""
        # Common patterns for councils and organizations
        patterns = [
            ("swanage town council", "stc"),
            ("town council", "tc"),
            ("city council", "cc"), 
            ("district council", "dc"),
            ("borough council", "bc"),
            ("parish council", "pc"),
            ("community council", "cc"),
            ("corporation", "corp"),
            ("company", "co"),
            ("limited", "ltd"),
            ("incorporated", "inc"),
            ("association", "assoc"),
            ("society", "soc"),
            ("committee", "cttee"),
            ("department", "dept"),
            ("government", "gov"),
            ("authority", "auth")
        ]
        
        name_a_lower = name_a.lower()
        name_b_lower = name_b.lower()
        
        for full_form, abbrev in patterns:
            # Check if one contains full form and other contains abbreviation
            if ((full_form in name_a_lower and abbrev in name_b_lower) or
                (full_form in name_b_lower and abbrev in name_a_lower)):
                return True
                
        return False
        
    def calculate_confidence(self, similarity_scores: Dict[str, Any], entity_a: Dict[str, Any] = None, entity_b: Dict[str, Any] = None) -> float:
        """Calculate confidence score for organization matching."""
        # High weight on exact matches for key identifiers
        if self._has_exact_match(similarity_scores, ["Website", "Email"]):
            return 95.0
            
        # Name-based confidence
        name_score = self._get_field_score(similarity_scores, "Organization Name")
        
        # Supporting evidence
        website_score = self._get_field_score(similarity_scores, "Website")
        email_score = self._get_field_score(similarity_scores, "Email")
        category_score = self._get_field_score(similarity_scores, "Category")
        
        # Check for abbreviation pattern boost
        abbreviation_boost = 0
        if entity_a and entity_b:
            org_a = entity_a.get("Organization Name", "")
            org_b = entity_b.get("Organization Name", "")
            if self._could_be_abbreviation(org_a, org_b):
                abbreviation_boost = 50  # Major boost for abbreviation patterns
        
        # Weighted combination
        confidence = (name_score * 0.5) + (website_score * 0.2) + (email_score * 0.2) + (category_score * 0.1)
        
        # Add abbreviation boost
        confidence = min(confidence + abbreviation_boost, 100)
        
        # Boost for supporting evidence
        supporting_matches = sum(1 for field in ["Website", "Email", "Phone", "Address"]
                               if self._get_field_score(similarity_scores, field) > 80)
        
        if supporting_matches >= 2:
            confidence = min(confidence + 20, 100)
        elif supporting_matches == 1:
            confidence = min(confidence + 10, 100)
            
        return confidence
        
    def _has_exact_match(self, scores: Dict[str, Any], fields: List[str]) -> bool:
        """Check if any of the specified fields has an exact match."""
        for field in fields:
            if field in scores and isinstance(scores[field], dict):
                if scores[field].get("exact", 0) == 100:
                    return True
        return False
        
    def _get_field_score(self, scores: Dict[str, Any], field: str) -> float:
        """Get composite score for a specific field."""
        if field not in scores or not isinstance(scores[field], dict):
            return 0.0
        return scores[field].get("composite", 0.0)


class EventProcessor(BaseEntityProcessor):
    """Processor for Key Places & Events entities."""
    
    def __init__(self):
        super().__init__("Key Places & Events")
        
    def get_comparison_fields(self) -> List[str]:
        """Get fields to compare for events/places."""
        return [
            "Event / Place Name",
            "Date of Event",
            "Location",
            "Type",
            "Description",
            "People Involved"
        ]
        
    def get_primary_fields(self) -> List[str]:
        """Get primary identifying fields for events."""
        return ["Event / Place Name", "Date of Event", "Location"]
        
    def is_potential_duplicate(self, event_a: Dict[str, Any], event_b: Dict[str, Any]) -> bool:
        """Quick pre-screening for potential event/place duplicates."""
        # Name similarity check
        name_a = event_a.get("Event / Place Name", "").strip().lower()
        name_b = event_b.get("Event / Place Name", "").strip().lower()
        
        if not name_a or not name_b:
            return False
            
        # Check for name overlap
        tokens_a = self.extract_key_tokens(name_a)
        tokens_b = self.extract_key_tokens(name_b)
        
        if len(tokens_a) == 0 or len(tokens_b) == 0:
            return False
            
        overlap = len(tokens_a & tokens_b)
        union = len(tokens_a | tokens_b)
        
        name_similarity = overlap / union
        
        # If names are very similar, check temporal proximity
        if name_similarity >= 0.6:
            return self._check_temporal_proximity(event_a, event_b)
            
        return name_similarity >= 0.8
        
    def _check_temporal_proximity(self, event_a: Dict[str, Any], event_b: Dict[str, Any]) -> bool:
        """Check if events are temporally close (for date-based events)."""
        date_a = self._parse_date(event_a.get("Date of Event", ""))
        date_b = self._parse_date(event_b.get("Date of Event", ""))
        
        if not date_a or not date_b:
            return True  # If no dates, don't exclude based on temporal proximity
            
        # Events within 1 day are considered potentially the same
        time_diff = abs((date_a - date_b).total_seconds())
        return time_diff <= 86400  # 24 hours
        
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string into datetime object."""
        if not date_str or not isinstance(date_str, str):
            return None
            
        # Try common date formats
        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y", 
            "%m/%d/%Y",
            "%Y-%m-%d %H:%M:%S",
            "%d-%m-%Y",
            "%B %d, %Y",
            "%d %B %Y"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
                
        return None
        
    def calculate_confidence(self, similarity_scores: Dict[str, Any], entity_a: Dict[str, Any] = None, entity_b: Dict[str, Any] = None) -> float:
        """Calculate confidence score for event/place matching."""
        # Name-based confidence
        name_score = self._get_field_score(similarity_scores, "Event / Place Name")
        
        # Date proximity (if available)
        date_score = self._get_field_score(similarity_scores, "Date of Event")
        
        # Location similarity
        location_score = self._get_field_score(similarity_scores, "Location")
        
        # Type and description
        type_score = self._get_field_score(similarity_scores, "Type")
        desc_score = self._get_field_score(similarity_scores, "Description")
        
        # Weighted combination - for events, date + location is very important
        confidence = (name_score * 0.3) + (date_score * 0.3) + (location_score * 0.3) + (type_score * 0.05) + (desc_score * 0.05)
        
        # Special boost for events with same date and similar location
        if date_score == 100 and location_score > 50:
            confidence = min(confidence + 25, 100)
        elif date_score > 90 and location_score > 80:
            confidence = min(confidence + 15, 100)
        elif date_score > 80 or location_score > 80:
            confidence = min(confidence + 5, 100)
            
        return confidence
        
    def _get_field_score(self, scores: Dict[str, Any], field: str) -> float:
        """Get composite score for a specific field."""
        if field not in scores or not isinstance(scores[field], dict):
            return 0.0
        return scores[field].get("composite", 0.0)


class DocumentProcessor(BaseEntityProcessor):
    """Processor for Documents & Evidence and similar text-based entities."""
    
    def __init__(self):
        super().__init__("Documents & Evidence")
        
    def get_comparison_fields(self) -> List[str]:
        """Get fields to compare for documents."""
        return [
            "Document Name",
            "Entry Title", 
            "Title",
            "Document Type",
            "Description",
            "Notes",
            "Source",
            "URL"
        ]
        
    def get_primary_fields(self) -> List[str]:
        """Get primary identifying fields for documents."""
        return ["Document Name", "Entry Title", "Title", "URL"]
        
    def is_potential_duplicate(self, doc_a: Dict[str, Any], doc_b: Dict[str, Any]) -> bool:
        """Quick pre-screening for potential document duplicates."""
        # URL exact match
        url_a = self._normalize_url(doc_a.get("URL", ""))
        url_b = self._normalize_url(doc_b.get("URL", ""))
        if url_a and url_b and url_a == url_b:
            return True
            
        # Title similarity check
        title_a = self._get_document_title(doc_a)
        title_b = self._get_document_title(doc_b)
        
        if not title_a or not title_b:
            return False
            
        # Check for substantial title overlap
        tokens_a = self.extract_key_tokens(title_a)
        tokens_b = self.extract_key_tokens(title_b)
        
        if len(tokens_a) == 0 or len(tokens_b) == 0:
            return False
            
        overlap = len(tokens_a & tokens_b)
        union = len(tokens_a | tokens_b)
        
        return overlap / union >= 0.7
        
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for comparison."""
        if not url:
            return ""
            
        url = url.lower().strip()
        
        # Remove protocol
        url = re.sub(r'^https?://', '', url)
        
        # Remove www
        url = re.sub(r'^www\.', '', url)
        
        # Remove fragments and query parameters for comparison
        url = url.split('#')[0].split('?')[0]
        
        return url
        
    def _get_document_title(self, doc: Dict[str, Any]) -> str:
        """Get the document title from various possible fields."""
        title_fields = ["Document Name", "Entry Title", "Title", "Name"]
        
        for field in title_fields:
            title = doc.get(field, "")
            if title and isinstance(title, str):
                return title.strip()
                
        return ""
        
    def calculate_confidence(self, similarity_scores: Dict[str, Any], entity_a: Dict[str, Any] = None, entity_b: Dict[str, Any] = None) -> float:
        """Calculate confidence score for document matching."""
        # High weight on exact URL match
        url_score = self._get_field_score(similarity_scores, "URL")
        if url_score == 100:
            return 95.0
            
        # Title-based confidence
        title_scores = []
        for field in ["Document Name", "Entry Title", "Title"]:
            score = self._get_field_score(similarity_scores, field)
            if score > 0:
                title_scores.append(score)
                
        max_title_score = max(title_scores) if title_scores else 0
        
        # Supporting evidence
        type_score = self._get_field_score(similarity_scores, "Document Type")
        desc_score = self._get_field_score(similarity_scores, "Description")
        source_score = self._get_field_score(similarity_scores, "Source")
        
        # Weighted combination
        confidence = (max_title_score * 0.5) + (url_score * 0.2) + (type_score * 0.1) + (desc_score * 0.1) + (source_score * 0.1)
        
        # Boost for multiple supporting fields
        supporting_matches = sum(1 for score in [type_score, desc_score, source_score] if score > 70)
        
        if supporting_matches >= 2:
            confidence = min(confidence + 10, 100)
        elif supporting_matches == 1:
            confidence = min(confidence + 5, 100)
            
        return confidence
        
    def _get_field_score(self, scores: Dict[str, Any], field: str) -> float:
        """Get composite score for a specific field."""
        if field not in scores or not isinstance(scores[field], dict):
            return 0.0
        return scores[field].get("composite", 0.0)