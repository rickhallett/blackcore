# Minimal Transcript Processor

A streamlined Python module for processing transcripts, extracting entities using AI, and updating Notion databases. This minimal implementation focuses on the core workflow without enterprise complexity.

## Features

- 📝 **Transcript Processing**: Load transcripts from JSON or text files
- 🤖 **AI Entity Extraction**: Extract people, organizations, tasks, and more using Claude or OpenAI
- 📊 **Notion Integration**: Automatically create and update entries in Notion databases
- 🔧 **All Property Types**: Support for all Notion property types (text, select, relations, etc.)
- 💾 **Simple Caching**: File-based caching to reduce API calls
- 🔄 **JSON Sync**: Sync local JSON data files directly to Notion databases without AI processing
- ⚡ **High Test Coverage**: Comprehensive test suite with 90%+ coverage target

## Quick Start

### 1. Installation

```bash
# Install required dependencies
pip install notion-client anthropic  # or openai for OpenAI

# Or add to your requirements.txt:
notion-client>=2.2.1
anthropic>=0.8.0  # For Claude
# openai>=1.0.0   # For OpenAI
```

### 2. Configuration

Create a configuration file or use environment variables:

```bash
# Environment variables
export NOTION_API_KEY="your_notion_api_key"
export ANTHROPIC_API_KEY="your_claude_api_key"  # or OPENAI_API_KEY

# Database IDs (get from Notion URLs)
export NOTION_DB_PEOPLE_ID="your_people_database_id"
export NOTION_DB_ORGANIZATIONS_ID="your_org_database_id"
export NOTION_DB_TASKS_ID="your_tasks_database_id"
export NOTION_DB_TRANSCRIPTS_ID="your_transcripts_database_id"
```

Or create a `config.json` file:

```json
{
  "notion": {
    "api_key": "your_notion_api_key",
    "databases": {
      "people": {
        "id": "your_people_database_id",
        "mappings": {
          "name": "Full Name",
          "role": "Role",
          "organization": "Organization"
        }
      }
    }
  },
  "ai": {
    "provider": "claude",
    "api_key": "your_ai_api_key"
  }
}
```

### 3. Basic Usage

```python
from blackcore.minimal import TranscriptProcessor, TranscriptInput

# Initialize processor
processor = TranscriptProcessor(config_path="config.json")

# Create transcript
transcript = TranscriptInput(
    title="Meeting with Mayor",
    content="Meeting discussed beach hut survey concerns...",
    date="2025-01-09"
)

# Process transcript
result = processor.process_transcript(transcript)

print(f"Created {len(result.created)} entities")
print(f"Updated {len(result.updated)} entities")
```

### 4. Batch Processing

```python
from blackcore.minimal.utils import load_transcripts_from_directory

# Load all transcripts from a directory
transcripts = load_transcripts_from_directory("./transcripts")

# Process in batch
batch_result = processor.process_batch(transcripts)

print(f"Processed {batch_result.total_transcripts} transcripts")
print(f"Success rate: {batch_result.success_rate:.1%}")
```

## CLI Usage

### Process a Single Transcript

```bash
python -m blackcore.minimal process transcript.json
```

### Process Multiple Transcripts

```bash
python -m blackcore.minimal process-batch ./transcripts/
```

### Dry Run Mode

```bash
python -m blackcore.minimal process transcript.json --dry-run
```

### Sync JSON Files to Notion

```bash
# Sync all JSON files to Notion databases
python -m blackcore.minimal sync-json

# Sync a specific database
python -m blackcore.minimal sync-json --database "People & Contacts"

# Dry run to preview changes
python -m blackcore.minimal sync-json --dry-run

# Verbose output
python -m blackcore.minimal sync-json --verbose
```

### Generate Config Template

```bash
python -m blackcore.minimal generate-config > config.json
```

## Transcript Format

### JSON Format

```json
{
  "title": "Meeting with Mayor - Beach Hut Survey",
  "content": "Full transcript text here...",
  "date": "2025-01-09T14:00:00",
  "source": "voice_memo",
  "metadata": {
    "location": "Town Hall",
    "duration_minutes": 45
  }
}
```

### Text Format

For `.txt` or `.md` files, the filename is used as the title and the entire content is processed.

```
Meeting-with-Mayor-2025-01-09.txt
```

## Entity Extraction

The AI extracts the following entity types:

- **People**: Names, roles, contact information
- **Organizations**: Company/organization names, categories
- **Tasks**: Action items with assignees and due dates
- **Transgressions**: Issues or violations identified
- **Events**: Meetings, dates, locations
- **Documents**: Referenced documents or evidence

## Database Mapping

Configure how entities map to your Notion databases:

```json
{
  "people": {
    "name": "Full Name",        // Your Notion property name
    "role": "Role",
    "email": "Email Address",
    "organization": "Company"
  }
}
```

## Advanced Features

### Custom AI Prompts

```python
custom_prompt = """
Extract entities focusing on:
1. Financial transactions
2. Legal violations
3. Key decision makers

Format as JSON with confidence scores.
"""

result = processor.process_transcript(
    transcript,
    ai_prompt=custom_prompt
)
```

### Caching

The processor automatically caches AI extraction results:

```python
# Clear cache
processor.cache.clear()

# View cache stats
stats = processor.cache.get_stats()
print(f"Cached entries: {stats['total_entries']}")
```

### Error Handling

```python
result = processor.process_transcript(transcript)

if not result.success:
    for error in result.errors:
        print(f"Error in {error.stage}: {error.message}")
```

## Testing

Run the test suite:

```bash
# Run all tests
pytest blackcore/minimal/tests/ -v

# Run with coverage
pytest blackcore/minimal/tests/ --cov=blackcore.minimal

# Run specific test file
pytest blackcore/minimal/tests/test_transcript_processor.py
```

## Architecture

```
blackcore/minimal/
├── transcript_processor.py  # Main orchestrator
├── ai_extractor.py         # AI integration (Claude/OpenAI)
├── notion_updater.py       # Notion API wrapper
├── property_handlers.py    # All Notion property types
├── models.py              # Pydantic data models
├── config.py              # Configuration management
├── cache.py               # Simple file-based cache
├── utils.py               # Helper functions
├── cli.py                 # Command-line interface
└── tests/                 # Comprehensive test suite
```

## Common Issues

### Rate Limiting

The module automatically handles Notion's rate limits (3 requests/second by default):

```python
# Adjust rate limit if needed
processor = TranscriptProcessor()
processor.notion_updater.rate_limiter.min_interval = 0.5  # 2 req/sec
```

### Large Transcripts

For very large transcripts, the AI might hit token limits:

```python
# Split large transcripts
if len(transcript.content) > 10000:
    # Process in chunks
    chunks = [transcript.content[i:i+8000] 
              for i in range(0, len(transcript.content), 8000)]
```

### Missing Database IDs

If you see warnings about missing database IDs:

1. Go to your Notion database
2. Copy the URL: `https://notion.so/workspace/database_id?v=...`
3. The database ID is the part before the `?`
4. Add to your config or environment variables

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

[Your License Here]