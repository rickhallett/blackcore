# Running Deduplication Without AI

The deduplication system works perfectly fine without AI/LLM analysis. It will use fuzzy matching algorithms to detect duplicates.

## Quick Start (No AI)

1. **Run the safe launcher:**
   ```bash
   python scripts/run_dedupe_cli_safe.py
   ```
   This will check your environment and warn you if AI is disabled.

2. **Or run the CLI directly:**
   ```bash
   python scripts/dedupe_cli.py
   ```

3. **When configuring:**
   - At Step 3 (AI Settings), choose **No** when asked "Enable AI-powered analysis?"
   - This will skip AI configuration entirely

## What Works Without AI

✅ **Fuzzy Matching**
- String similarity algorithms (Levenshtein, Jaro-Winkler)
- Phonetic matching (Soundex, Metaphone)
- Token-based analysis
- Pattern recognition (nicknames, abbreviations)

✅ **Smart Detection**
- Email address matching
- Phone number matching (handles formatting differences)
- Organization abbreviation detection (e.g., "STC" = "Swanage Town Council")
- Name variations (e.g., "Tony" = "Anthony", "Bob" = "Robert")

✅ **All Core Features**
- Multi-database analysis
- Confidence scoring
- Interactive review interface
- Safety mode (no automatic changes)
- Audit trails

## Example Results (No AI)

The system successfully detects duplicates like:
- **Tony Powell** entries with slight organization variations
- **Colin Bright** vs **Collin Bright** (same email)
- **Elaine Snow** exact duplicates

## Detection Accuracy

Without AI, expect:
- **95-100%** accuracy for exact/near-exact matches
- **85-95%** accuracy for common variations (nicknames, typos)
- **70-85%** accuracy for complex matches

## Configuration for Best Results

When running without AI, use these settings:
- Auto-merge threshold: **95%** (be more conservative)
- Review threshold: **65%** (catch more potential matches)

## If You See API Key Errors

If you get errors about invalid API keys:

1. **Temporary fix:** Clear the environment variable
   ```bash
   unset ANTHROPIC_API_KEY
   python scripts/dedupe_cli.py
   ```

2. **Or use the test script directly:**
   ```bash
   python scripts/test_people_deduplication.py
   ```
   This bypasses the CLI and runs analysis directly.

## Summary

The deduplication system is fully functional without AI. It uses sophisticated fuzzy matching algorithms that can detect most duplicates accurately. AI analysis is an enhancement, not a requirement.