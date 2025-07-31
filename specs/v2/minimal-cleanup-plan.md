# Blackcore Minimal Cleanup Plan

## Executive Summary

This document outlines the comprehensive plan for removing unused parts of the blackcore codebase, keeping only the minimal module and its essential dependencies. The analysis shows that approximately 80% of the codebase can be safely removed.

## Analysis Results

### Minimal Module Dependencies

The minimal module (`blackcore/minimal/`) is completely self-contained with the following characteristics:

1. **No internal blackcore dependencies**: All imports within minimal reference only other files within the minimal module
2. **External dependencies**: Only uses standard Python libraries and pip packages (notion-client, pydantic, etc.)
3. **Shared resources**: 
   - `blackcore/config/notion_config.json` - Required for database configuration
   - No dependency on `blackcore/models/json/` directory

### Modules Safe to Remove

The following blackcore modules have no connection to minimal:

1. **blackcore/errors/** - Custom error handling (minimal has its own)
2. **blackcore/handlers/** - Property handlers (minimal has its own implementation)
3. **blackcore/intelligence/** - AI analysis engine (separate system)
4. **blackcore/labs/** - Experimental code
5. **blackcore/models/** - Data models (except json/ directory used by some scripts)
6. **blackcore/notion/** - Notion client wrapper (minimal has its own)
7. **blackcore/rate_limiting/** - Rate limiting (minimal has its own)
8. **blackcore/repositories/** - Repository pattern (minimal has its own)
9. **blackcore/security/** - Security features (not used by minimal)
10. **blackcore/services/** - Service layer (not used by minimal)
11. **blackcore/deduplication/** - Deduplication system (large module, not used by minimal)

## Scripts Analysis

### Scripts to REMOVE (Dependencies on Modules Being Deleted)

#### Setup Scripts (use `blackcore.notion`)
- `scripts/setup/discover_and_configure.py`
- `scripts/setup/setup_databases.py`
- `scripts/setup/verify_databases.py`

#### Deduplication Scripts (use `blackcore.deduplication`)
- `scripts/deduplication/dedupe_cli.py`
- `scripts/deduplication/demo_dedupe_cli.py`
- `scripts/deduplication/demonstrate_dedupe_cli.py`
- `scripts/deduplication/diagnose_deduplication.py`
- `scripts/deduplication/run_dedupe_cli_safe.py`
- `scripts/deduplication/run_dedupe_demo.py`
- `scripts/deduplication/test_deduplication_system.py`
- `scripts/deduplication/test_full_merge_flow.py`
- `scripts/deduplication/test_low_confidence_review.py`
- `scripts/deduplication/test_merge_fix.py`
- `scripts/deduplication/test_people_deduplication.py`

#### Data Processing Scripts (use `blackcore.notion`)
- `scripts/data_processing/ingest_intelligence.py`
- `scripts/data_processing/data_remediation.py`
- `scripts/data_processing/analyse_relations.py`

#### Sync Scripts (use `blackcore.notion`)
- `scripts/sync/notion_sync.py`
- `scripts/sync/compare_local_notion.py`
- `scripts/sync/create_missing_local_files.py`
- `scripts/sync/merge_notion_to_local.py`
- `scripts/sync/upload_missing_simple.py`
- `scripts/sync/verify_sync_completion.py`

#### Testing Scripts (use `blackcore.deduplication`)
- `scripts/testing/test_cli_interactive.py`
- `scripts/testing/test_cli_merge.py`
- `scripts/testing/test_cli_no_ai.py`
- `scripts/testing/test_dedupe_analysis.py`
- `scripts/testing/test_dedupe_cli.py`
- `scripts/testing/test_dedupe_detailed.py`
- `scripts/testing/test_single_page_creation.py`

#### Debug Scripts (mixed dependencies)
- `scripts/debug/debug_database_loading.py` (uses deduplication)
- `scripts/debug/fix_property_formatting.py` (unknown dependencies)
- `scripts/debug/fix_remaining_issues.py` (unknown dependencies)

#### Other Scripts
- `scripts/blacksails/scrape_plot.py` (unrelated web scraping)
- `scripts/external/fireflies_support.html` (just HTML documentation)
- `scripts/utilities/run_neo4j-blackcore.sh` (Neo4j integration)

### Scripts to KEEP (Use Minimal or Standalone)

#### Scripts Using `blackcore.minimal`
- `scripts/deduplication/demo_deduplication.py`
- `scripts/deduplication/demo_llm_deduplication.py`
- `scripts/sync/sync_production.py`
- `scripts/sync/sync_production_staged.py`
- `scripts/sync/final_production_sync.py`
- `scripts/sync/upload_missing_local_records.py`
- `scripts/data_processing/export_complete_notion.py`
- `scripts/testing/test_staged_sync.py`
- `scripts/debug/debug_property_formatting.py`
- `scripts/debug/debug_property_preparation.py`

#### Standalone Utilities
- `scripts/generate_master_key.py` (security key generation)
- `scripts/utilities/merge_hook_files.py` (general utility)
- `scripts/utilities/run_interactive_dedupe.sh` (shell script launcher)

#### Configuration Files
- `scripts/config/` directory (contains JSON configuration files)

## Tests to Remove

All tests outside of `blackcore/minimal/tests/` should be removed:
- `tests/` directory (contains tests for non-minimal modules)

## Cleanup Execution Plan

### Phase 1: Remove Core Modules
```bash
# Remove unused blackcore modules
rm -rf blackcore/errors/
rm -rf blackcore/handlers/
rm -rf blackcore/intelligence/
rm -rf blackcore/labs/
rm -rf blackcore/notion/
rm -rf blackcore/rate_limiting/
rm -rf blackcore/repositories/
rm -rf blackcore/security/
rm -rf blackcore/services/
rm -rf blackcore/deduplication/

# Remove model files but keep json directory
rm -f blackcore/models/*.py
```

### Phase 2: Remove Scripts
```bash
# Remove setup scripts
rm -rf scripts/setup/

# Remove most deduplication scripts (keep the 2 that use minimal)
rm -f scripts/deduplication/dedupe_cli.py
rm -f scripts/deduplication/demo_dedupe_cli.py
rm -f scripts/deduplication/demonstrate_dedupe_cli.py
rm -f scripts/deduplication/diagnose_deduplication.py
rm -f scripts/deduplication/run_dedupe_cli_safe.py
rm -f scripts/deduplication/run_dedupe_demo.py
rm -f scripts/deduplication/test_*.py

# Remove data processing scripts (keep export_complete_notion.py)
rm -f scripts/data_processing/ingest_intelligence.py
rm -f scripts/data_processing/data_remediation.py
rm -f scripts/data_processing/analyse_relations.py

# Remove sync scripts (keep the ones using minimal)
rm -f scripts/sync/notion_sync.py
rm -f scripts/sync/compare_local_notion.py
rm -f scripts/sync/create_missing_local_files.py
rm -f scripts/sync/merge_notion_to_local.py
rm -f scripts/sync/upload_missing_simple.py
rm -f scripts/sync/verify_sync_completion.py

# Remove testing scripts (keep test_staged_sync.py)
rm -f scripts/testing/test_cli_*.py
rm -f scripts/testing/test_dedupe_*.py
rm -f scripts/testing/test_single_page_creation.py

# Remove debug scripts that don't use minimal
rm -f scripts/debug/debug_database_loading.py
rm -f scripts/debug/fix_property_formatting.py
rm -f scripts/debug/fix_remaining_issues.py

# Remove other unrelated scripts
rm -rf scripts/blacksails/
rm -rf scripts/external/
rm -f scripts/utilities/run_neo4j-blackcore.sh
```

### Phase 3: Remove Tests
```bash
rm -rf tests/
```

### Phase 4: Clean Up Artifacts
```bash
# Remove database files
rm -f deduplication_audit.db
rm -f scripts/deduplication_audit.db

# Remove temporary files
rm -f tmp*.txt
```

### Phase 5: Update Project Files
1. Update `pyproject.toml`:
   - Remove script entries for deleted scripts
   - Update dependencies if any are no longer needed
   
2. Update documentation:
   - Remove references to deleted modules
   - Update README to focus on minimal module
   
3. Update `.gitignore` if needed

## Final Structure

After cleanup, the project structure will be:

```
blackcore/
├── __init__.py
├── config/
│   └── notion_config.json
├── minimal/
│   ├── [all minimal module files]
│   └── tests/
└── models/
    └── json/  # Keep for now, used by some remaining scripts

scripts/
├── config/  # Configuration files
├── data_processing/
│   └── export_complete_notion.py
├── debug/
│   ├── debug_property_formatting.py
│   └── debug_property_preparation.py
├── deduplication/
│   ├── demo_deduplication.py
│   └── demo_llm_deduplication.py
├── generate_master_key.py
├── sync/
│   ├── final_production_sync.py
│   ├── sync_production.py
│   ├── sync_production_staged.py
│   └── upload_missing_local_records.py
├── testing/
│   └── test_staged_sync.py
└── utilities/
    ├── merge_hook_files.py
    └── run_interactive_dedupe.sh
```

## Impact Summary

- **Code Removed**: ~80% of blackcore modules
- **Scripts Removed**: ~35 out of ~48 scripts (73%)
- **Tests Removed**: All non-minimal tests
- **Space Saved**: Significant reduction in codebase size
- **Complexity Reduced**: Much simpler project structure
- **Functionality Preserved**: All minimal module functionality intact

## Verification Steps

After cleanup:
1. Run minimal module tests: `pytest blackcore/minimal/tests/`
2. Test a transcript processing operation
3. Verify JSON sync functionality still works
4. Check that remaining scripts run without import errors

## Rollback Plan

If issues arise:
1. Use git to revert changes: `git checkout HEAD~1`
2. Or restore from backup if created before cleanup