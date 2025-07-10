# Recommended Cleanup for Blackcore Repository

**Date**: January 10, 2025  
**Purpose**: Document files and directories that could be removed or reorganized to improve project structure

## Files Recommended for Removal

### 1. Generated/Cache Files
These files appear to be generated and should not be in version control:

- `logs/` directory - All log files should be gitignored
  - `logs/chat.json`
  - `logs/notification.json`
  - `logs/post_tool_use.json`
  - `logs/pre_tool_use.json`
  - `logs/stop.json`
  - `logs/subagent_stop.json`

- `blackcore/models/notion_cache/` - Cache directory should be gitignored

- `database_report.txt` - Appears to be generated output

- `potential_relations.json` - Appears to be analysis output

### 2. Development/Personal Files
These appear to be personal development files:

- `fireflies_support.html` - Appears to be a support page download
- `.claude/hooks/` - Personal Claude Code hooks (unless shared team config)
- `uv.lock` - Lock file might be personal preference (check team standards)

### 3. Duplicate Documentation
Some documentation appears redundant:

- Multiple code review files in `docs/`:
  - Consider consolidating code review docs
  - Archive older reviews if needed

## Files to Reorganize

### 1. Move to Examples Directory
- `transcripts/intelligence_package_20250618.json` - Move to `examples/data/`

### 2. Consolidate Configuration
- `blackcore/config/notion_config.json` - Consider moving to root `config/` directory
- Create single `config/` directory for all configuration

### 3. Organize Specifications
In `specs/` directory, consider subdirectories:
- `specs/phase0/` - Phase 0 related specs
- `specs/prd/` - Product requirement documents
- `specs/technical/` - Technical specifications

## Recommended .gitignore Additions

Add the following to `.gitignore`:

```gitignore
# Logs
logs/
*.log

# Cache
**/cache/
**/notion_cache/
**/__pycache__/

# Generated files
database_report.txt
potential_relations.json

# Personal configuration
.claude/hooks/
.claude/settings.json

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Python
*.pyc
*.pyo
*.pyd
.Python
*.egg-info/
dist/
build/

# Environment
.env.local
.env.*.local

# Coverage
htmlcov/
.coverage
.coverage.*
coverage.xml
*.cover

# Testing
.pytest_cache/
.tox/

# Development databases
*.db
*.sqlite
*.sqlite3
```

## Directory Structure Improvements

### Current Issues:
1. `blackcore/labs/` - Unclear purpose, consider renaming to `experimental/` or `prototypes/`
2. `blackcore/minimal/` - Large subdirectory that might warrant being a separate package
3. Mixed test data with source code

### Proposed Structure:
```
blackcore/
├── config/                 # All configuration files
├── docs/                   # All documentation
│   ├── api/               # API documentation
│   ├── architecture/      # Architecture decisions
│   └── reviews/           # Code reviews
├── examples/              # Example usage and data
│   ├── data/             # Sample data files
│   └── scripts/          # Example scripts
├── src/
│   └── blackcore/        # Main package (consider moving under src/)
├── tests/                # All tests
│   ├── unit/
│   ├── integration/
│   └── fixtures/
└── scripts/              # Utility scripts
```

## Action Items

1. **Immediate**: Add comprehensive `.gitignore` file
2. **Short-term**: Remove generated files from repository
3. **Medium-term**: Reorganize directory structure
4. **Long-term**: Consider splitting `minimal/` into separate package

## Note on Deletion

**IMPORTANT**: No files should be deleted without team consensus. This document serves as a recommendation only. All deletions should be:
1. Discussed with the team
2. Backed up if needed
3. Properly documented in commit messages
4. Verified not to break any functionality

## Files to Keep

Despite appearing unused, keep these files:
- All `.md` files in `specs/` - Historical documentation
- All test fixtures and data - Needed for testing
- `.claude/commands/` - Team shared commands
- `ai_docs/` - Useful reference documentation

## Simplified DB Sync (Minimal Module) Specific Recommendations

### Files to Add to .gitignore:
```gitignore
# Minimal module cache
blackcore/minimal/.cache/
blackcore/minimal/*.cache

# Minimal module test outputs
blackcore/minimal/tests/test_output/
blackcore/minimal/tests/*.log

# Minimal module config
blackcore/minimal/config.local.json
blackcore/minimal/.env.local
```

### Minimal Module Organization:

#### Current Issues:
1. **Cache files**: The file-based cache in `minimal/` creates `.cache` directories that shouldn't be in version control
2. **Test artifacts**: Test runs may create output files that should be ignored
3. **Local configs**: Users might create local config overrides

#### Recommendations:
1. **Create default config template**:
   - Rename any existing config to `config.example.json`
   - Add `config.json` to .gitignore
   - Document all configuration options

2. **Separate examples from tests**:
   - Move `blackcore/minimal/examples/` to `examples/minimal/`
   - Keep only unit tests in the module

3. **Consider package separation**:
   - The minimal module is self-contained enough to be its own package
   - Could be published as `blackcore-minimal` on PyPI
   - Would simplify dependency management

### Proposed Minimal Module Structure:
```
blackcore-minimal/  # Separate package
├── src/
│   └── blackcore_minimal/
│       ├── __init__.py
│       ├── processor.py
│       ├── notion.py
│       ├── ai.py
│       └── cache.py
├── tests/
├── examples/
├── docs/
└── pyproject.toml
```

### Cache Directory Cleanup:
The minimal module uses file-based caching that can accumulate:
- Add automatic cache cleanup on startup
- Implement cache size limits
- Add cache purge command to CLI