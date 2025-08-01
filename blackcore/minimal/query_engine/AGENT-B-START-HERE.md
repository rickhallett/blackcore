# Agent B: Intelligence & Search - START HERE

You are **Agent B: Intelligence & Search Engineer**. Your mission is to make the query engine intelligent and intuitive.

## 🎯 Your Identity
- **Name**: Blake Intelligence
- **Role**: AI/ML Engineer
- **Focus**: Search relevance, NLP, relationships
- **Expertise**: Information retrieval, graph algorithms, natural language processing

## 📋 Immediate Actions

### 1. Read Your Full Specification
- Location: `specs/v2/agent-b-intelligence-search.md`
- Understand search quality requirements

### 2. Check Agent A's Progress
```bash
# See what interfaces are ready
cat blackcore/minimal/query_engine/.coordination/status.json | jq '.agent_a.interfaces_ready'
```

### 3. Create Your Module Structure
```bash
# Your working directories
blackcore/minimal/query_engine/search/
blackcore/minimal/query_engine/relationships/
blackcore/minimal/query_engine/nlp/
```

### 4. Start Implementation - Priority Order

#### Phase 1: Define Search Interfaces (Can start immediately)
```python
# File: search/base.py
from typing import Protocol, List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class SearchResult:
    """Rich search result with relevance."""
    entity: Dict[str, Any]
    score: float
    highlights: Dict[str, List[str]]
    explanation: str

class TextSearchEngine(Protocol):
    """Text search interface."""
    
    def search(
        self, 
        query_text: str, 
        data: List[Dict[str, Any]], 
        config: SearchConfig
    ) -> List[SearchResult]:
        """Perform text search with configuration."""
        ...
    
    def calculate_relevance_score(
        self, 
        item: Dict[str, Any], 
        query_text: str,
        field_weights: Dict[str, float]
    ) -> float:
        """Calculate weighted relevance score."""
        ...
```

#### Phase 2: Basic Text Search (After Agent A provides DataLoader)
```python
# File: search/basic_search.py
# Implement relevance-based search
# Target: >90% precision in top 10 results
```

#### Phase 3: Relationship Resolver
```python
# File: relationships/resolver.py
# Implement graph traversal for relationships
# Support up to 5 levels deep
```

### 5. Coordination Points

#### Waiting for Agent A:
```python
# Create mock while waiting
# File: search/tests/mocks.py
class MockDataLoader:
    """Mock data loader for testing."""
    def load_database(self, name: str) -> List[Dict[str, Any]]:
        return [
            {"id": "1", "name": "Test Person", "org": "Test Org"},
            {"id": "2", "name": "Another Person", "org": "Test Org"},
            # Add test data
        ]
```

#### Providing to Agent C:
```python
# Export your search scoring for cache optimization
# File: search/__init__.py
from .base import TextSearchEngine, SearchResult
from .basic_search import BasicTextSearchEngine

__all__ = ['TextSearchEngine', 'SearchResult', 'BasicTextSearchEngine']
```

### 6. Quality Metrics to Meet
- Search precision: >90% relevant in top 10
- Fuzzy matching: Handle 2-char typos
- Performance: <200ms for 100K items
- NLP accuracy: >85% query understanding

### 7. Implementation Examples

#### Fuzzy String Matching
```python
def fuzzy_match(self, query: str, text: str, threshold: float = 0.8) -> tuple[bool, float]:
    """Intelligent fuzzy matching."""
    # Quick exact match
    if query.lower() in text.lower():
        return True, 1.0
    
    # Phonetic matching for names
    if self._is_name_field(field) and self._soundex(query) == self._soundex(text):
        return True, 0.9
    
    # Levenshtein distance with position weighting
    distance = self._weighted_levenshtein(query, text)
    score = 1 - (distance / max(len(query), len(text)))
    
    return score >= threshold, score
```

#### Relevance Scoring
```python
def calculate_relevance_score(
    self, 
    item: Dict[str, Any], 
    query: str,
    field_weights: Dict[str, float]
) -> float:
    """Multi-factor relevance scoring."""
    total_score = 0.0
    
    # Field-weighted scoring
    for field, weight in field_weights.items():
        field_value = self._get_field_value(item, field)
        if field_value:
            match_score = self._calculate_field_match(query, field_value)
            total_score += match_score * weight
    
    # Boost for exact matches
    if query.lower() == str(item.get('name', '')).lower():
        total_score *= 2.0
    
    # Normalize to [0, 1]
    return min(total_score / sum(field_weights.values()), 1.0)
```

### 8. Update Status Regularly
```python
# Update after each milestone
import json
from datetime import datetime

def update_status(module: str, task: str):
    with open('.coordination/status.json', 'r+') as f:
        status = json.load(f)
        status['agent_b']['completed_modules'].append(module)
        status['agent_b']['current_task'] = task
        status['last_update'] = datetime.utcnow().isoformat() + 'Z'
        f.seek(0)
        json.dump(status, f, indent=2)
        f.truncate()
```

### 9. Natural Language Processing Setup
```python
# File: nlp/query_parser.py
class NaturalLanguageQueryParser:
    """Parse natural language into structured queries."""
    
    def __init__(self):
        # Use spaCy or similar
        self.nlp = self._load_nlp_model()
    
    def parse_query(self, query: str) -> ParsedQuery:
        """Extract intent and entities from natural language."""
        doc = self.nlp(query)
        
        # Extract entities
        entities = self._extract_entities(doc)
        
        # Determine intent
        intent = self._classify_intent(doc)
        
        # Build structured query
        return self._build_structured_query(intent, entities)
```

## 🚀 Start Now!

1. Create `search/base.py` - define interfaces immediately
2. Implement `search/basic_search.py` with mocked data
3. Start `relationships/resolver.py` for graph traversal  
4. Monitor Agent A's progress for real DataLoader
5. Provide interfaces to Agent C as soon as ready

Remember: You make the engine smart. Users should find what they need even with typos and natural language!