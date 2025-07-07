# Project Nassau Database Setup

This directory contains the implementation for creating and managing the 8 interconnected Notion databases for Project Nassau.

## Prerequisites

- Python 3.11+
- `uv` package manager
- Notion API integration token

## Setup

1. **Clone and navigate to the project**:
   ```bash
   cd blackcore
   ```

2. **Copy the environment file**:
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env` and add your Notion API key**:
   ```
   NOTION_API_KEY=your_notion_integration_token_here
   ```

4. **Create virtual environment and install dependencies**:
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv pip install -r requirements-dev.txt
   ```

## Usage

### Creating Databases

Run the setup script to create all 8 databases:

```bash
uv run python scripts/setup_databases.py
```

The script will:
1. Ask for the parent page ID where databases should be created
2. Check for existing databases
3. Create all missing databases with proper schemas
4. Set up relations between databases
5. Generate a report of created databases

### Verifying Databases

To verify that all databases were created correctly:

```bash
uv run python scripts/verify_databases.py
```

### Running Tests

```bash
uv run pytest
```

### Linting and Formatting

```bash
# Check code quality
uv run ruff check .

# Format code
uv run ruff format .
```

## Database Schema

The system creates 8 interconnected databases:

1. **People & Contacts** - CRM for all individuals
2. **Organizations & Bodies** - Institutional entities
3. **Agendas & Epics** - Strategic goals and initiatives
4. **Actionable Tasks** - Operational task management
5. **Intelligence & Transcripts** - Raw data repository
6. **Documents & Evidence** - File and document library
7. **Key Places & Events** - Location and event tracking
8. **Identified Transgressions** - Issue and violation catalog

Each database has specific properties and relations to other databases, creating a comprehensive knowledge graph.

## Project Structure

```
blackcore/
├── blackcore/
│   ├── notion/
│   │   ├── client.py          # Notion API wrapper
│   │   ├── database_creator.py # Database creation logic
│   │   └── schemas/
│   │       └── all_databases.py # Database schemas
│   └── models/
│       └── notion_properties.py # Property type models
├── scripts/
│   ├── setup_databases.py      # Main setup script
│   └── verify_databases.py     # Verification script
├── tests/
│   └── test_database_creation.py
├── requirements.txt            # Core dependencies
├── requirements-dev.txt        # Dev dependencies
└── pyproject.toml             # Project configuration
```

## Next Steps

After creating the databases, you can proceed with Phase 1 of the roadmap:
- Implement read-only operations
- Create object fetchers
- Build query engines
- Display relational data

See `specs/roadmap.md` for the complete development plan.