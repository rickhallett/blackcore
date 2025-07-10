# Product Requirements Document: Minimal Transcript Processor

**Version:** 1.0  
**Date:** January 9, 2025  
**Author:** Development Team  
**Branch:** minimal

## Executive Summary

This PRD defines a streamlined transcript processing module that focuses exclusively on the core workflow: ingesting transcripts, extracting information via AI, and updating Notion databases. This minimal implementation maintains high code quality and test coverage while eliminating enterprise-grade complexity that isn't needed for campaign information management.

## Problem Statement

The current blackcore implementation includes extensive enterprise features (distributed rate limiting, complex abstractions, full security stack) that add unnecessary complexity for the primary use case of processing meeting transcripts and updating campaign information in Notion. We need a focused solution that:

1. Processes transcripts reliably
2. Extracts entities and relationships using AI
3. Updates Notion databases accurately
4. Maintains high test coverage (90%+)
5. Supports all Notion property types
6. Remains simple to understand and maintain

## Solution Overview

Create a new `blackcore/minimal/` module that implements only the essential pipeline components with a focus on simplicity, reliability, and testability.

### Core Workflow

```
Transcript Input → AI Extraction → Entity Resolution → Notion Update
      ↓                  ↓                ↓                 ↓
   JSON/Text      Claude/OpenAI    Local Cache      Direct API
```

## Functional Requirements

### 1. Transcript Ingestion
- Accept transcripts in JSON or plain text format
- Support batch processing of multiple transcripts
- Validate input format and content
- Handle various transcript sources (voice memos, meeting notes, etc.)

### 2. AI Entity Extraction
- Integrate with Claude or OpenAI for entity extraction
- Extract people, organizations, events, tasks, and transgressions
- Identify relationships between entities
- Generate summaries and key insights
- Support custom extraction prompts

### 3. Notion Database Updates
- Create new entries in appropriate databases
- Update existing entries based on matching criteria
- Establish relationships between entities
- Support all Notion property types:
  - Title, Rich Text
  - Number, Select, Multi-select
  - Date, People, Files
  - Checkbox, URL, Email, Phone
  - Relation, Formula, Rollup
  - Created/Last Edited Time
  - Created/Last Edited By

### 4. Configuration Management
- JSON-based configuration for database mappings
- Environment variables for API keys
- Configurable AI prompts
- Database schema definitions

### 5. Error Handling
- Graceful handling of API failures
- Retry logic with exponential backoff
- Clear error messages and logging
- Transaction-like behavior (all or nothing updates)

## Non-Functional Requirements

### 1. Performance
- Process a typical transcript (5-10 pages) in under 30 seconds
- Handle rate limits gracefully (3 requests/second for Notion)
- Minimize API calls through intelligent batching

### 2. Reliability
- 90%+ test coverage across all modules
- Comprehensive error handling
- Idempotent operations (safe to retry)
- Local caching to prevent data loss

### 3. Usability
- Simple command-line interface
- Clear documentation with examples
- Minimal configuration required to start
- Helpful error messages

### 4. Maintainability
- Clean, well-documented code
- Single responsibility principle
- Minimal external dependencies
- Easy to extend with new entity types

## Technical Architecture

### Module Structure

```
blackcore/minimal/
├── __init__.py
├── transcript_processor.py    # Main orchestrator
├── ai_extractor.py           # AI integration
├── notion_updater.py         # Notion API wrapper
├── property_handlers.py      # All property type handlers
├── models.py                 # Data models
├── config.py                 # Configuration
├── cache.py                  # Simple local cache
├── utils.py                  # Helper functions
└── tests/
    ├── __init__.py
    ├── test_transcript_processor.py
    ├── test_ai_extractor.py
    ├── test_notion_updater.py
    ├── test_property_handlers.py
    ├── test_models.py
    ├── test_cache.py
    └── fixtures/
        ├── sample_transcript.json
        ├── sample_config.json
        └── mock_responses.py
```

### Key Components

#### 1. TranscriptProcessor (transcript_processor.py)
```python
class TranscriptProcessor:
    """Main orchestrator for transcript processing pipeline."""
    
    def process_transcript(self, transcript: dict) -> ProcessingResult:
        """Process a single transcript through the pipeline."""
    
    def process_batch(self, transcripts: List[dict]) -> BatchResult:
        """Process multiple transcripts."""
```

#### 2. AIExtractor (ai_extractor.py)
```python
class AIExtractor:
    """Extract entities and relationships using AI."""
    
    def extract_entities(self, text: str) -> ExtractedEntities:
        """Extract all entities from transcript text."""
    
    def identify_relationships(self, entities: ExtractedEntities) -> List[Relationship]:
        """Identify relationships between entities."""
```

#### 3. NotionUpdater (notion_updater.py)
```python
class NotionUpdater:
    """Simplified Notion API client for updates."""
    
    def create_page(self, database_id: str, properties: dict) -> Page:
        """Create a new page in a database."""
    
    def update_page(self, page_id: str, properties: dict) -> Page:
        """Update an existing page."""
    
    def find_page(self, database_id: str, query: dict) -> Optional[Page]:
        """Find a page by properties."""
```

#### 4. PropertyHandlers (property_handlers.py)
```python
# All property handlers in one file for simplicity
class PropertyHandler(ABC):
    """Base property handler."""

class TextPropertyHandler(PropertyHandler):
    """Handle text and title properties."""

class SelectPropertyHandler(PropertyHandler):
    """Handle select and multi-select properties."""

# ... all other property types
```

### Data Flow

1. **Input Stage**
   - Load transcript from file or API
   - Validate format and required fields
   - Extract metadata (date, source, participants)

2. **AI Processing Stage**
   - Send transcript to AI with extraction prompt
   - Parse AI response for entities
   - Validate extracted data
   - Cache results locally

3. **Entity Resolution Stage**
   - Check if entities already exist in Notion
   - Merge with existing data if found
   - Prepare creation/update operations

4. **Update Stage**
   - Execute Notion API calls with rate limiting
   - Establish relationships between entities
   - Update transcript status
   - Log results

## Configuration Schema

```json
{
  "notion": {
    "api_key": "NOTION_API_KEY",
    "databases": {
      "people": {
        "id": "database-id",
        "mappings": {
          "name": "Full Name",
          "role": "Role",
          "organization": "Organization"
        }
      },
      "organizations": {
        "id": "database-id",
        "mappings": {
          "name": "Organization Name",
          "category": "Category"
        }
      }
    }
  },
  "ai": {
    "provider": "claude",
    "api_key": "AI_API_KEY",
    "model": "claude-3-sonnet-20240229",
    "extraction_prompt": "Extract all people, organizations..."
  },
  "processing": {
    "batch_size": 10,
    "rate_limit": 3,
    "retry_attempts": 3,
    "cache_ttl": 3600
  }
}
```

## Usage Examples

### Basic Usage
```bash
# Process a single transcript
python -m blackcore.minimal process transcript.json

# Process a batch of transcripts
python -m blackcore.minimal process-batch ./transcripts/

# Dry run (preview without updating)
python -m blackcore.minimal process transcript.json --dry-run
```

### Python API
```python
from blackcore.minimal import TranscriptProcessor

# Initialize processor
processor = TranscriptProcessor(config_path="config.json")

# Process single transcript
result = processor.process_transcript({
    "title": "Meeting with Mayor",
    "date": "2024-01-09",
    "content": "Discussed beach hut survey concerns..."
})

# Check results
print(f"Created {len(result.created)} entities")
print(f"Updated {len(result.updated)} entities")
print(f"Errors: {len(result.errors)}")
```

## Testing Strategy

### Unit Tests (90% coverage minimum)
- Test each component in isolation
- Mock external API calls
- Verify error handling
- Test all property type handlers

### Integration Tests
- Test full pipeline with mock APIs
- Verify entity relationship creation
- Test batch processing
- Verify transaction behavior

### Example Test
```python
def test_transcript_processing():
    """Test full transcript processing pipeline."""
    processor = TranscriptProcessor(config=test_config)
    
    result = processor.process_transcript(sample_transcript)
    
    assert result.success
    assert len(result.created) == 3  # Mayor, Council, Meeting
    assert len(result.relationships) == 2  # Mayor->Council, Meeting->Mayor
    assert result.transcript_updated
```

## Success Metrics

1. **Functionality**
   - Successfully process 95%+ of transcripts
   - Accurate entity extraction (90%+ precision)
   - Correct relationship mapping

2. **Reliability**
   - Zero data loss during processing
   - Graceful handling of all API errors
   - 90%+ test coverage maintained

3. **Performance**
   - Average processing time < 30 seconds
   - Batch processing at 100+ transcripts/hour
   - Minimal API calls through caching

4. **Usability**
   - Setup time < 10 minutes
   - Clear error messages
   - Comprehensive documentation

## Implementation Timeline

### Week 1: Core Implementation
- Days 1-2: Create module structure and models
- Days 3-4: Implement transcript processor and AI extractor
- Days 5-7: Implement Notion updater and property handlers

### Week 2: Testing and Polish
- Days 8-9: Write comprehensive test suite
- Days 10-11: Add caching and error handling
- Days 12-13: Documentation and examples
- Day 14: Final testing and code review

## Out of Scope

The following features are explicitly excluded from this minimal implementation:

1. **Enterprise Features**
   - Distributed rate limiting
   - Complex authentication/authorization
   - Metrics and monitoring
   - Admin UI

2. **Advanced Architecture**
   - Repository pattern
   - Service layers
   - Dependency injection
   - Event-driven architecture

3. **Performance Optimizations**
   - Redis caching
   - Async/await
   - Connection pooling
   - Worker queues

4. **Additional Functionality**
   - Web API endpoints
   - Real-time processing
   - Webhook support
   - Multi-tenant support

These features can be added later if needed, but are not required for the core use case of campaign information management.

## Conclusion

This minimal transcript processor provides a focused, reliable solution for the specific use case of processing campaign-related transcripts and updating Notion databases. By eliminating unnecessary complexity while maintaining high code quality and test coverage, we can deliver a working solution in approximately 2 weeks that meets all core requirements.

The modular design allows for future enhancements if needed, but the initial implementation remains deliberately simple and focused on the essential workflow.