# Blackcore

> **Intelligence processing and automation system for Project Nassau**

Blackcore is a production-ready Python system that transforms raw intelligence data (transcripts, documents, meetings) into structured knowledge graphs using AI-powered entity extraction and sophisticated Notion database integration. Built with security-first design and enterprise-grade reliability.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-686%20passing-green.svg)](#testing)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## 🚀 Key Features

### 🧠 **AI-Powered Intelligence Processing**
- **Entity Extraction**: Automatically identify people, organizations, tasks, events, and transgressions
- **Dual AI Support**: Works with both Anthropic Claude and OpenAI models
- **Smart Relationships**: AI discovers and creates connections between entities

### 📊 **Notion Database Integration**
- **14 Interconnected Databases**: Complete intelligence management schema
- **All Property Types**: Full support for all Notion property types (text, select, relations, etc.)
- **Automatic Schema Creation**: Set up your intelligence workspace automatically

### ⚡ **Minimal Module - Production Ready**
- **686 Comprehensive Tests**: 100% pass rate with realistic workflows, network resilience, and performance validation
- **CLI Interface**: Process single transcripts or batch operations
- **Dry Run Mode**: Test processing without making changes
- **Simple Caching**: File-based caching with TTL support

### 🔒 **Security First**
- **Encrypted Secrets Management**: Secure storage with rotation capabilities
- **Input Sanitization**: Protection against injection attacks
- **Audit Logging**: Comprehensive audit trails with PII redaction
- **SSRF Protection**: Private IP blocking and request validation

### 🛠 **Developer Experience**
- **Interactive Deduplication**: AI-powered duplicate detection and merging
- **Comprehensive Testing**: Network resilience, performance regression, security validation
- **Modern Python**: Pydantic v2, async support, type hints throughout
- **Rich CLI Tools**: Beautiful terminal interfaces with progress tracking

## 🏃‍♂️ Quick Start

### Prerequisites
- Python 3.11 or higher
- Notion workspace and API key
- AI API key (Anthropic Claude or OpenAI)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd blackcore

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e .

# Set up environment
cp .env.example .env
# Edit .env with your API keys

# Generate secure master key (REQUIRED)
python scripts/generate_master_key.py
```

### Quick Start - Minimal Module

The minimal module is the fastest way to get started:

```bash
# Generate a configuration template
python -m blackcore.minimal generate-config > config.json

# Process a single transcript
python -m blackcore.minimal process transcript.json

# Process a directory of transcripts
python -m blackcore.minimal process-batch ./transcripts/

# Dry run (no changes to Notion)
python -m blackcore.minimal process transcript.json --dry-run

# Sync JSON data directly to Notion
python -m blackcore.minimal sync-json
```

### Example Transcript

Create a file `meeting.json`:

```json
{
  "title": "Weekly Team Meeting - Project Alpha",
  "content": "Meeting with Sarah Johnson from TechCorp. Discussed Q2 budget allocation. Action item: John Smith to prepare risk assessment by Friday. Identified potential compliance issue with data retention policy.",
  "date": "2025-01-31T14:00:00",
  "metadata": {
    "source": "zoom_recording",
    "duration": "45 minutes"
  }
}
```

Process it:

```bash
python -m blackcore.minimal process meeting.json
```

The AI will extract:
- **Person**: Sarah Johnson (TechCorp)
- **Person**: John Smith
- **Organization**: TechCorp
- **Task**: Risk assessment (assigned to John, due Friday)
- **Transgression**: Data retention compliance issue

## 🏗 Architecture

Blackcore follows a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                     CLI Layer                               │
├─────────────────────────────────────────────────────────────┤
│                   Service Layer                             │
│  TranscriptProcessor | DeduplicationEngine | SyncService   │
├─────────────────────────────────────────────────────────────┤
│                 Repository Layer                            │
│    PageRepository | DatabaseRepository | SearchRepository  │
├─────────────────────────────────────────────────────────────┤
│                Integration Layer                            │
│      NotionClient | AIExtractor | PropertyHandlers        │
├─────────────────────────────────────────────────────────────┤
│               Infrastructure Layer                          │
│    Security | RateLimiting | Caching | ErrorHandling     │
└─────────────────────────────────────────────────────────────┘
```

For detailed technical documentation, see [Architecture.md](architecture.md).

## 🧪 Testing

Blackcore includes a comprehensive test suite with **686 tests** achieving **100% pass rate**:

```bash
# Run all tests
pytest blackcore/minimal/tests/ -v

# Run specific test categories
pytest blackcore/minimal/tests/test_transcript_processor.py -v  # Core functionality
pytest blackcore/minimal/tests/comprehensive/test_realistic_workflows.py -v  # 16 workflow tests  
pytest blackcore/minimal/tests/comprehensive/test_network_resilience.py -v  # 22+ resilience tests
pytest blackcore/minimal/tests/comprehensive/test_performance_regression.py -v  # Performance benchmarks

# Run with coverage
pytest blackcore/minimal/tests/ --cov=blackcore.minimal --cov-report=term-missing
```

**Test Categories:**
- ✅ **Unit Tests** - Core functionality validation
- ✅ **Realistic Workflows** - End-to-end scenarios with authentic data  
- ✅ **Network Resilience** - Production failure simulation and recovery
- ✅ **Performance Regression** - Benchmarking and scalability validation
- ✅ **Security & Edge Cases** - Input validation and malicious content handling

## 🔧 Main Scripts

### Database Management
```bash
# Initialize Notion databases (14 interconnected databases)
python scripts/setup/setup_databases.py

# Verify database configuration
python scripts/setup/verify_databases.py

# Discover and configure workspace
python scripts/setup/discover_and_configure.py
```

### Deduplication
```bash
# Interactive deduplication CLI
python scripts/deduplication/dedupe_cli.py

# The CLI guides you through:
# 1. Database selection
# 2. Threshold configuration (auto-merge: 90%, review: 70%)  
# 3. AI-powered analysis
# 4. Review and approval of matches
```

### Data Processing
```bash
# Process new intelligence
python scripts/process_intelligence.py

# Sync data between local JSON and Notion
python scripts/sync/notion_sync.py
```

## 📊 Database Schema  

Blackcore manages 14 interconnected Notion databases:

- **People & Contacts** - Individual tracking with relationships
- **Organizations & Bodies** - Institutional entities  
- **Agendas & Epics** - Strategic goals and initiatives
- **Actionable Tasks** - Operational task management
- **Intelligence & Transcripts** - Raw data repository
- **Documents & Evidence** - File and document library
- **Key Places & Events** - Location and event tracking
- **Identified Transgressions** - Issue and violation catalog
- **Plus 6 additional specialized databases**

## 🔐 Security

Blackcore implements defense-in-depth security:

- **Encrypted Secrets**: AES-256 encryption with key rotation
- **Input Validation**: Comprehensive sanitization and validation
- **SSRF Protection**: Private IP blocking and request filtering  
- **Audit Logging**: Comprehensive trails with PII redaction
- **Rate Limiting**: Thread-safe API throttling
- **Secure Defaults**: Minimal permissions and secure configurations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Write tests first (TDD approach)
4. Implement your feature
5. Ensure all tests pass: `pytest blackcore/minimal/tests/ -v`
6. Run linting: `ruff format . && ruff check --fix .`
7. Submit a pull request

## 📝 Development

### Code Quality
```bash
# Lint and format (recommended before commits)
ruff format . && ruff check --fix .

# Check specific directories
ruff check blackcore/security/
```

### Environment Variables
Required in `.env`:
- `BLACKCORE_MASTER_KEY` - **REQUIRED**: Master encryption key
- `NOTION_API_KEY` - Notion integration token
- `ANTHROPIC_API_KEY` - Claude API key (or `OPENAI_API_KEY`)
- `NOTION_PARENT_PAGE_ID` - Parent page for database creation

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built for Project Nassau intelligence processing
- Powered by Anthropic Claude and OpenAI models
- Integrates seamlessly with Notion workspaces
- Comprehensive test infrastructure inspired by production reliability requirements
