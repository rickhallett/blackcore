# Deduplication Quick Start Guide

## Running the Interactive CLI

To analyze the People & Contacts database for duplicates:

```bash
cd /Users/oceanheart/Documents/Manual Library/code/blackcore
python scripts/dedupe_cli.py
```

Or use the launcher script:
```bash
./run_interactive_dedupe.sh
```

## Step-by-Step Process

### 1. Main Menu
When the CLI starts, you'll see:
- **[1] New Analysis** - Choose this to start
- [2] Configure Settings
- [3] View Statistics
- [4] Help & Documentation
- [5] Exit

### 2. Database Selection
- The system will show all available databases
- To analyze just People & Contacts, enter: `4` (when People & Contacts is #4)
- Or press Enter to analyze all databases

### 3. Threshold Configuration
- **Auto-merge threshold**: 90% (default) - High confidence matches
- **Review threshold**: 70% (default) - Medium confidence matches
- Press Enter to accept defaults

### 4. AI Settings
- If you have ANTHROPIC_API_KEY set, you can enable AI analysis
- AI improves accuracy for complex matches
- Works without AI too (faster but less sophisticated)

### 5. Analysis
- The system will analyze all records
- Shows real-time progress
- Safety mode is ON by default

### 6. Review Matches
After analysis, you can review each match:
- **[A]pprove** - Mark as duplicate
- **[R]eject** - Not duplicates
- **[D]efer** - Skip for now
- **[E]vidence** - See detailed comparison
- **[N]ext/[P]revious** - Navigate matches

## Keyboard Shortcuts

- `j` or `↓` - Next match
- `k` or `↑` - Previous match
- `a` - Approve merge
- `r` - Reject (not duplicates)
- `d` - Defer decision
- `e` - View evidence
- `h` - Help
- `q` - Quit review

## Found Duplicates in People Database

The analysis found these high-confidence duplicates:

1. **Tony Powell** (95% match)
   - Entry 1: Dorset Coast Forum
   - Entry 2: Dorset Coast Forum (DCF)
   - Same person, slightly different org name

2. **Elaine Snow** (100% match)
   - Exact duplicate entry
   - Both have same org: Dorset Coast Forum (DCF)

3. **Colin/Collin Bright** (95% match)
   - Same email: 34crbright@gmail.com
   - Name spelled differently (Colin vs Collin)

## Safety Mode

- **No automatic changes** - Everything requires approval
- All decisions are logged for audit
- You can quit at any time without making changes
- To actually merge duplicates, you would need to:
  1. Review and approve matches
  2. Explicitly confirm merge operations
  3. Run with safety_mode=False (not recommended for first use)

## AI Model Configuration

The system now uses the latest Claude models:
- Primary: claude-3-7-sonnet-20250219
- Also available: claude-sonnet-4-20250514, claude-opus-4-20250514

To use AI analysis, ensure your ANTHROPIC_API_KEY is set:
```bash
export ANTHROPIC_API_KEY=your_key_here
```