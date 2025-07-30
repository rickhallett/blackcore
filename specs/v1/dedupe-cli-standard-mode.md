# Blackcore Deduplication CLI - Standard Mode Specification

## 1. Overview

### 1.1 Purpose
The Standard Mode CLI provides an interactive, user-friendly interface for the Blackcore deduplication engine, designed for regular users who need comprehensive deduplication capabilities with reasonable defaults and guided workflows.

### 1.2 Target Users
- Data analysts performing regular deduplication tasks
- Team members without deep technical expertise
- Users needing interactive review workflows
- Organizations requiring audit trails and decision tracking

### 1.3 Key Differentiators
- **Balance**: More features than Simple mode, less complexity than Expert mode
- **Interactive**: Real-time feedback and visual progress tracking
- **Guided**: Step-by-step configuration with sensible defaults
- **Async**: Non-blocking operations for better performance
- **Integration-Ready**: Designed for standalone use or integration

## 2. Architecture

### 2.1 Module Structure
```
blackcore/deduplication/cli/
├── __init__.py              # Module exports
├── standard_mode.py         # Main application class
├── ui_components.py         # Rich UI components
├── config_wizard.py         # Configuration management
└── async_engine.py          # Async wrapper for engine
```

### 2.2 Component Responsibilities

#### standard_mode.py
- Main application loop
- Menu navigation
- Workflow orchestration
- User input handling
- State management

#### ui_components.py
- Progress bars and spinners
- Tables and comparison views
- Interactive prompts
- Color-coded displays
- Dashboard layouts

#### config_wizard.py
- Step-by-step configuration
- Threshold adjustment
- Database selection
- Settings validation
- Preview generation

#### async_engine.py
- Async wrapper for DeduplicationEngine
- Progress callbacks
- Concurrent operations
- Cancellation support
- Error propagation

### 2.3 Data Flow
```
User Input → Standard Mode → Config Wizard → Async Engine → UI Components
                ↑                                 ↓              ↓
                ←─────────── Progress/Results ←───────────────────
```

## 3. Features

### 3.1 Main Menu
```
╭─────────────────────────────────────────────╮
│       Blackcore Deduplication Engine        │
│            Standard Mode v1.0.0             │
├─────────────────────────────────────────────┤
│  1. New Analysis                            │
│  2. Configure Settings                      │
│  3. View Statistics                         │
│  4. Help & Documentation                    │
│  5. Exit                                    │
╰─────────────────────────────────────────────╯
```

### 3.2 Configuration Wizard

#### Step 1: Database Selection
- List available databases
- Multi-select interface
- Preview record counts
- Show last modified dates

#### Step 2: Threshold Configuration
- Auto-merge threshold (default: 90%)
- Review threshold (default: 70%)
- Visual impact preview
- Explanation of thresholds

#### Step 3: AI Settings (Optional)
- Enable/disable AI analysis
- Select AI model (Claude/GPT)
- Configure rate limits
- Test connection

#### Step 4: Review Settings
- Summary of configuration
- Estimated processing time
- Resource requirements
- Confirm or modify

### 3.3 Analysis Dashboard
```
┌─ Analysis Progress ─────────────────────────────────────┐
│                                                         │
│  Database: People & Contacts                            │
│  Stage: AI Analysis                                     │
│                                                         │
│  [████████████████░░░░░░░░░░] 72% (360/500 entities)  │
│                                                         │
│  ⚡ Processing: 12.3 entities/sec                       │
│  ⏱  Elapsed: 00:02:45 | ETA: 00:00:52                 │
│                                                         │
├─ Live Statistics ───────────────────────────────────────┤
│  Total Comparisons:     24,750                          │
│  Potential Duplicates:  142                             │
│  High Confidence:       38                              │
│  Medium Confidence:     67                              │
│  Low Confidence:        37                              │
└─────────────────────────────────────────────────────────┘
```

### 3.4 Match Review Interface

#### Navigation
- `j`/`k` or `↓`/`↑`: Navigate matches
- `Enter`: View details
- `a`: Approve merge
- `r`: Reject (not duplicates)
- `d`: Defer decision
- `e`: View evidence
- `q`: Return to menu
- `h`: Help

#### Display Format
```
┌─ Match 1 of 142 ────────────────────────────────────────┐
│  Confidence: 92.5% [HIGH]                               │
├─────────────────────────────────────────────────────────┤
│  Entity A                 │  Entity B                   │
├──────────────────────────┼─────────────────────────────┤
│  Name: Anthony Smith     │  Name: Tony Smith           │
│  Email: tony@example.com │  Email: tony@example.com    │
│  Org: Swanage Council    │  Org: STC                   │
│  Phone: 01234567890      │  Phone: 01234 567 890       │
├─────────────────────────────────────────────────────────┤
│  Evidence:                                              │
│  • Exact email match (100%)                             │
│  • Name similarity: Tony is nickname for Anthony       │
│  • Organization: STC = Swanage Town Council            │
│  • Phone numbers match (formatting difference)          │
├─────────────────────────────────────────────────────────┤
│  [A]pprove  [R]eject  [D]efer  [E]vidence  [Q]uit     │
└─────────────────────────────────────────────────────────┘
```

### 3.5 Progress Tracking

#### Multi-Stage Progress
1. Loading databases
2. Pre-processing & indexing
3. Fuzzy matching
4. AI analysis (if enabled)
5. Graph analysis
6. Preparing results

#### Visual Indicators
- Overall progress bar
- Current stage highlight
- Processing rate
- Time estimates
- Memory usage (optional)

## 4. User Workflows

### 4.1 First-Time Usage
1. Launch CLI
2. Guided configuration wizard
3. Select databases
4. Run analysis
5. Review matches
6. Complete

### 4.2 Regular Usage
1. Launch with saved config
2. Confirm or adjust settings
3. Run analysis
4. Review new matches
5. Export decisions

### 4.3 Keyboard-Driven Workflow
- Full keyboard navigation
- No mouse required
- Vim-style shortcuts
- Quick actions
- Efficient review

## 5. Technical Implementation

### 5.1 Async Architecture
```python
class StandardModeCLI:
    async def run_analysis(self, databases, config):
        # Non-blocking analysis
        async with AsyncDeduplicationEngine(config) as engine:
            # Progress callback
            async def on_progress(stage, current, total):
                await self.update_dashboard(stage, current, total)
            
            # Run analysis
            results = await engine.analyze_databases_async(
                databases,
                progress_callback=on_progress
            )
        return results
```

### 5.2 Rich UI Components
```python
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn
from rich.layout import Layout
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

class UIComponents:
    def __init__(self):
        self.console = Console()
        
    def create_progress_bar(self, stages):
        # Multi-stage progress tracking
        
    def create_comparison_table(self, entity_a, entity_b):
        # Side-by-side comparison
        
    def create_dashboard(self, stats):
        # Live statistics dashboard
```

### 5.3 Error Handling
- Graceful degradation (AI fails → continue without)
- Clear error messages
- Recovery suggestions
- Progress preservation
- Automatic retries

### 5.4 Performance Optimizations
- Async I/O throughout
- Batch processing
- Progress streaming
- Minimal memory footprint
- Efficient rendering

## 6. Configuration

### 6.1 Runtime Configuration
```python
{
    "thresholds": {
        "auto_merge": 90.0,
        "human_review": 70.0
    },
    "ai": {
        "enabled": True,
        "model": "claude-3-5-sonnet-20241022",
        "max_concurrent": 5,
        "timeout": 30
    },
    "ui": {
        "page_size": 10,
        "color_scheme": "default",
        "show_memory": False
    },
    "analysis": {
        "batch_size": 100,
        "enable_graph": True
    }
}
```

### 6.2 Defaults
- Safety-first: No auto-merging without confirmation
- Reasonable thresholds: 90% auto, 70% review
- AI optional: Works without API keys
- Standard batch sizes: Balance speed/memory

## 7. Integration Points

### 7.1 Standalone Usage
```bash
# Direct execution
python -m blackcore.deduplication.cli.standard_mode

# Via entry script
python scripts/dedupe_cli.py --mode standard
```

### 7.2 Programmatic Usage
```python
from blackcore.deduplication.cli import StandardModeCLI

# Create instance
cli = StandardModeCLI()

# Run with config
results = await cli.run_analysis(
    databases=["People & Contacts"],
    config={"thresholds": {"auto_merge": 95}}
)
```

### 7.3 Extension Points
- Custom UI components
- Additional review actions
- Plugin system (future)
- Event hooks

## 8. Testing Strategy

### 8.1 Unit Tests
- UI component rendering
- Configuration validation
- Progress calculations
- Navigation logic

### 8.2 Integration Tests
- Full workflow tests
- Async operation tests
- Error scenario tests
- Performance benchmarks

### 8.3 User Acceptance
- Usability testing
- Keyboard navigation
- Error message clarity
- Performance perception

## 9. Documentation

### 9.1 User Guide
- Getting started
- Configuration guide
- Keyboard shortcuts
- Best practices

### 9.2 Examples
- Common workflows
- Configuration templates
- Troubleshooting

### 9.3 API Reference
- Public methods
- Configuration options
- Extension points

## 10. Future Enhancements

### 10.1 Phase 2 Features
- Export functionality
- Session management
- Batch decision import
- Custom shortcuts

### 10.2 Phase 3 Features
- Web UI option
- REST API
- Multi-user support
- Advanced visualizations

## 11. Success Criteria

### 11.1 Performance
- < 100ms UI response time
- Process 1000 entities/minute
- < 200MB memory usage
- Smooth progress updates

### 11.2 Usability
- < 5 minutes to first result
- Intuitive navigation
- Clear error messages
- Efficient review workflow

### 11.3 Reliability
- Graceful error handling
- Progress preservation
- Consistent results
- No data loss

## 12. Implementation Timeline

### Week 1
- Core structure
- Async engine wrapper
- Basic UI components

### Week 2
- Configuration wizard
- Main application loop
- Progress tracking

### Week 3
- Match review interface
- Keyboard navigation
- Error handling

### Week 4
- Testing
- Documentation
- Performance optimization
- Release preparation