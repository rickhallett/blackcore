# LLM-Based Entity Deduplication Specification

## Overview

This specification outlines the architecture and implementation details for replacing the rule-based deduplication system in `blackcore/minimal/simple_scorer.py` with an LLM-based approach using Claude 3.5 Haiku. The LLM will handle entity matching with greater flexibility and intelligence, eliminating hardcoded mappings while introducing additional comparison dimensions.

## Motivation

The current rule-based system has limitations:
- Hardcoded nickname mappings that don't scale
- Fixed organization suffix removal patterns
- Limited to simple string matching and fuzzy comparison
- Cannot understand context or semantic similarity
- Misses complex relationships and patterns

## Architecture Design

### Core Components

#### 1. LLMScorer Class
```python
class LLMScorer:
    """LLM-based similarity scoring for intelligent deduplication."""
    
    def __init__(self, api_key: str, model: str = "claude-3.5-haiku-20241022"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        
    def score_entities(self, entity1: Dict, entity2: Dict, entity_type: str) -> Tuple[float, str, Dict]:
        """Score similarity between two entities using LLM analysis."""
```

#### 2. Function Calling Tools

The LLM will use structured function calling to provide consistent scoring output:

```python
entity_scoring_tool = {
    "name": "score_entity_match",
    "description": "Analyze two entities and determine if they represent the same real-world entity",
    "input_schema": {
        "type": "object",
        "properties": {
            "confidence_score": {
                "type": "number",
                "description": "Similarity score from 0-100",
                "minimum": 0,
                "maximum": 100
            },
            "is_match": {
                "type": "boolean",
                "description": "Whether these entities represent the same real-world entity"
            },
            "match_reason": {
                "type": "string",
                "description": "Primary reason for match/non-match decision"
            },
            "supporting_evidence": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of specific evidence supporting the decision"
            },
            "analysis_dimensions": {
                "type": "object",
                "properties": {
                    "name_similarity": {"type": "number", "minimum": 0, "maximum": 100},
                    "temporal_proximity": {"type": "number", "minimum": 0, "maximum": 100},
                    "social_graph": {"type": "number", "minimum": 0, "maximum": 100},
                    "location_overlap": {"type": "number", "minimum": 0, "maximum": 100},
                    "communication_pattern": {"type": "number", "minimum": 0, "maximum": 100},
                    "professional_context": {"type": "number", "minimum": 0, "maximum": 100},
                    "behavioral_pattern": {"type": "number", "minimum": 0, "maximum": 100},
                    "linguistic_similarity": {"type": "number", "minimum": 0, "maximum": 100}
                }
            }
        },
        "required": ["confidence_score", "is_match", "match_reason", "supporting_evidence"]
    }
}
```

## Comparison Dimensions

### 1. Name Similarity (Existing, Enhanced)
- **Current**: Nickname mappings, fuzzy matching
- **Enhanced**: 
  - Understands cultural name variations (e.g., "José" vs "Joe")
  - Recognizes titles and honorifics across languages
  - Handles transliterations (e.g., "Александр" vs "Alexander")
  - Identifies maiden names and name changes

### 2. Temporal Proximity (New)
- Analyzes when entities were mentioned/created
- Considers activity patterns over time
- Identifies gaps that might indicate different entities
- Example: Two "John Smiths" active in different decades likely different people

### 3. Social Graph Analysis (New)
- Examines relationships and connections
- Shared contacts increase match probability
- Overlapping social circles as evidence
- Example: Both entities connected to same organization members

### 4. Location Correlation (New)
- Geographic proximity of activities
- Overlapping location mentions
- Travel patterns and presence
- Example: One in New York, one in London reduces match probability

### 5. Communication Patterns (New)
- Email domains and formats
- Phone number patterns and regions
- Communication style and frequency
- Example: Similar email structure (firstname.lastname@company.com)

### 6. Professional Context (New)
- Industry and sector alignment
- Role progression and career paths
- Skill sets and expertise areas
- Example: Junior Developer → Senior Developer progression

### 7. Behavioral Patterns (New)
- Meeting attendance patterns
- Task assignment types
- Interaction styles
- Example: Always attends Monday planning meetings

### 8. Linguistic Cues (New)
- Writing style analysis
- Vocabulary and phrasing patterns
- Language preferences
- Example: Consistent use of specific technical terms

## Implementation Details

### Request Format

```python
def _build_llm_prompt(self, entity1: Dict, entity2: Dict, entity_type: str, context: Dict) -> str:
    """Build comprehensive prompt for LLM analysis."""
    return f"""Analyze these two {entity_type} entities for potential duplication.

Entity 1:
{json.dumps(entity1, indent=2)}

Entity 2:
{json.dumps(entity2, indent=2)}

Additional Context:
- Time between mentions: {context.get('time_gap', 'unknown')}
- Shared connections: {context.get('shared_connections', [])}
- Previous decisions: {context.get('previous_matches', [])}

Use the score_entity_match tool to provide your analysis. Consider all available dimensions."""
```

### Response Processing

```python
def _process_llm_response(self, response: Message) -> Tuple[float, str, Dict]:
    """Extract scoring from LLM response."""
    for content in response.content:
        if content.type == "tool_use" and content.name == "score_entity_match":
            result = content.input
            return (
                result["confidence_score"],
                result["match_reason"],
                {
                    "is_match": result["is_match"],
                    "evidence": result["supporting_evidence"],
                    "dimensions": result.get("analysis_dimensions", {})
                }
            )
```

### Caching Strategy

```python
class LLMScorerCache:
    """Cache LLM scoring decisions for efficiency."""
    
    def get_cache_key(self, entity1: Dict, entity2: Dict) -> str:
        """Generate stable cache key for entity pair."""
        # Sort entities to ensure consistent ordering
        e1_str = json.dumps(entity1, sort_keys=True)
        e2_str = json.dumps(entity2, sort_keys=True)
        combined = "".join(sorted([e1_str, e2_str]))
        return hashlib.md5(combined.encode()).hexdigest()
```

## Integration Approach

### 1. Backward Compatibility
- Keep SimpleScorer as fallback option
- Configuration flag to choose scorer type
- Gradual migration path

### 2. Configuration
```python
class ProcessingConfig(BaseModel):
    """Processing configuration."""
    # ... existing fields ...
    deduplication_scorer: str = "llm"  # "llm" or "simple"
    llm_scorer_config: Dict = {
        "model": "claude-3.5-haiku-20241022",
        "temperature": 0.1,
        "cache_ttl": 3600,
        "batch_size": 5  # Process multiple comparisons in one request
    }
```

### 3. Error Handling
- Fallback to SimpleScorer on LLM errors
- Retry logic with exponential backoff
- Clear error messages for debugging

## Performance Considerations

### 1. Batching
- Group multiple entity comparisons per LLM request
- Reduce API calls and latency
- Target: 5-10 comparisons per request

### 2. Caching
- Cache LLM decisions for identical entity pairs
- TTL-based cache expiration
- Memory-efficient cache implementation

### 3. Cost Optimization
- Use Claude 3.5 Haiku for cost efficiency
- Estimated cost: ~$0.0003 per comparison
- Batch processing reduces per-comparison cost

## Migration Plan

### Phase 1: Implementation
1. Create `llm_scorer.py` with LLMScorer class
2. Implement function calling tools
3. Add comprehensive logging

### Phase 2: Testing
1. Unit tests with mocked LLM responses
2. Integration tests with real API calls
3. A/B testing against SimpleScorer

### Phase 3: Rollout
1. Feature flag for gradual rollout
2. Monitor accuracy and performance
3. Gather feedback and iterate

## Example Usage

```python
# Initialize LLM scorer
scorer = LLMScorer(api_key=config.ai.api_key)

# Score two person entities
score, reason, details = scorer.score_entities(
    entity1={
        "name": "Tony Smith",
        "email": "anthony.smith@nassau.gov",
        "organization": "Nassau Council"
    },
    entity2={
        "name": "Anthony Smith", 
        "email": "asmith@nassau.gov",
        "organization": "Nassau Council Inc"
    },
    entity_type="person"
)

# Result
# score: 95.0
# reason: "Same person - nickname variation with matching organization"
# details: {
#     "is_match": True,
#     "evidence": [
#         "Tony is common nickname for Anthony",
#         "Email domains match (nassau.gov)",
#         "Organization names are variations of same entity"
#     ],
#     "dimensions": {
#         "name_similarity": 90,
#         "professional_context": 95,
#         "communication_pattern": 100
#     }
# }
```

## Success Metrics

1. **Accuracy**: >95% correct deduplication decisions
2. **Performance**: <2s average scoring time
3. **Cost**: <$0.001 per entity processed
4. **Flexibility**: Handle 90% of edge cases without code changes

## Future Enhancements

1. **Multi-model support**: Add GPT-4o-mini as alternative
2. **Confidence calibration**: Learn from user feedback
3. **Explanation UI**: Show reasoning in Notion
4. **Bulk operations**: Process entire databases
5. **Active learning**: Improve from corrections