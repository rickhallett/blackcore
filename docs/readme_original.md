Of course. Here is a README for the `Blackcore` repository, written to be both descriptive and evocative of the # Blackcore

> The Intelligence Processing & Automation Engine for Project Nassau.

## 1. Overview

Blackcore is a Python-based intelligence processing system that interfaces with Notion workspaces to create structured knowledge graphs from raw intelligence data. It provides a secure, scalable foundation for transforming unstructured information into actionable insights.

The system emphasizes security-first design, robust error handling, and enterprise-grade reliability while maintaining the flexibility to adapt to evolving intelligence requirements.

## 2. Core Philosophy

This project operates on the principle that victory is achieved not through brute force alone, but through superior intelligence and flawless execution. While Notion serves as our central map room and database, Blackcore provides the instruments to work that data.

This codebase is built to:
*   **Systemize Intelligence:** Convert raw, unstructured data (voice transcripts, meeting notes) into structured, relational objects.
*   **Automate Analysis:** Leverage AI APIs to perform deep analysis on documents and data that would be too time-consuming for a human crew.
*   **Create Connections:** Programmatically build and maintain the relationships between people, organizations, places, events, and transgressions, revealing patterns and opportunities that might otherwise be missed.
*   **Maintain Operational Rhythm:** Provide the tools to ensure our strategic actions are perfectly synchronized with our intelligence-gathering efforts.

## 3. Key Components (Implemented)

### Security Layer
*   **Secrets Manager:** Encrypted storage and rotation of API keys with audit logging
*   **URL Validator:** SSRF prevention with private IP blocking and domain whitelisting
*   **Input Sanitizer:** Protection against injection attacks with HTML escaping
*   **Audit Logger:** Comprehensive security event tracking with sensitive data redaction

### Error Handling Framework
*   **Contextual Error System:** Rich error context preservation for debugging
*   **Retry Logic:** Intelligent retry with exponential backoff for transient failures
*   **Rate Limit Handling:** Automatic detection and handling of API rate limits
*   **User-Friendly Messages:** Clear error messages for common issues

### Property Handlers
*   **Type-Safe Handler Registry:** Automatic registration and validation of property types
*   **Comprehensive Type Support:** Title, Rich Text, Number, Select, Multi-Select, Date, People, Files, Checkbox, URL, Email, Phone, Relation, Formula, Rollup, and timestamp handlers
*   **Bidirectional Conversion:** Seamless conversion between Notion API format and Python objects

### Repository Pattern
*   **Page Repository:** CRUD operations for Notion pages with batch support
*   **Database Repository:** Schema management and query operations
*   **Search Repository:** Unified search across workspaces with filtering

### Notion Integration
*   **Client Wrapper:** Rate-limited API client with automatic retries
*   **Response Validation:** Pydantic models for type-safe API responses
*   **Pagination Support:** Automatic handling of large result sets

### The Minimal Module (MVP)
The `blackcore.minimal` module represents the current MVP implementation focused on core intelligence processing:

*   **Transcript Processing:** Ingests audio/text transcripts and extracts structured data
*   **Entity Identification:** Automatically identifies new unique database entries (People, Organizations, Places, Core Documents, etc.)
*   **Workspace Synchronization:** Maintains a local mapping of the current Notion workspace for efficient querying
*   **Relationship Management:** Identifies and creates schema-defined relationships (e.g., "Gary Suttle" as member of "Swanage Town Council")
*   **Bidirectional Sync:** Supports both Notion-to-JSON and JSON-to-Notion synchronization
*   **Query Engine Foundation:** Developing a comprehensive query system to retrieve blocks of information for intelligence creation
*   **Intelligence Pipeline Architecture:** Designed to support configurable data analysis pipelines with structured prompt templates

## 4. The Intelligence Workflow

The workflow enabled by Blackcore is designed to be a continuous, cyclical process:

1.  **Capture:** The Strategist records raw intelligence on the go.
2.  **Structure:** The Technician, aided by Blackcore scripts, parses this intelligence, creating and linking the relevant objects within our Notion databases.
3.  **Analyze:** Blackcore sends the structured data to our AI models for deep analysis, research, and prompt-driven content creation.
4.  **Enrich:** The AI's output is then programmatically written back into Notion, enriching our knowledge graph with new insights, summaries, and actionable tasks.

This loop ensures we are constantly refining our intelligence and adapting our strategy based on the most current information available.

### Intelligence Engine Vision

The Minimal module is evolving into a comprehensive intelligence engine that automates much of the repetitive prompt engineering work:

*   **Automated Analysis Pipelines:** Eliminating manual Chain of Experts, LLM vs LLM, and multishot prompting through configurable pipelines
*   **Structured Prompt Templates:** Different types of data analysis with structure defined in reusable templates
*   **Pipeline Configuration:** Preconfigured pipelines specified in config files that define:
    - Which prompts are called
    - What information is provided to each prompt
    - The sequence and timing of prompt execution
*   **Custom Pipeline Support:** Ability to create ad-hoc pipelines for specific analysis needs
*   **Intelligence Products:** Automated generation of:
    - Important changes over time reports
    - Undiscovered data relationship analysis
    - Document production workflows
    - Strategic intelligence briefings

## 5. Installation & Setup

### Prerequisites
- Python 3.11+
- uv (recommended) or pip

### Quick Start
```bash
# Clone the repository
git clone https://github.com/yourusername/blackcore.git
cd blackcore

# Install dependencies
uv sync  # or: pip install -e .

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys:
# - BLACKCORE_MASTER_KEY (REQUIRED - see security docs)
# - NOTION_API_KEY
# - NOTION_PARENT_PAGE_ID
# - ANTHROPIC_API_KEY (optional)
# - GOOGLE_API_KEY (optional)

# Generate secure master key
python scripts/generate_master_key.py --save

# Run tests to verify installation
pytest
```

### Database Setup
```bash
# Initialize Notion databases
python scripts/setup_databases.py

# Verify configuration
python scripts/verify_databases.py
```

### Minimal Module Quick Start
```bash
# Process a single transcript
python -m blackcore.minimal process transcript.json

# Batch process transcripts
python -m blackcore.minimal process-batch ./transcripts/

# Sync JSON data to Notion
python -m blackcore.minimal sync-json

# Run in dry-run mode to preview changes
python -m blackcore.minimal process transcript.json --dry-run
```

## 6. Development

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=blackcore

# Run specific test file
pytest tests/test_security.py -v
```

### Code Quality
```bash
# Lint code
ruff check .

# Format code
ruff format .

# Fix auto-fixable issues
ruff check --fix .
```

### Architecture Principles
- **Security First:** All external inputs validated, secrets encrypted
- **Test-Driven Development:** Comprehensive test coverage (>94%)
- **Type Safety:** Full type hints with Pydantic validation
- **Error Resilience:** Graceful handling of API failures
- **Audit Trail:** Complete logging of security-relevant events

## 7. Current Status

### Phase 0 Complete ✓
- Core security infrastructure implemented
- Error handling framework operational
- Property handlers for all Notion types
- Repository pattern with full CRUD support
- 112/112 tests passing

### Minimal Module (MVP) Status
- **Transcript Processing:** Fully functional with JSON/text support
- **Entity Extraction:** Working with Claude and OpenAI APIs
- **Notion Integration:** All property types supported
- **Relationship Management:** One-way relationships implemented
- **JSON Sync:** Bidirectional sync operational
- **Test Coverage:** 90%+ coverage achieved
- **CLI Interface:** Complete with batch processing

### Query Engine (In Development)
- **Workspace Mapping:** Local JSON cache of all Notion data
- **Query Interface:** Foundation for retrieving information blocks
- **Relationship Traversal:** Navigate connected entities
- **Data Aggregation:** Combine related information for analysis

### Intelligence Pipeline (Planned)
- **Prompt Template System:** Structured templates for different analyses
- **Pipeline Configuration:** YAML/JSON-based pipeline definitions
- **Execution Engine:** Sequential and parallel prompt execution
- **Result Aggregation:** Combine outputs from multiple prompts
- **Custom Pipelines:** User-defined analysis workflows

### Next Steps (Phase 1)
- Complete query engine implementation
- Build intelligence pipeline infrastructure
- Create preconfigured analysis pipelines
- Implement temporal analysis capabilities
- Add document generation workflows

## 8. Security Considerations

Blackcore implements defense-in-depth security:
- Encrypted secrets storage with key rotation
- SSRF protection blocking private networks
- Input sanitization preventing injection attacks
- Comprehensive audit logging with PII redaction
- Rate limiting to prevent API abuse

## 9. Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## 10. License

[License details here]

---
*Built with security, reliability, and operational excellence in mind.*