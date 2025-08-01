"""Natural language query parsing implementation.

This module implements NLP capabilities for parsing natural language
queries into structured query formats.
"""

import re
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict

from .interfaces import (
    QueryParser,
    ParsedQuery,
    ExtractedEntity,
    QueryIntent,
    EntityType,
    NLPConfig
)


class SimpleQueryParser:
    """Basic query parser using pattern matching and heuristics."""
    
    def __init__(self, config: Optional[NLPConfig] = None):
        self.config = config or NLPConfig()
        self.entity_patterns = self._build_entity_patterns()
        self.intent_patterns = self._build_intent_patterns()
        self.filter_patterns = self._build_filter_patterns()
    
    def parse(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ParsedQuery:
        """Parse natural language query into structured format."""
        if not query:
            return self._empty_query(query)
        
        # Normalize query
        normalized = self._normalize_query(query)
        
        # Extract entities
        entities = self.extract_entities(normalized)
        
        # Classify intent
        intent, confidence = self.classify_intent(normalized, entities)
        
        # Extract filters
        filters = self.extract_filters(normalized, entities)
        
        # Extract sort criteria
        sort_criteria = self._extract_sort_criteria(normalized)
        
        # Extract limit
        limit = self._extract_limit(normalized)
        
        # Extract relationships to include
        relationships = self._extract_relationships(normalized)
        
        # Extract aggregations
        aggregations = self._extract_aggregations(normalized)
        
        return ParsedQuery(
            original_text=query,
            intent=intent,
            entities=entities,
            filters=filters,
            sort_criteria=sort_criteria,
            limit=limit,
            relationships_to_include=relationships,
            aggregations=aggregations,
            confidence=confidence
        )
    
    def extract_entities(self, text: str) -> List[ExtractedEntity]:
        """Extract entities from text."""
        entities = []
        
        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    entity = ExtractedEntity(
                        text=match.group(),
                        entity_type=entity_type,
                        confidence=0.8,  # Base confidence
                        start_pos=match.start(),
                        end_pos=match.end()
                    )
                    
                    # Adjust confidence based on context
                    if self._is_quoted(text, match.start(), match.end()):
                        entity.confidence = 0.95
                    
                    entities.append(entity)
        
        # Remove overlapping entities (keep higher confidence)
        entities = self._remove_overlapping_entities(entities)
        
        return entities
    
    def classify_intent(
        self,
        query: str,
        entities: List[ExtractedEntity]
    ) -> Tuple[QueryIntent, float]:
        """Classify query intent."""
        query_lower = query.lower()
        
        # Check each intent pattern
        best_intent = QueryIntent.UNKNOWN
        best_confidence = 0.0
        
        for intent, patterns in self.intent_patterns.items():
            for pattern, confidence in patterns:
                if re.search(pattern, query_lower):
                    if confidence > best_confidence:
                        best_intent = intent
                        best_confidence = confidence
        
        # Adjust based on entities found
        if best_intent == QueryIntent.UNKNOWN and entities:
            # Default to search if entities found
            best_intent = QueryIntent.SEARCH_ENTITY
            best_confidence = 0.6
        
        return best_intent, best_confidence
    
    def extract_filters(
        self,
        query: str,
        entities: List[ExtractedEntity]
    ) -> Dict[str, Any]:
        """Extract filter conditions from query."""
        filters = {}
        query_lower = query.lower()
        
        # Date filters
        date_filters = self._extract_date_filters(query_lower)
        filters.update(date_filters)
        
        # Status filters
        status_filters = self._extract_status_filters(query_lower)
        filters.update(status_filters)
        
        # Numeric filters
        numeric_filters = self._extract_numeric_filters(query_lower)
        filters.update(numeric_filters)
        
        # Entity-based filters
        for entity in entities:
            if entity.entity_type == EntityType.PERSON:
                filters["owner"] = entity.text
            elif entity.entity_type == EntityType.ORGANIZATION:
                filters["organization"] = entity.text
            elif entity.entity_type == EntityType.LOCATION:
                filters["location"] = entity.text
        
        return filters
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query text."""
        # Remove extra whitespace
        normalized = " ".join(query.split())
        
        # Expand common contractions
        contractions = {
            "don't": "do not",
            "won't": "will not",
            "can't": "cannot",
            "n't": " not",
            "'re": " are",
            "'ve": " have",
            "'ll": " will",
            "'d": " would"
        }
        
        for contraction, expansion in contractions.items():
            normalized = normalized.replace(contraction, expansion)
        
        return normalized
    
    def _build_entity_patterns(self) -> Dict[EntityType, List[str]]:
        """Build regex patterns for entity extraction."""
        return {
            EntityType.PERSON: [
                r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # Full names
                r'\b(?:Mr\.|Mrs\.|Ms\.|Dr\.) [A-Z][a-z]+\b',  # Titles
                r'"([^"]+)"',  # Quoted names
            ],
            EntityType.ORGANIZATION: [
                r'\b[A-Z][a-z]+(?: [A-Z][a-z]+)* (?:Inc|LLC|Ltd|Corp|Company|Organization)\b',
                r'\b[A-Z]{2,}\b',  # Acronyms
            ],
            EntityType.DATE: [
                r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',  # MM/DD/YYYY
                r'\b\d{4}-\d{2}-\d{2}\b',  # YYYY-MM-DD
                r'\b(?:yesterday|today|tomorrow)\b',
                r'\b(?:last|next) (?:week|month|year)\b',
                r'\b\d+ (?:days?|weeks?|months?|years?) ago\b',
            ],
            EntityType.LOCATION: [
                r'\b(?:in|at|from|to) ([A-Z][a-z]+(?: [A-Z][a-z]+)*)\b',
                r'\b[A-Z][a-z]+, [A-Z]{2}\b',  # City, State
            ],
            EntityType.EVENT: [
                r'\b[A-Z][a-z]+ (?:Meeting|Conference|Summit|Event)\b',
            ],
            EntityType.TASK: [
                r'\btask #?\d+\b',
                r'\b(?:TODO|FIXME|BUG):\s*([^,\n]+)',
            ]
        }
    
    def _build_intent_patterns(self) -> Dict[QueryIntent, List[Tuple[str, float]]]:
        """Build patterns for intent classification."""
        return {
            QueryIntent.SEARCH_ENTITY: [
                (r'\b(?:find|search|show|get|list)\b.*\b(?:all|any)?\b', 0.9),
                (r'\b(?:who|what|where|which)\b', 0.8),
                (r'\b(?:people|persons?|organizations?|companies|entities)\b', 0.7),
            ],
            QueryIntent.FIND_RELATIONSHIP: [
                (r'\b(?:related|connected|associated|linked)\b', 0.9),
                (r'\b(?:relationship|connection|association|link) between\b', 0.95),
                (r'\b(?:who knows|connected to|works with)\b', 0.85),
            ],
            QueryIntent.AGGREGATE_DATA: [
                (r'\b(?:count|sum|average|total|statistics)\b', 0.9),
                (r'\b(?:how many|how much)\b', 0.85),
                (r'\b(?:group by|grouped|categorized)\b', 0.9),
            ],
            QueryIntent.FILTER_RESULTS: [
                (r'\b(?:filter|where|only|just)\b', 0.8),
                (r'\b(?:created|updated|modified) (?:after|before|between)\b', 0.9),
                (r'\b(?:status|state|type) (?:is|equals?)\b', 0.85),
            ],
            QueryIntent.SORT_RESULTS: [
                (r'\b(?:sort|order) by\b', 0.95),
                (r'\b(?:latest|newest|oldest|recent)\b', 0.8),
                (r'\b(?:alphabetical|chronological)\b', 0.85),
            ],
            QueryIntent.COMPARE_ENTITIES: [
                (r'\b(?:compare|versus|vs|difference between)\b', 0.9),
                (r'\b(?:similar|different|alike)\b', 0.7),
            ]
        }
    
    def _build_filter_patterns(self) -> Dict[str, str]:
        """Build patterns for filter extraction."""
        return {
            "status": r'\bstatus (?:is |= )?([a-z]+)\b',
            "type": r'\btype (?:is |= )?([a-z]+)\b',
            "priority": r'\bpriority (?:is |= )?([a-z]+)\b',
            "created_after": r'\bcreated after ([0-9-/]+)\b',
            "created_before": r'\bcreated before ([0-9-/]+)\b',
            "updated_after": r'\bupdated after ([0-9-/]+)\b',
            "updated_before": r'\bupdated before ([0-9-/]+)\b',
        }
    
    def _extract_sort_criteria(self, query: str) -> List[Tuple[str, str]]:
        """Extract sorting criteria from query."""
        criteria = []
        
        # Pattern for "sort by X"
        sort_match = re.search(r'\bsort(?:ed)? by (\w+)(?: (asc|desc|ascending|descending))?\b', query, re.IGNORECASE)
        if sort_match:
            field = sort_match.group(1)
            direction = sort_match.group(2) or "asc"
            if "desc" in direction:
                direction = "desc"
            else:
                direction = "asc"
            criteria.append((field, direction))
        
        # Implicit sorting patterns
        if re.search(r'\b(?:latest|newest|most recent)\b', query, re.IGNORECASE):
            criteria.append(("created_at", "desc"))
        elif re.search(r'\b(?:oldest|earliest)\b', query, re.IGNORECASE):
            criteria.append(("created_at", "asc"))
        elif re.search(r'\balphabetical\b', query, re.IGNORECASE):
            criteria.append(("name", "asc"))
        
        return criteria
    
    def _extract_limit(self, query: str) -> Optional[int]:
        """Extract result limit from query."""
        # Pattern for "top N" or "first N" or "limit N"
        limit_match = re.search(r'\b(?:top|first|limit) (\d+)\b', query, re.IGNORECASE)
        if limit_match:
            return int(limit_match.group(1))
        
        # Pattern for "N results"
        results_match = re.search(r'\b(\d+) results?\b', query, re.IGNORECASE)
        if results_match:
            return int(results_match.group(1))
        
        return None
    
    def _extract_relationships(self, query: str) -> List[str]:
        """Extract relationships to include."""
        relationships = []
        
        # Pattern for "with their X"
        with_match = re.findall(r'\bwith (?:their |its )?(\w+)\b', query, re.IGNORECASE)
        relationships.extend(with_match)
        
        # Pattern for "including X"
        including_match = re.findall(r'\bincluding (\w+)\b', query, re.IGNORECASE)
        relationships.extend(including_match)
        
        # Common relationship keywords
        rel_keywords = ["members", "participants", "owners", "creators", "assignees"]
        for keyword in rel_keywords:
            if keyword in query.lower():
                relationships.append(keyword)
        
        return list(set(relationships))  # Remove duplicates
    
    def _extract_aggregations(self, query: str) -> List[Dict[str, Any]]:
        """Extract aggregation requests."""
        aggregations = []
        
        # Count aggregations
        count_match = re.search(r'\bcount (?:of |by )?(\w+)\b', query, re.IGNORECASE)
        if count_match:
            aggregations.append({
                "type": "count",
                "field": count_match.group(1)
            })
        
        # Sum aggregations
        sum_match = re.search(r'\bsum (?:of )?(\w+)\b', query, re.IGNORECASE)
        if sum_match:
            aggregations.append({
                "type": "sum",
                "field": sum_match.group(1)
            })
        
        # Average aggregations
        avg_match = re.search(r'\b(?:average|avg) (?:of )?(\w+)\b', query, re.IGNORECASE)
        if avg_match:
            aggregations.append({
                "type": "avg",
                "field": avg_match.group(1)
            })
        
        # Group by
        group_match = re.search(r'\bgroup(?:ed)? by (\w+)\b', query, re.IGNORECASE)
        if group_match:
            aggregations.append({
                "type": "group_by",
                "field": group_match.group(1)
            })
        
        return aggregations
    
    def _extract_date_filters(self, query: str) -> Dict[str, Any]:
        """Extract date-based filters."""
        filters = {}
        
        # Relative dates
        if "today" in query:
            filters["date"] = {"$gte": "today", "$lt": "tomorrow"}
        elif "yesterday" in query:
            filters["date"] = {"$gte": "yesterday", "$lt": "today"}
        elif "this week" in query:
            filters["date"] = {"$gte": "start_of_week", "$lt": "end_of_week"}
        elif "last week" in query:
            filters["date"] = {"$gte": "start_of_last_week", "$lt": "end_of_last_week"}
        
        # Date ranges
        range_match = re.search(r'between ([0-9-/]+) and ([0-9-/]+)', query)
        if range_match:
            filters["date"] = {
                "$gte": range_match.group(1),
                "$lte": range_match.group(2)
            }
        
        return filters
    
    def _extract_status_filters(self, query: str) -> Dict[str, Any]:
        """Extract status-based filters."""
        filters = {}
        
        status_keywords = {
            "open": ["open", "active", "pending"],
            "closed": ["closed", "completed", "done"],
            "in progress": ["in progress", "working", "ongoing"]
        }
        
        for status, keywords in status_keywords.items():
            for keyword in keywords:
                if keyword in query:
                    filters["status"] = status
                    break
        
        return filters
    
    def _extract_numeric_filters(self, query: str) -> Dict[str, Any]:
        """Extract numeric filters."""
        filters = {}
        
        # Greater than patterns
        gt_match = re.search(r'(\w+) (?:greater than|gt|>) (\d+)', query)
        if gt_match:
            filters[gt_match.group(1)] = {"$gt": int(gt_match.group(2))}
        
        # Less than patterns
        lt_match = re.search(r'(\w+) (?:less than|lt|<) (\d+)', query)
        if lt_match:
            filters[lt_match.group(1)] = {"$lt": int(lt_match.group(2))}
        
        # Between patterns
        between_match = re.search(r'(\w+) between (\d+) and (\d+)', query)
        if between_match:
            filters[between_match.group(1)] = {
                "$gte": int(between_match.group(2)),
                "$lte": int(between_match.group(3))
            }
        
        return filters
    
    def _is_quoted(self, text: str, start: int, end: int) -> bool:
        """Check if text span is within quotes."""
        # Check for quotes before start
        quote_before = text.rfind('"', 0, start)
        quote_after = text.find('"', end)
        
        if quote_before != -1 and quote_after != -1:
            # Check if there's a closing quote between
            quote_between = text.find('"', quote_before + 1, start)
            return quote_between == -1
        
        return False
    
    def _remove_overlapping_entities(self, entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
        """Remove overlapping entities, keeping higher confidence ones."""
        if not entities:
            return entities
        
        # Sort by confidence (descending)
        sorted_entities = sorted(entities, key=lambda e: e.confidence, reverse=True)
        
        kept_entities = []
        for entity in sorted_entities:
            # Check if overlaps with any kept entity
            overlaps = False
            for kept in kept_entities:
                if (entity.start_pos < kept.end_pos and 
                    entity.end_pos > kept.start_pos):
                    overlaps = True
                    break
            
            if not overlaps:
                kept_entities.append(entity)
        
        # Sort by position for consistent output
        kept_entities.sort(key=lambda e: e.start_pos)
        
        return kept_entities
    
    def _empty_query(self, original: str) -> ParsedQuery:
        """Create empty parsed query."""
        return ParsedQuery(
            original_text=original,
            intent=QueryIntent.UNKNOWN,
            entities=[],
            filters={},
            sort_criteria=[],
            limit=None,
            relationships_to_include=[],
            aggregations=[],
            confidence=0.0
        )