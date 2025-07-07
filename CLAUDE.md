# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Blackcore is a Python-based intelligence processing and automation system for "Project Nassau" that interfaces with Notion workspaces to create structured knowledge graphs from raw intelligence data.

## Development Commands

### Setup
```bash
# Install dependencies (once implemented)
uv pip install -r requirements-dev.txt

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

# Run with coverage
pytest --cov=blackcore
```

### Code Quality
```bash
# Run linter
ruff check .

# Format code
ruff format .
```

### Main Scripts
```bash
# Initialize Notion databases
python scripts/setup_databases.py

# Process new intelligence
python scripts/process_new_intelligence.py

# Main application (various modes)
python main.py --mode [ingest|link|report]
```

## Architecture

### Core Components
1. **Ingestion Engine** (`blackcore/ingestion/`) - Processes raw data from Google Drive
2. **Notion ORM** (`blackcore/models/`) - Object-relational mapper for Notion databases
3. **Relational Linker** (`blackcore/linker/`) - Creates connections between data objects
4. **AI Integration** (`blackcore/ai/`) - Interfaces for Claude and Gemini models
5. **Reporting Engine** (`blackcore/reporting/`) - Query and report generation

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