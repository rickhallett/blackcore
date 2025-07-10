# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Blackcore is a Python-based intelligence processing and automation system for "Project Nassau" that interfaces with Notion workspaces to create structured knowledge graphs from raw intelligence data.

## Development Commands

### Setup
```bash
# Install dependencies
uv sync

# Set up environment variables
cp .env.example .env
# Then edit .env with your API keys
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
```

### Main Scripts
```bash
# Initialize Notion databases
python scripts/setup_databases.py
# Or using uv script alias:
uv run setup-databases

# Verify database configuration
python scripts/verify_databases.py
# Or:
uv run verify-databases

# Process new intelligence
python scripts/process_intelligence.py
# Or:
uv run process-intelligence

# Discover and configure Notion workspace
python scripts/discover_and_configure.py

# Sync data between local JSON and Notion
python scripts/notion_sync.py

# Analyze database relationships
python scripts/analyse_relations.py
```

## Architecture

### Core Components
The project follows a clean, layered architecture:

1. **Property Handlers** (`blackcore/handlers/`) - Type-specific handlers for all Notion property types (text, select, multi_select, relation, etc.)
2. **Repository Layer** (`blackcore/repositories/`) - Data access abstraction using repository pattern with base classes for CRUD operations
3. **Service Layer** (`blackcore/services/`) - Business logic including sync services and domain-specific operations
4. **Notion Client** (`blackcore/notion/`) - Custom Notion API wrapper with database creators and client abstraction
5. **Security Module** (`blackcore/security/`) - Comprehensive security with secrets management, validators, and audit logging
6. **Rate Limiting** (`blackcore/rate_limiting/`) - Thread-safe rate limiting for API calls with configurable limits
7. **Error Handling** (`blackcore/errors/`) - Custom exception hierarchy for graceful error handling

### Database Schema
The system uses 8 interconnected Notion databases:
- **People & Contacts** - Individual tracking with relationships
- **Organizations & Bodies** - Institutional entities
- **Agendas & Epics** - Strategic goals and initiatives
- **Actionable Tasks** - Operational task management
- **Intelligence & Transcripts** - Raw data repository
- **Documents & Evidence** - File and document library
- **Key Places & Events** - Location and event tracking
- **Identified Transgressions** - Issue and violation catalog

### Development Principles
1. Test-Driven Development (TDD) - Write tests before implementation
2. Incremental approach - Start with Phase 0 (foundation), then Phase 1 (read), Phase 2 (write)
3. Human-in-the-Middle verification - AI suggests, human approves
4. API-first but abstracted - Hide Notion API complexity behind clean interfaces

### Environment Variables
Required in `.env`:
- `NOTION_API_KEY` - Notion integration token
- `NOTION_PARENT_PAGE_ID` - Parent page for database creation
- `ANTHROPIC_API_KEY` - Claude API key (optional)
- `GOOGLE_API_KEY` - Gemini API key (optional)
- `GOOGLE_DRIVE_FOLDER_ID` - Source folder for intelligence data

### Key Development Tasks
When implementing features:
1. Check the roadmap in `specs/roadmap.md` for current phase requirements
2. Reference `specs/db-relations.md` for database schema details
3. Follow TDD approach - write tests in `tests/` before implementation
4. Use type hints and Pydantic models for data validation
5. Keep AI prompts in separate files for maintainability

### Current Phase
The project is in Phase 0 (Foundation & Schema Automation) focusing on:
- Database schema creation and validation
- Basic Notion API wrapper implementation
- Test infrastructure setup
- Configuration discovery and management

## Key Architectural Patterns

### Repository Pattern
All data access goes through repository classes that inherit from `BaseRepository`:
```python
# Example: PersonRepository inherits from BaseRepository
# Provides standard CRUD operations plus custom queries
```

### Property Handler System
Each Notion property type has a dedicated handler:
- `TextPropertyHandler` - Plain text fields
- `SelectPropertyHandler` - Single select options
- `RelationPropertyHandler` - Database relations
- Custom handlers for each Notion property type

### Testing Strategy
- **Fixtures**: Comprehensive fixtures in `tests/conftest.py` for mock clients and test data
- **Test Organization**: Tests mirror source structure (e.g., `blackcore/security/` → `tests/test_security.py`)
- **Async Testing**: Full support for async tests with `pytest-asyncio`
- **Mock Strategy**: Use fixtures for Notion client mocking to avoid API calls in tests

### Error Handling
Custom exception hierarchy in `blackcore/errors/`:
- `BlackcoreError` - Base exception
- `ConfigurationError` - Configuration issues
- `ValidationError` - Data validation failures
- `NotionAPIError` - Notion API specific errors