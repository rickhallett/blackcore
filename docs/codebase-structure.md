# Blackcore Codebase Structure

## Project Overview
Blackcore is a Python-based intelligence processing and automation system for "Project Nassau" that interfaces with Notion workspaces to create structured knowledge graphs from raw intelligence data. The system emphasizes security-first design, robust error handling, and enterprise-grade reliability.

## Directory Structure

```
blackcore/
├── .claude/                    # Claude Code configuration
├── ai_docs/                    # AI-related documentation
│   ├── anthropic_quick_start.md
│   ├── claude_code_best_practices.md
│   └── examples/              # Code examples
├── blackcore/                  # Main package directory
│   ├── __init__.py
│   ├── config/                # Configuration files
│   │   └── notion_config.json
│   ├── errors/                # Error handling framework
│   │   ├── __init__.py
│   │   └── handlers.py        # Custom exception hierarchy
│   ├── handlers/              # Property type handlers
│   │   ├── base.py           # Base handler and registry
│   │   ├── checkbox.py       # Checkbox property handler
│   │   ├── date.py           # Date property handler
│   │   ├── files.py          # Files property handler
│   │   ├── formula.py        # Formula property handler
│   │   ├── number.py         # Number property handler
│   │   ├── people.py         # People property handler
│   │   ├── relation.py       # Relation property handler
│   │   ├── rollup.py         # Rollup property handler
│   │   ├── select.py         # Select/Multi-select handlers
│   │   ├── text.py           # Text/Title handlers
│   │   ├── timestamp.py      # Timestamp handlers
│   │   ├── url.py            # URL/Email/Phone handlers
│   │   └── user.py           # User property handlers
│   ├── labs/                  # Experimental features
│   │   ├── dry_run_notion_sync.py
│   │   └── generic_notion_sync.py
│   ├── minimal/               # Simplified DB sync implementation
│   │   ├── __init__.py       # Package initialization
│   │   ├── __main__.py       # CLI entry point
│   │   ├── ai_extractor.py   # AI integration for entity extraction
│   │   ├── cache.py          # File-based caching system
│   │   ├── cli.py            # Command-line interface
│   │   ├── config.py         # Configuration management
│   │   ├── models.py         # Pydantic data models
│   │   ├── notion_updater.py # Simplified Notion API client
│   │   ├── property_handlers.py # Notion property type handlers
│   │   ├── transcript_processor.py # Main orchestration logic
│   │   ├── utils.py          # Helper utilities
│   │   ├── examples/         # Usage examples
│   │   └── tests/            # Comprehensive test suite
│   ├── models/                # Data models
│   │   ├── json/             # JSON data templates
│   │   ├── notion_cache/     # Cached Notion data
│   │   ├── notion_properties.py  # Notion property models
│   │   ├── properties.py     # Base property models
│   │   └── responses.py      # API response models
│   ├── notion/                # Notion integration layer
│   │   ├── client.py         # Notion API wrapper
│   │   ├── database_creator.py  # Database creation utilities
│   │   └── schemas/          # Database schemas
│   │       └── all_databases.py  # All 8 database schemas
│   ├── rate_limiting/         # Rate limiting infrastructure
│   │   └── thread_safe.py    # Thread-safe rate limiter
│   ├── repositories/          # Repository pattern implementation
│   │   ├── base.py           # Base repository class
│   │   ├── database.py       # Database operations
│   │   ├── page.py           # Page operations
│   │   └── search.py         # Search operations
│   ├── security/              # Security layer
│   │   ├── audit.py          # Audit logging
│   │   ├── secrets_manager.py # Secrets management
│   │   └── validators.py     # Input validation & SSRF prevention
│   └── services/              # Service layer
│       ├── base.py           # Base service class
│       └── sync.py           # Sync services
├── docs/                      # Documentation
├── logs/                      # Log files
├── prompts/                   # AI prompts
│   └── extract.md
├── scripts/                   # Executable scripts
│   ├── analyse_relations.py   # Analyze database relationships
│   ├── discover_and_configure.py # Workspace discovery
│   ├── ingest_intelligence.py # Intelligence ingestion
│   ├── notion_sync.py        # Data synchronization
│   ├── setup_databases.py    # Database initialization
│   └── verify_databases.py   # Database verification
├── specs/                     # Specifications and design docs
│   ├── db-relations.md       # Database relationship specs
│   ├── roadmap.md           # Development roadmap
│   └── *.prd/.md            # Various PRDs and specs
├── tests/                     # Test suite
│   ├── conftest.py          # Test configuration & fixtures
│   ├── test_database_creation.py
│   ├── test_error_handlers.py
│   ├── test_handlers.py
│   ├── test_notion_sync.py
│   ├── test_property_handlers.py
│   ├── test_repositories.py
│   ├── test_security.py
│   └── test_sync_integration.py
├── transcripts/               # Sample/test data
├── pyproject.toml            # Package configuration
├── requirements.txt          # Production dependencies
├── requirements-dev.txt      # Development dependencies
├── CLAUDE.md                 # Claude Code instructions
├── README.md                 # Project documentation
└── README_DATABASES.md       # Database documentation
```

## Key Components

### 1. Core Package (`blackcore/`)
The main Python package containing all business logic, organized into logical modules.

### 2. Error Handling (`errors/`)
- Custom exception hierarchy
- Contextual error information
- User-friendly error messages
- Retry logic with exponential backoff

### 3. Property Handlers (`handlers/`)
- Type-safe handler registry system
- Individual handlers for each Notion property type
- Bidirectional conversion between Python and Notion API formats
- Comprehensive type validation

### 4. Models (`models/`)
- Pydantic models for type safety
- Notion property definitions
- API response models
- JSON templates for test data

### 5. Notion Integration (`notion/`)
- Client wrapper with rate limiting
- Database creation utilities
- Schema definitions for 8 interconnected databases

### 6. Security Layer (`security/`)
- Secrets management with encryption
- URL validation and SSRF prevention
- Input sanitization
- Comprehensive audit logging

### 7. Repository Pattern (`repositories/`)
- Abstraction over data access
- CRUD operations for pages and databases
- Search functionality
- Batch operations support

### 8. Services (`services/`)
- Business logic layer
- Sync services for data synchronization
- Domain-specific operations

### 9. Scripts (`scripts/`)
- Executable utilities for common operations
- Database setup and verification
- Data ingestion and synchronization
- Relationship analysis

### 10. Tests (`tests/`)
- Comprehensive test coverage
- Unit and integration tests
- Mock fixtures for Notion API
- Performance test scenarios

### 11. Minimal Module (`minimal/`) - Simplified DB Sync
A streamlined implementation focusing on the core workflow of transcript processing and Notion synchronization:

- **Purpose**: Simplified alternative to the full enterprise implementation
- **Architecture**: Direct implementation without complex abstractions
- **Key Features**:
  - Transcript processing (JSON/text input)
  - AI entity extraction (Claude/OpenAI)
  - Direct Notion API updates
  - File-based caching
  - Batch processing support
  - CLI interface
- **Usage**: Standalone module for basic sync operations
- **Benefits**: 
  - Easier to understand and maintain
  - Minimal dependencies
  - Quick setup and configuration
  - Focused on core use case

## Database Schema
The system manages 8 interconnected Notion databases:

1. **People & Contacts** - Individual tracking with relationships
2. **Organizations & Bodies** - Institutional entities
3. **Agendas & Epics** - Strategic goals and initiatives
4. **Actionable Tasks** - Operational task management
5. **Intelligence & Transcripts** - Raw data repository
6. **Documents & Evidence** - File and document library
7. **Key Places & Events** - Location and event tracking
8. **Identified Transgressions** - Issue and violation catalog

## Configuration
- Environment variables via `.env` file
- Notion configuration in `config/notion_config.json`
- Package configuration in `pyproject.toml`

## Development Workflow
- Test-Driven Development (TDD) approach
- Git workflow with feature branches
- Comprehensive documentation
- Security-first design principles