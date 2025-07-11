# Live Notion Configuration Fetching

## Overview
This feature enables the blackcore project to fetch its Notion database configuration dynamically from the live Notion workspace, rather than relying solely on a static JSON configuration file.

## Implementation

### 1. NotionClient Enhancements
Added two new methods to the `NotionClient` class:

#### `refresh_config()`
- Rediscovers all accessible databases in the Notion workspace
- Fetches their schemas and properties
- Saves the updated configuration to `notion_config.json`
- Returns the refreshed configuration

#### `validate_database_exists(database_id)`
- Checks if a specific database ID is still valid and accessible
- Returns `True` if the database exists, `False` otherwise
- Handles API errors gracefully

### 2. Sync Script Enhancements
Modified `scripts/notion_sync.py` to support dynamic configuration:

#### `--refresh-config` Flag
- When provided, refreshes the configuration before any sync operation
- Example: `python scripts/notion_sync.py --refresh-config "People & Contacts"`

#### Automatic Database Validation
- Before syncing, validates that the target database still exists
- If not found, prompts the user to refresh the configuration
- Provides a simple y/n prompt for user control

## Usage Examples

### Refresh configuration manually
```bash
python scripts/notion_sync.py --refresh-config
```

### Sync with automatic validation
```bash
python scripts/notion_sync.py "People & Contacts"
# If database not found: "Database not found. Refresh config? (y/n)"
```

### Force refresh before sync
```bash
python scripts/notion_sync.py --refresh-config "People & Contacts" --live
```

## Benefits
1. **Resilience**: Handles database ID changes gracefully
2. **Simplicity**: No complex caching or automatic updates
3. **User Control**: User decides when to refresh configuration
4. **Validation**: Ensures databases exist before operations
5. **Minimal Changes**: ~30 lines of code total

## Technical Details
- Reuses existing `discover_databases()` and `save_config_to_file()` functions
- No new dependencies or complex state management
- Configuration still stored in JSON for offline access
- Backwards compatible with existing workflows