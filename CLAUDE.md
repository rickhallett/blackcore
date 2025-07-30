# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Blackcore is a Python-based intelligence processing and automation system for "Project Nassau" that interfaces with Notion workspaces to create structured knowledge graphs from raw intelligence data. The system emphasizes security-first design, robust error handling, and enterprise-grade reliability.

## Development Commands

### Setup
```bash
# Install dependencies (Python 3.11+ required)
uv sync

# Alternative installation
pip install -e .

# Set up environment variables
cp .env.example .env
# Edit .env with required API keys

# Generate secure master key (REQUIRED)
python scripts/generate_master_key.py
# Or manually: python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_filename.py

# Run specific test function
pytest tests/test_filename.py::test_function_name

# Run with coverage
pytest --cov=blackcore

# Run tests with verbose output
pytest -v

# Run tests matching a pattern
pytest -k "test_pattern"

# Run async tests (automatically handled by pytest-asyncio)
pytest tests/test_async.py

# Run minimal module tests
cd blackcore/minimal && make test
# Or specific minimal tests:
make test-unit
make test-integration
make test-coverage
make test-performance
```

### Code Quality
```bash
# Run linter
ruff check .

# Format code
ruff format .

# Fix auto-fixable linting issues
ruff check --fix .

# Check specific files/directories
ruff check blackcore/security/

# Lint and format in one command
ruff format . && ruff check --fix .
```

### Main Scripts

#### Database Management
```bash
# Initialize Notion databases
python scripts/setup/setup_databases.py
# Or using uv script alias:
uv run setup-databases

# Verify database configuration
python scripts/setup/verify_databases.py
# Or:
uv run verify-databases

# Discover and configure Notion workspace
python scripts/setup/discover_and_configure.py
```

#### Data Processing
```bash
# Process new intelligence
python scripts/process_intelligence.py
# Or:
uv run process-intelligence

# Ingest new intelligence data
python scripts/data_processing/ingest_intelligence.py

# Analyze database relationships
python scripts/data_processing/analyse_relations.py

# Run minimal transcript processor
python -m blackcore.minimal
```

#### Synchronization
```bash
# Sync data between local JSON and Notion
python scripts/sync/notion_sync.py

# Production sync with staging
python scripts/sync/sync_production_staged.py

# Verify sync completion
python scripts/sync/verify_sync_completion.py
```

#### Deduplication
```bash
# Run interactive deduplication CLI
python scripts/deduplication/dedupe_cli.py

# Or use the launcher script:
./scripts/utilities/run_interactive_dedupe.sh

# Run with specific mode
python scripts/deduplication/dedupe_cli.py --mode standard

# Test deduplication system
python scripts/deduplication/test_deduplication_system.py
```

## Architecture

### Core Components

1. **Security Layer** (`blackcore/security/`)
   - Encrypted secrets management with rotation capabilities
   - SSRF protection with private IP blocking
   - Input sanitization against injection attacks
   - Comprehensive audit logging with PII redaction

2. **Property Handlers** (`blackcore/handlers/`)
   - Type-specific handlers for all 15+ Notion property types
   - Bidirectional conversion between Notion API and Python objects
   - Automatic registration system with validation

3. **Repository Layer** (`blackcore/repositories/`)
   - Clean data access abstraction using repository pattern
   - Page, Database, and Search repositories
   - Type-safe CRUD operations with batch support

4. **Service Layer** (`blackcore/services/`)
   - Business logic including sync services
   - Domain-specific operations
   - AI integration for entity extraction

5. **Notion Client** (`blackcore/notion/`)
   - Rate-limited API wrapper with automatic retries
   - Database schema creators
   - Response validation with Pydantic models

6. **Error Handling** (`blackcore/errors/`)
   - Contextual error system preserving debugging info
   - Intelligent retry logic with exponential backoff
   - User-friendly error messages

7. **Rate Limiting** (`blackcore/rate_limiting/`)
   - Thread-safe rate limiting for API calls
   - Configurable limits per endpoint
   - Automatic backoff handling

8. **Deduplication System** (`blackcore/deduplication/`)
   - Interactive CLI with multiple modes (simple, standard, expert)
   - AI-powered similarity scoring with LLM analysis
   - Graph-based relationship analysis
   - Audit system with SQLite persistence
   - Real-time progress tracking and match review

### Database Schema

The system manages 14 interconnected Notion databases:
- **People & Contacts** - Individual tracking with relationships
- **Organizations & Bodies** - Institutional entities
- **Agendas & Epics** - Strategic goals and initiatives
- **Actionable Tasks** - Operational task management
- **Intelligence & Transcripts** - Raw data repository
- **Documents & Evidence** - File and document library
- **Key Places & Events** - Location and event tracking
- **Identified Transgressions** - Issue and violation catalog
- **Plus 6 additional specialized databases**

Database configuration is stored in `blackcore/config/notion_config.json`.

### The Minimal Module

A self-contained transcript processing implementation at `blackcore/minimal/`:
- Streamlined architecture for easier adoption
- CLI interface with batch processing support
- Full test coverage target of 90%+
- Support for all Notion property types
- Simple file-based caching

### Development Workflow

1. **Capture**: Record raw intelligence (transcripts, documents)
2. **Structure**: Parse intelligence, create/link Notion objects
3. **Analyze**: AI extracts entities and relationships
4. **Enrich**: AI-generated insights written back to Notion

### Environment Variables

Required in `.env`:
- `BLACKCORE_MASTER_KEY` - **REQUIRED**: Master encryption key (see [Security Configuration Guide](docs/security-configuration.md))
- `NOTION_API_KEY` - Notion integration token
- `NOTION_PARENT_PAGE_ID` - Parent page for database creation
- `ANTHROPIC_API_KEY` - Claude API key (optional)
- `GOOGLE_API_KEY` - Gemini API key (optional)
- `GOOGLE_DRIVE_FOLDER_ID` - Source folder for intelligence data
- `OPENAI_API_KEY` - OpenAI API key (optional)
- `REDIS_URL` - Redis connection for distributed rate limiting (optional)

### Key Architectural Patterns

**Repository Pattern**
All data access through repository classes inheriting from `BaseRepository`:
- Standard CRUD operations
- Custom query methods
- Pagination handling
- Batch operations

**Property Handler System**
Each Notion property type has a dedicated handler:
- `TextPropertyHandler` - Plain text fields
- `SelectPropertyHandler` - Single select options
- `RelationPropertyHandler` - Database relations
- Plus handlers for all other Notion types

**Security-First Design**
- Defense-in-depth security model
- Input validation at all boundaries
- Encrypted storage for sensitive data
- Comprehensive audit trails

### Testing Strategy

- **Test Organization**: Tests mirror source structure
- **Fixtures**: Comprehensive fixtures in `tests/conftest.py`
- **Mock Strategy**: Notion client mocking to avoid API calls
- **Performance Tests**: Scalability testing included
- **Coverage Target**: 94%+ for critical paths
- **Test Categories**:
  - Unit tests: `tests/test_*.py`
  - Integration tests: `tests/integration/`
  - Performance tests: `tests/performance/`
  - Regression tests: `tests/regression/`
  - Workflow tests: `tests/workflows/`

### Current Development Phase

The project is in Phase 0 (Foundation & Schema Automation):
- Database schema creation and validation
- Basic Notion API wrapper implementation
- Test infrastructure setup
- Configuration discovery and management

Reference `specs/roadmap.md` for detailed phase requirements.

### Working with AI Integration

When implementing AI features:
1. Prompts are stored in separate files for maintainability
2. Support both Claude (Anthropic) and OpenAI APIs
3. Entity extraction focuses on: People, Organizations, Tasks, Places, Events, Transgressions
4. AI-generated content includes metadata for tracking

### Performance Considerations

- Local JSON caching reduces API calls
- Batch operations for bulk updates
- Rate limiting prevents API throttling
- Async support for concurrent operations
- Connection pooling for database operations

## Graphiti MCP Integration

The repository integrates with the Graphiti MCP (Model Context Protocol) server for temporally-aware knowledge graph management. Graphiti provides persistent memory and contextual awareness across conversations.

### What is Graphiti?

Graphiti is a framework for building and querying temporally-aware knowledge graphs, specifically designed for AI agents operating in dynamic environments. Unlike traditional RAG methods, Graphiti continuously integrates user interactions, structured and unstructured data into a coherent, queryable graph.

### Available MCP Tools

The Graphiti MCP server provides the following tools for knowledge graph operations:

**Episode Management:**
```python
# Add episodes to the knowledge graph
mcp__graphiti__add_episode(name, episode_body, format="text")

# Get recent episodes
mcp__graphiti__get_episodes(group_id=None, last_n=10)

# Delete episodes
mcp__graphiti__delete_episode(uuid)
```

**Search Operations:**
```python
# Search for relevant node summaries
mcp__graphiti__search_nodes(query, max_nodes=10)

# Search for relevant facts
mcp__graphiti__search_facts(query, max_facts=10)
```

**Entity Management:**
```python
# Get entity edge details
mcp__graphiti__get_entity_edge(uuid)

# Delete entity edges
mcp__graphiti__delete_entity_edge(uuid)
```

**Graph Management:**
```python
# Clear entire graph (requires authorization)
mcp__graphiti__clear_graph(auth=None)
```

### Integration with Blackcore Intelligence Processing

Graphiti enhances Blackcore's intelligence processing workflow:

1. **Capture Phase**: Raw intelligence (transcripts, documents) can be added as episodes
2. **Structure Phase**: Entities and relationships are automatically extracted and stored
3. **Analyze Phase**: Historical context from the knowledge graph informs AI analysis
4. **Enrich Phase**: Insights are stored back into the graph for future reference

### Best Practices

- Use descriptive episode names for better searchability
- Store intelligence transcripts as episodes with metadata
- Leverage search functions to find related entities before creating new ones
- Group related episodes using consistent group_id values
- Use the knowledge graph to maintain context across processing sessions

### Example Usage

```python
# Store a new intelligence transcript
await mcp__graphiti__add_episode(
    name="Intelligence Brief 2024-01-15",
    episode_body="Meeting transcript content...",
    format="text"
)

# Search for related entities
results = await mcp__graphiti__search_nodes(
    query="organization meeting participants",
    max_nodes=5
)

# Find relevant historical context
facts = await mcp__graphiti__search_facts(
    query="similar meetings or organizations",
    max_facts=10
)
```

## Deduplication CLI

The deduplication system provides an interactive CLI for identifying and merging duplicate records:

### Quick Start
```bash
# Run interactive CLI
python scripts/deduplication/dedupe_cli.py

# The CLI will guide you through:
# 1. Database selection
# 2. Threshold configuration (auto-merge: 90%, review: 70%)
# 3. AI settings (optional but recommended)
# 4. Analysis and review of matches
```

### Features
- **Safety Mode**: No automatic changes without approval
- **AI-Powered**: Optional LLM analysis for complex matches
- **Graph Analysis**: Understands relationships between entities
- **Audit Trail**: SQLite database tracks all operations
- **Interactive Review**: Approve/reject each match

### Deduplication Workflow
1. Select databases to analyze
2. Configure similarity thresholds
3. Run analysis (with optional AI enhancement)
4. Review proposed matches
5. Execute approved merges

## Debugging Scripts

Located in `scripts/debug/`:
- `debug_database_loading.py` - Troubleshoot database connection issues
- `debug_property_formatting.py` - Analyze property formatting problems
- `fix_property_formatting.py` - Repair property formatting issues

## Data Remediation

Tools for data cleanup and migration in `scripts/data_processing/`:
- `data_remediation.py` - Fix data inconsistencies
- `export_complete_notion.py` - Export all Notion data to JSON

## Project File Locations

- **Configuration**: `blackcore/config/notion_config.json`
- **Local Data**: `blackcore/models/json/` (database JSON files)
- **Test Data**: `testing/exports/`
- **Logs**: `logs/` (sync reports, debug logs)
- **Documentation**: `docs/` and `specs/`
- **Scripts**: `scripts/` (organized by function)

## Development Patterns

### Adding New Features
1. Create feature branch: `git checkout -b feature/your-feature`
2. Write tests first (TDD approach)
3. Implement feature
4. Ensure all tests pass
5. Run linting and formatting
6. Create PR to main branch

### Working with Notion Properties
1. Check existing handlers in `blackcore/handlers/`
2. Use property mappings from `blackcore/minimal/property_mappings.json`
3. Test with real Notion data using integration tests

### Async Operations
- Use `asyncio` for concurrent Notion API calls
- Implement proper rate limiting
- Handle network errors with retries

## Common Development Tasks

### Running a Single Test
```bash
pytest tests/test_specific.py::test_function_name -v
```

### Checking Test Coverage for a Module
```bash
pytest tests/test_module.py --cov=blackcore.module --cov-report=term-missing
```

### Running Deduplication Without AI
```bash
# Set empty API key to disable AI
ANTHROPIC_API_KEY="" python scripts/deduplication/dedupe_cli.py
```

### Syncing Specific Database
```bash
# Use the sync scripts with database filtering
python scripts/sync/notion_sync.py --database "People & Contacts"
```

### Validating Database Schema
```bash
python scripts/setup/verify_databases.py --detailed
```