# Search API Documentation

The Search API provides advanced semantic search capabilities for the BlackCore knowledge graph, featuring natural language understanding, fuzzy matching, and intelligent entity recognition.

## Overview

The Search API extends the Query Engine with sophisticated NLP capabilities:

- **Natural Language Understanding** - Process queries in plain English
- **Fuzzy Matching** - Find results despite typos and variations
- **Entity Recognition** - Automatically detect emails, dates, phone numbers
- **Synonym Expansion** - Match related terms (e.g., "task" finds "todo")
- **Intent Detection** - Understand what users are looking for
- **Semantic Scoring** - Rank results by true relevance

## Endpoints

### Universal Search

`POST /search/universal`

Perform intelligent search across all databases with semantic understanding.

```json
{
  "query": "Alice machine learning quarterly report",
  "databases": ["People & Contacts", "Documents & Evidence"],
  "max_results": 50,
  "min_score": 0.3,
  "enable_fuzzy": true,
  "enable_semantic": true,
  "include_explanations": true
}
```

Response includes:
- Ranked results with relevance scores
- Search intent detection
- Faceted results by database/type/status
- Suggested alternative queries
- Execution time metrics

### Entity-Specific Search

`POST /search/entities/{entity_type}`

Optimized search for specific entity types:

- `/search/entities/people` - Search People & Contacts
- `/search/entities/tasks` - Search Actionable Tasks
- `/search/entities/documents` - Search Documents & Evidence
- `/search/entities/organizations` - Search Organizations & Bodies
- `/search/entities/events` - Search Key Places & Events

```bash
# Example: Find all engineers named Alice
curl -X POST "http://localhost:8001/search/entities/people?query=Alice%20engineer" \
  -H "Authorization: Bearer your-api-key"
```

### Semantic Search

`POST /search/semantic`

Advanced semantic search with context awareness:

```json
{
  "query": "Who worked on the ML pipeline?",
  "context": "Looking for the engineering team members",
  "enable_learning": true
}
```

Features:
- Context-aware search refinement
- Relationship analysis
- Concept matching
- Query learning (when enabled)

### Search Suggestions

`GET /search/suggestions`

Get intelligent search suggestions:

```bash
# Get suggestions for partial query
curl "http://localhost:8001/search/suggestions?q=eng&limit=10" \
  -H "Authorization: Bearer your-api-key"
```

Returns:
- Query completions
- Related entities
- Common searches

## Search Features

### Natural Language Queries

The Search API understands various query formats:

```
"Who is Alice Johnson?"                    # Find person
"What tasks are assigned to engineering?"   # Find tasks by department
"Documents from Q4 2023"                   # Find by date
"meeting about machine learning"           # Contextual search
"alice.johnson@example.com"               # Direct entity search
```

### Fuzzy Matching

Handles typos and variations automatically:

- "Alise" finds "Alice"
- "enginer" finds "engineer"
- "machne lerning" finds "machine learning"

### Entity Recognition

Automatically detects and prioritizes:
- Email addresses
- Phone numbers
- Dates (various formats)
- URLs
- Mentions (@username)
- Currency amounts

### Field Weighting

Important fields get higher relevance scores:

```python
default_weights = {
    'properties.Title': 2.0,      # Titles most important
    'properties.Name': 2.0,       # Names highly weighted
    'properties.Description': 1.5, # Descriptions moderately weighted
    'properties.Content': 1.0,    # Content baseline weight
    'properties.Tags': 1.8,       # Tags help categorization
}
```

### Highlighting

Search results include highlighted snippets:

```json
{
  "entity": {...},
  "score": 0.95,
  "highlights": {
    "properties.Title": [
      "...Implement machine learning pipeline for..."
    ],
    "properties.Description": [
      "...using advanced ML techniques to predict..."
    ]
  },
  "explanation": "Exact match for 'machine learning'; Contains entity: alice.johnson@example.com"
}
```

## Query Syntax

### Basic Queries

```
machine learning              # All words (any order)
"machine learning"           # Exact phrase
alice OR bob                # Either term
engineering -sales          # Exclude term
eng*                       # Prefix matching
```

### Advanced Queries

```
type:person Alice           # Search specific entity type
status:"In Progress"        # Search by field value
created:2024-01-*          # Date patterns
score:>0.8                 # Minimum score filter
```

## Performance

The Search API is optimized for speed:

- **Indexing**: Automatic field indexing
- **Caching**: Results cached for repeated queries
- **Parallel Search**: Multi-database searches run concurrently
- **Early Termination**: Stops when enough high-quality results found

Typical performance:
- 10K records: <200ms
- 100K records: <500ms
- 1M records: <2s

## Examples

### Finding People

```python
# Find engineers named Alice
response = requests.post(
    "http://localhost:8001/search/universal",
    json={
        "query": "Alice engineer",
        "databases": ["People & Contacts"],
        "enable_semantic": True
    },
    headers={"Authorization": "Bearer api-key"}
)
```

### Complex Multi-Database Search

```python
# Find everything related to Q4 machine learning work
response = requests.post(
    "http://localhost:8001/search/universal",
    json={
        "query": "Q4 machine learning pipeline progress",
        "max_results": 100,
        "include_explanations": True
    },
    headers={"Authorization": "Bearer api-key"}
)

# Results will include:
# - People working on ML
# - Tasks related to ML pipeline
# - Documents mentioning ML
# - Meetings about ML progress
```

### Typo-Tolerant Search

```python
# Even with typos, finds correct results
response = requests.post(
    "http://localhost:8001/search/universal",
    json={
        "query": "quartely enginerring reprt",  # Multiple typos
        "enable_fuzzy": True
    },
    headers={"Authorization": "Bearer api-key"}
)
# Still finds "Quarterly Engineering Report"
```

### Intent-Based Search

```python
# Different intents trigger optimized search strategies
queries = [
    "Who is the engineering manager?",      # Person search
    "What tasks are overdue?",              # Task search with filter
    "Find the Q4 financial report",         # Document search
    "When is the next team meeting?",       # Event search
    "How many people in sales?"             # Count query
]
```

## Best Practices

1. **Use Natural Language**: Write queries as you would ask a colleague
2. **Be Specific**: Include relevant context for better results
3. **Leverage Fuzzy Matching**: Don't worry about exact spelling
4. **Use Quotes Sparingly**: Only for exact phrases
5. **Check Suggestions**: Use the suggestions endpoint for better queries
6. **Enable Explanations**: During development to understand scoring
7. **Set Appropriate Limits**: Balance performance with completeness

## Configuration

The Search API behavior can be customized:

```python
# Custom field weights for domain-specific search
config = {
    "field_weights": {
        "properties.CustomField": 3.0,
        "properties.ImportantTag": 2.5
    },
    "enable_fuzzy": True,
    "fuzzy_threshold": 0.8,
    "enable_stemming": True,
    "synonym_expansion": True
}
```

## Error Handling

The Search API provides detailed error information:

```json
{
  "error": "invalid_query",
  "message": "Query syntax error: Unclosed quote",
  "details": {
    "position": 25,
    "suggestion": "Add closing quote or remove opening quote"
  }
}
```

Common errors:
- `400` - Invalid query syntax
- `404` - Database not found
- `429` - Rate limit exceeded
- `500` - Internal search error

## Future Enhancements

Planned improvements:

1. **Vector Search** - Semantic embeddings for similarity
2. **Multi-lingual** - Search in multiple languages
3. **Search Analytics** - Learn from user behavior
4. **Custom Analyzers** - Domain-specific text processing
5. **Real-time Indexing** - Instant search for new data