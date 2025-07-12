# Blackcore Deduplication Engine - Comprehensive Guide

## Table of Contents
1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Installation & Setup](#installation--setup)
4. [Basic Commands](#basic-commands)
5. [Configuration Guide](#configuration-guide)
6. [Interpreting Results](#interpreting-results)
7. [Advanced Features](#advanced-features)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)
10. [API Reference](#api-reference)

## Overview

The Blackcore Deduplication Engine is a sophisticated AI-powered system designed to identify and resolve duplicate entities in intelligence data with high accuracy while maintaining complete data integrity.

### Architecture: 4-Layer Processing Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    Layer 1: Fuzzy Matching                  │
│  • String similarity (Levenshtein, Jaro-Winkler)          │
│  • Phonetic matching (Soundex, Metaphone)                 │
│  • Token-based analysis                                   │
│  • Initial confidence scoring                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              Layer 2: AI/LLM Analysis                      │
│  • Context-aware entity resolution                        │
│  • Claude/GPT integration                                 │
│  • Domain-specific prompts                               │
│  • Confidence refinement                                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│           Layer 3: Graph Relationship Analysis            │
│  • Network effect consideration                           │
│  • Entity clustering                                      │
│  • Shared connection analysis                             │
│  • Centrality scoring                                     │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│            Layer 4: Human Review & Validation             │
│  • Review interface for uncertain cases                   │
│  • Decision tracking and audit                            │
│  • Quality assurance workflows                            │
│  • Learning from human decisions                          │
└─────────────────────────────────────────────────────────────┘
```

### Supported Entity Types
- **People & Contacts**: Names, emails, phones, organizations
- **Organizations & Bodies**: Names, websites, abbreviations
- **Key Places & Events**: Locations, dates, descriptions
- **Documents & Evidence**: Titles, URLs, content
- **Intelligence & Transcripts**: Text analysis, entity extraction
- **Actionable Tasks**: Task descriptions, assignments
- **Agendas & Epics**: Strategic goals, initiatives

### Key Features
- ✅ **Safety Mode by Default**: No automatic changes without explicit approval
- ✅ **Comprehensive Audit Trails**: Every decision tracked and reversible
- ✅ **AI-Powered Analysis**: Claude/GPT integration for complex cases
- ✅ **Confidence-Based Decisions**: Clear thresholds for automation vs review
- ✅ **Domain-Specific Logic**: Specialized processing for each entity type

## Quick Start

### 1. Run a Safe Dry Analysis (Recommended First Step)

```python
#!/usr/bin/env python3
from blackcore.deduplication import DeduplicationEngine
import json

# Initialize engine in safety mode (default)
engine = DeduplicationEngine()

# Load your data
with open('blackcore/models/json/people_places.json', 'r') as f:
    people_data = json.load(f)

# Run analysis - NO changes will be made
results = engine.analyze_database(
    "People & Contacts", 
    people_data.get("People & Contacts", []),
    enable_ai=False  # Start without AI for speed
)

# Display results
print(f"Total entities analyzed: {results.total_entities}")
print(f"Potential duplicates found: {results.potential_duplicates}")
print(f"High confidence matches (>90%): {len(results.high_confidence_matches)}")
print(f"Medium confidence matches (70-90%): {len(results.medium_confidence_matches)}")

# Examine specific matches
for match in results.high_confidence_matches:
    print(f"\nPotential duplicate found:")
    print(f"  {match['entity_a'].get('Full Name')} <-> {match['entity_b'].get('Full Name')}")
    print(f"  Confidence: {match['confidence_score']:.1f}%")
```

### 2. Comprehensive Multi-Database Analysis

```python
from blackcore.deduplication import DeduplicationEngine
import json
import glob

# Load all JSON databases
databases = {}
for json_file in glob.glob('blackcore/models/json/*.json'):
    with open(json_file, 'r') as f:
        data = json.load(f)
        db_name = list(data.keys())[0]
        databases[db_name] = data[db_name]

# Initialize engine with custom configuration
engine = DeduplicationEngine()
engine.config.update({
    "safety_mode": True,          # No automatic merges
    "enable_ai_analysis": True,   # Use AI for better accuracy
    "auto_merge_threshold": 95.0, # Only merge if >95% confident
    "human_review_threshold": 70.0 # Flag for review if 70-95%
})

# Analyze all databases
results = engine.analyze_all_databases(databases)

# Generate summary report
total_duplicates = sum(r.potential_duplicates for r in results.values())
print(f"\n🔍 Deduplication Analysis Complete")
print(f"📊 Total potential duplicates across all databases: {total_duplicates}")

for db_name, result in results.items():
    if result.potential_duplicates > 0:
        print(f"\n{db_name}:")
        print(f"  - High confidence: {len(result.high_confidence_matches)}")
        print(f"  - Medium confidence: {len(result.medium_confidence_matches)}")
        print(f"  - Low confidence: {len(result.low_confidence_matches)}")
```

## Installation & Setup

### Prerequisites
```bash
# Python 3.11+ required
python --version

# Install base dependencies
pip install -e .

# Optional: Install advanced matching libraries
pip install fuzzywuzzy python-Levenshtein jellyfish

# Optional: Install AI/LLM libraries
pip install anthropic openai
```

### Environment Variables
Create a `.env` file with:
```bash
# Required for AI-powered analysis
ANTHROPIC_API_KEY=your_claude_api_key
OPENAI_API_KEY=your_openai_api_key

# Required for Notion integration (if using)
NOTION_API_KEY=your_notion_api_key
```

### Initial Setup
```python
# Test the installation
python -c "from blackcore.deduplication import DeduplicationEngine; print('✅ Deduplication engine ready!')"
```

## Basic Commands

### 1. Single Database Analysis

```python
from blackcore.deduplication import DeduplicationEngine

engine = DeduplicationEngine()

# Analyze a specific database
results = engine.analyze_database(
    database_name="People & Contacts",
    records=people_records,
    enable_ai=True  # Enable AI analysis
)
```

### 2. Custom Configuration

```python
# Create custom configuration
custom_config = {
    "auto_merge_threshold": 92.0,      # Merge automatically if >92% confident
    "human_review_threshold": 65.0,    # Review if 65-92% confident
    "batch_size": 50,                  # Process in smaller batches
    "enable_ai_analysis": True,        # Use AI for disambiguation
    "safety_mode": True,               # Never auto-merge (dry run)
    "max_ai_requests_per_minute": 20   # Rate limit for AI API
}

# Apply configuration
engine = DeduplicationEngine()
engine.config.update(custom_config)
```

### 3. Export Results for Review

```python
import json
from datetime import datetime

# Run analysis
results = engine.analyze_database("People & Contacts", records)

# Export to JSON for manual review
export_data = {
    "analysis_date": datetime.now().isoformat(),
    "database": "People & Contacts",
    "summary": {
        "total_entities": results.total_entities,
        "potential_duplicates": results.potential_duplicates,
        "confidence_distribution": results.confidence_distribution
    },
    "high_confidence_matches": results.high_confidence_matches,
    "medium_confidence_matches": results.medium_confidence_matches,
    "requires_review": len(results.medium_confidence_matches)
}

with open(f'deduplication_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
    json.dump(export_data, f, indent=2)
    
print(f"✅ Report exported for review")
```

### 4. Human Review Workflow

```python
from blackcore.deduplication import HumanReviewInterface, ReviewDecision

# Initialize review interface
review_interface = HumanReviewInterface(engine.audit_system)

# Get next review task
review_task = review_interface.get_next_review_task("reviewer_name")

if review_task:
    print(f"Review Task: {review_task.task_id}")
    print(f"Entity A: {review_task.entity_pair['entity_a']}")
    print(f"Entity B: {review_task.entity_pair['entity_b']}")
    print(f"Risk Factors: {review_task.risk_factors}")
    print(f"Supporting Evidence: {review_task.supporting_evidence}")
    
    # Make decision
    decision = ReviewDecision(
        task_id=review_task.task_id,
        reviewer_id="reviewer_name",
        decision="merge",  # or "separate" or "defer"
        confidence=85.0,
        reasoning="Same person - email match and similar roles",
        time_spent_seconds=120
    )
    
    # Submit decision
    review_interface.submit_review_decision(decision)
```

## Configuration Guide

### Core Configuration Options

```python
{
    # Confidence Thresholds
    "auto_merge_threshold": 90.0,      # Auto-merge if confidence >= this (default: 90%)
    "human_review_threshold": 70.0,    # Flag for review if >= this (default: 70%)
    
    # Processing Options
    "batch_size": 100,                 # Records to process per batch
    "enable_ai_analysis": True,        # Use AI/LLM for complex cases
    "safety_mode": True,               # Prevent automatic merges (dry run)
    
    # AI Configuration
    "max_ai_requests_per_minute": 10,  # Rate limiting for API calls
    "primary_ai_model": "claude-3-5-sonnet-20241022",
    "fallback_ai_model": "gpt-4",
    "enable_cross_validation": False,  # Use multiple AI models
    
    # Merge Settings
    "merge_strategy": "conservative",  # "conservative" or "aggressive"
    "preserve_all_data": True,         # Keep all fields during merge
    "backup_before_merge": True,       # Create backups
    
    # Graph Analysis
    "enable_graph_analysis": True,     # Use relationship networks
    "min_relationship_strength": 0.3,  # Minimum strength to consider
    "clustering_threshold": 0.6,       # Threshold for entity clusters
}
```

### Entity-Specific Configuration

```python
# Configure per-entity processing
engine.processors["People & Contacts"].config = {
    "name_matching": {
        "use_nicknames": True,         # Tony -> Anthony
        "use_phonetic": True,          # Similar sounding names
        "title_removal": True          # Remove Mr/Mrs/Dr
    },
    "key_fields": ["Email", "Phone"],  # High-weight fields
    "min_name_similarity": 0.6         # Minimum name match score
}

engine.processors["Organizations & Bodies"].config = {
    "abbreviation_detection": True,    # STC -> Swanage Town Council
    "website_normalization": True,     # Ignore https/www differences
    "key_fields": ["Website", "Email"]
}
```

## Interpreting Results

### Understanding Confidence Scores

| Confidence Range | Interpretation | Recommended Action |
|-----------------|----------------|-------------------|
| 95-100% | Near certain match | Safe to auto-merge (if not in safety mode) |
| 90-95% | Very likely match | Auto-merge threshold (configurable) |
| 70-90% | Probable match | Human review recommended |
| 50-70% | Possible match | Detailed investigation needed |
| 30-50% | Unlikely match | Usually separate entities |
| 0-30% | Not a match | Definitely separate entities |

### Reading Match Details

```python
# Example match structure
{
    "entity_a": {
        "id": "person_1",
        "Full Name": "Anthony Smith",
        "Email": "tony.smith@example.com",
        "Organization": "Swanage Town Council"
    },
    "entity_b": {
        "id": "person_2", 
        "Full Name": "Tony Smith",
        "Email": "tony.smith@example.com",
        "Organization": "STC"
    },
    "confidence_score": 95.0,
    "similarity_scores": {
        "Full Name": {
            "exact": 0,
            "fuzzy": 85.4,
            "phonetic": 100,
            "composite": 71.8
        },
        "Email": {
            "exact": 100,
            "composite": 100
        },
        "Organization": {
            "exact": 0,
            "abbreviation_match": True,
            "composite": 90.0
        }
    },
    "ai_analysis": {
        "confidence_score": 98.0,
        "reasoning": "Same person - exact email match, Tony is common nickname for Anthony",
        "risk_assessment": "low"
    },
    "recommended_action": "merge"
}
```

### Identifying False Positives

Common false positive patterns to watch for:

1. **Generic Names**: "Admin User", "Test Account"
2. **Temporal Conflicts**: Same person in different time periods
3. **Role Changes**: Person changed organizations
4. **Family Members**: Similar names, different people

```python
# Check for false positive indicators
def check_false_positive_risk(match):
    risks = []
    
    # Check for generic names
    generic_terms = ["admin", "test", "user", "unknown"]
    name_a = match["entity_a"].get("Full Name", "").lower()
    name_b = match["entity_b"].get("Full Name", "").lower()
    
    if any(term in name_a for term in generic_terms):
        risks.append("Generic name in entity A")
    
    # Check for conflicting data
    if match["entity_a"].get("Email") and match["entity_b"].get("Email"):
        if match["entity_a"]["Email"] != match["entity_b"]["Email"]:
            risks.append("Different email addresses")
    
    return risks
```

## Advanced Features

### 1. Graph-Based Relationship Analysis

```python
from blackcore.deduplication import GraphRelationshipAnalyzer

# Build relationship graph
graph_analyzer = GraphRelationshipAnalyzer()
graph_analyzer.build_relationship_graph(databases)

# Analyze specific entity pairs
entity_pairs = [
    ("People & Contacts:person_1", "People & Contacts:person_2"),
    ("Organizations & Bodies:org_1", "Organizations & Bodies:org_2")
]

graph_results = graph_analyzer.analyze_for_disambiguation(entity_pairs)

print(f"Network Analysis Results:")
print(f"  Total nodes: {graph_results.network_metrics['total_nodes']}")
print(f"  Total relationships: {graph_results.network_metrics['total_edges']}")
print(f"  Entity clusters found: {len(graph_results.entity_clusters)}")

# Use graph context for better decisions
for suggestion in graph_results.disambiguation_suggestions:
    print(f"\nGraph-based insight:")
    print(f"  Entities: {suggestion['entity_a_id']} <-> {suggestion['entity_b_id']}")
    print(f"  Shared connections: {suggestion['shared_connections']}")
    print(f"  Graph confidence: {suggestion['confidence']*100:.1f}%")
```

### 2. Custom Entity Processors

```python
from blackcore.deduplication.entity_processors import BaseEntityProcessor

class CustomDocumentProcessor(BaseEntityProcessor):
    """Custom processor for specialized document matching."""
    
    def __init__(self):
        super().__init__("Custom Documents")
        
    def get_comparison_fields(self):
        return ["Title", "Content Hash", "Author", "Date"]
        
    def get_primary_fields(self):
        return ["Title", "Content Hash"]
        
    def is_potential_duplicate(self, doc_a, doc_b):
        # Custom logic for document comparison
        if doc_a.get("Content Hash") == doc_b.get("Content Hash"):
            return True
            
        title_a = doc_a.get("Title", "").lower()
        title_b = doc_b.get("Title", "").lower()
        
        # Check for versioned documents
        if "v1" in title_a and "v2" in title_b:
            base_title_a = title_a.replace("v1", "").strip()
            base_title_b = title_b.replace("v2", "").strip()
            return base_title_a == base_title_b
            
        return False
        
    def calculate_confidence(self, scores, entity_a=None, entity_b=None):
        # Custom confidence calculation
        if scores.get("Content Hash", {}).get("exact") == 100:
            return 100.0  # Identical content
            
        # Weight different factors
        title_score = scores.get("Title", {}).get("composite", 0)
        author_score = scores.get("Author", {}).get("composite", 0)
        
        return (title_score * 0.6) + (author_score * 0.4)

# Register custom processor
engine.processors["Custom Documents"] = CustomDocumentProcessor()
```

### 3. Batch Processing with Progress

```python
from tqdm import tqdm
import math

def process_large_dataset(engine, database_name, all_records, batch_size=100):
    """Process large datasets in batches with progress tracking."""
    
    total_batches = math.ceil(len(all_records) / batch_size)
    all_results = []
    
    print(f"Processing {len(all_records)} records in {total_batches} batches...")
    
    for i in tqdm(range(0, len(all_records), batch_size)):
        batch = all_records[i:i + batch_size]
        
        # Process batch
        result = engine.analyze_database(
            database_name,
            batch,
            enable_ai=False  # Disable AI for speed in large batches
        )
        
        all_results.append(result)
        
        # Optional: Save intermediate results
        if i % (batch_size * 10) == 0:
            save_intermediate_results(all_results)
    
    # Combine results
    return combine_batch_results(all_results)
```

### 4. Export to Multiple Formats

```python
import pandas as pd
from datetime import datetime

def export_deduplication_results(results, format="excel"):
    """Export results in various formats for review."""
    
    # Prepare data for export
    export_data = []
    
    for match in results.high_confidence_matches:
        export_data.append({
            "Entity_A_ID": match["entity_a"].get("id"),
            "Entity_A_Name": match["entity_a"].get("Full Name", match["entity_a"].get("Organization Name")),
            "Entity_B_ID": match["entity_b"].get("id"),
            "Entity_B_Name": match["entity_b"].get("Full Name", match["entity_b"].get("Organization Name")),
            "Confidence": match["confidence_score"],
            "Match_Type": "High Confidence",
            "Key_Evidence": ", ".join(match.get("key_evidence", [])),
            "Recommended_Action": match.get("recommended_action", "review")
        })
    
    df = pd.DataFrame(export_data)
    
    if format == "excel":
        filename = f"deduplication_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Potential Duplicates', index=False)
            
            # Add summary sheet
            summary_df = pd.DataFrame([{
                "Total Entities": results.total_entities,
                "Potential Duplicates": results.potential_duplicates,
                "High Confidence": len(results.high_confidence_matches),
                "Medium Confidence": len(results.medium_confidence_matches),
                "Low Confidence": len(results.low_confidence_matches)
            }])
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
    elif format == "csv":
        filename = f"deduplication_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(filename, index=False)
        
    print(f"✅ Results exported to {filename}")
    return filename
```

## Best Practices

### 1. Start with Dry Runs

Always begin with safety mode enabled:

```python
# Initial discovery run
engine = DeduplicationEngine()
engine.config["safety_mode"] = True  # Default, but explicit is better
engine.config["enable_ai_analysis"] = False  # Start without AI

# Gradually increase sophistication
# Step 1: Basic fuzzy matching only
results_basic = engine.analyze_database("People & Contacts", records)

# Step 2: Add AI analysis
engine.config["enable_ai_analysis"] = True
results_with_ai = engine.analyze_database("People & Contacts", records)

# Step 3: Review differences
compare_results(results_basic, results_with_ai)
```

### 2. Threshold Tuning Strategy

```python
# Conservative approach for production
PRODUCTION_CONFIG = {
    "auto_merge_threshold": 95.0,      # Very high confidence only
    "human_review_threshold": 75.0,    # Review most matches
    "safety_mode": True,               # Start with dry runs
    "backup_before_merge": True,       # Always backup
    "enable_ai_analysis": True,        # Use all available intelligence
}

# Gradual confidence building
TESTING_PHASES = [
    {"phase": 1, "auto_merge": 98.0, "review": 85.0},  # Very conservative
    {"phase": 2, "auto_merge": 95.0, "review": 80.0},  # Standard conservative
    {"phase": 3, "auto_merge": 92.0, "review": 75.0},  # Balanced
    {"phase": 4, "auto_merge": 90.0, "review": 70.0},  # Default
]
```

### 3. Data Quality Checks

```python
def assess_data_quality(records):
    """Assess data quality before deduplication."""
    
    quality_report = {
        "total_records": len(records),
        "missing_primary_fields": 0,
        "missing_emails": 0,
        "missing_phones": 0,
        "generic_names": 0,
        "duplicate_ids": 0
    }
    
    seen_ids = set()
    
    for record in records:
        # Check primary identifiers
        if not record.get("Full Name") and not record.get("Organization Name"):
            quality_report["missing_primary_fields"] += 1
            
        if not record.get("Email"):
            quality_report["missing_emails"] += 1
            
        if not record.get("Phone"):
            quality_report["missing_phones"] += 1
            
        # Check for generic names
        name = record.get("Full Name", "").lower()
        if any(term in name for term in ["test", "admin", "user", "unknown"]):
            quality_report["generic_names"] += 1
            
        # Check for duplicate IDs
        if record.get("id") in seen_ids:
            quality_report["duplicate_ids"] += 1
        seen_ids.add(record.get("id"))
    
    # Calculate quality score
    quality_score = 100
    quality_score -= (quality_report["missing_primary_fields"] / len(records)) * 20
    quality_score -= (quality_report["generic_names"] / len(records)) * 10
    quality_score -= (quality_report["duplicate_ids"] / len(records)) * 30
    
    quality_report["quality_score"] = max(0, quality_score)
    
    return quality_report
```

### 4. Production Deployment Checklist

```python
def production_readiness_check(engine, test_data):
    """Verify system is ready for production use."""
    
    checklist = {
        "dry_run_tested": False,
        "accuracy_acceptable": False,
        "backup_system_ready": False,
        "rollback_tested": False,
        "audit_trail_verified": False,
        "human_review_workflow": False,
        "performance_acceptable": False
    }
    
    # Test 1: Dry run works
    try:
        engine.config["safety_mode"] = True
        result = engine.analyze_database("Test", test_data[:10])
        checklist["dry_run_tested"] = True
    except Exception as e:
        print(f"❌ Dry run failed: {e}")
        
    # Test 2: Accuracy on known duplicates
    # (assumes test_data has known duplicates)
    accuracy = test_known_duplicates(engine, test_data)
    checklist["accuracy_acceptable"] = accuracy >= 80
    
    # Test 3: Backup system
    checklist["backup_system_ready"] = check_backup_system()
    
    # Test 4: Rollback capability
    checklist["rollback_tested"] = test_rollback_capability(engine)
    
    # Test 5: Audit trail
    checklist["audit_trail_verified"] = verify_audit_trail(engine)
    
    # Test 6: Human review workflow
    checklist["human_review_workflow"] = test_review_workflow(engine)
    
    # Test 7: Performance
    import time
    start = time.time()
    engine.analyze_database("Test", test_data[:1000], enable_ai=False)
    elapsed = time.time() - start
    checklist["performance_acceptable"] = elapsed < 60  # Under 1 minute for 1000 records
    
    # Report
    ready = all(checklist.values())
    print(f"\n{'✅' if ready else '❌'} Production Readiness: {ready}")
    for check, passed in checklist.items():
        print(f"  {'✅' if passed else '❌'} {check}")
    
    return ready
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Low Detection Rate

**Symptom**: Missing obvious duplicates
```python
# Diagnosis
def diagnose_low_detection(engine, known_duplicate_pair):
    """Diagnose why duplicates aren't being detected."""
    
    entity_a, entity_b = known_duplicate_pair
    
    # Check if pre-screening is too strict
    processor = engine.processors["People & Contacts"]
    is_candidate = processor.is_potential_duplicate(entity_a, entity_b)
    print(f"Pre-screening passed: {is_candidate}")
    
    if not is_candidate:
        print("❌ Failed pre-screening - adjust processor logic")
        return
    
    # Check similarity scores
    scores = engine.similarity_scorer.calculate_similarity(
        entity_a, entity_b, processor.get_comparison_fields()
    )
    
    print("\nSimilarity Scores:")
    for field, score in scores.items():
        if isinstance(score, dict):
            print(f"  {field}: {score.get('composite', 0):.1f}%")
    
    # Check confidence calculation
    confidence = processor.calculate_confidence(scores, entity_a, entity_b)
    print(f"\nFinal confidence: {confidence:.1f}%")
    
    # Recommendations
    if confidence < 70:
        print("\n💡 Recommendations:")
        print("  - Lower pre-screening thresholds")
        print("  - Adjust field weights in confidence calculation")
        print("  - Add domain-specific rules (e.g., nickname handling)")
```

**Solution**: Adjust configuration
```python
# More sensitive configuration
engine.config.update({
    "human_review_threshold": 60.0,  # Lower threshold
})

# Adjust processor settings
processor = engine.processors["People & Contacts"]
processor.min_name_similarity = 0.5  # Lower threshold
```

#### 2. Too Many False Positives

**Symptom**: Unrelated entities marked as duplicates
```python
# Add stricter validation
def add_validation_rules(engine):
    """Add custom validation to reduce false positives."""
    
    original_calculate = engine.processors["People & Contacts"].calculate_confidence
    
    def enhanced_calculate(scores, entity_a=None, entity_b=None):
        # Get base confidence
        confidence = original_calculate(scores, entity_a, entity_b)
        
        # Apply penalties for conflicts
        if entity_a and entity_b:
            # Different organizations penalty
            org_a = entity_a.get("Organization", "").lower()
            org_b = entity_b.get("Organization", "").lower()
            if org_a and org_b and org_a != org_b:
                confidence *= 0.8  # 20% penalty
                
            # Different locations penalty
            loc_a = entity_a.get("Location", "").lower()
            loc_b = entity_b.get("Location", "").lower()
            if loc_a and loc_b and not any(word in loc_b for word in loc_a.split()):
                confidence *= 0.7  # 30% penalty
        
        return confidence
    
    engine.processors["People & Contacts"].calculate_confidence = enhanced_calculate
```

#### 3. AI Analysis Errors

**Symptom**: AI analysis failing or giving poor results
```python
# Debug AI analysis
def debug_ai_analysis(engine, entity_pair):
    """Debug AI analysis issues."""
    
    # Test with minimal example
    test_pair = {
        "entity_a": {"Full Name": "John Smith", "Email": "john@example.com"},
        "entity_b": {"Full Name": "J Smith", "Email": "john@example.com"}
    }
    
    try:
        result = engine.llm_analyzer.analyze_entity_pair(
            test_pair["entity_a"],
            test_pair["entity_b"],
            "People & Contacts"
        )
        print(f"✅ AI analysis working: {result.confidence_score:.1f}%")
    except Exception as e:
        print(f"❌ AI analysis error: {e}")
        print("\nTroubleshooting steps:")
        print("1. Check API keys are set correctly")
        print("2. Verify internet connection")
        print("3. Check API rate limits")
        print("4. Try with fallback model")
```

#### 4. Performance Issues

**Symptom**: Analysis taking too long
```python
# Performance optimization
def optimize_performance(engine, records):
    """Optimize for large datasets."""
    
    # 1. Disable AI for initial pass
    engine.config["enable_ai_analysis"] = False
    
    # 2. Increase batch size
    engine.config["batch_size"] = 500
    
    # 3. Use parallel processing
    from concurrent.futures import ProcessPoolExecutor
    import numpy as np
    
    def process_batch(batch_records):
        return engine.analyze_database("Batch", batch_records, enable_ai=False)
    
    # Split into batches
    batches = np.array_split(records, 4)  # 4 parallel processes
    
    with ProcessPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(process_batch, batches))
    
    return combine_results(results)
```

### Error Messages Reference

| Error | Cause | Solution |
|-------|-------|----------|
| `TypeError: 'NoneType' object is not subscriptable` | Missing required field | Add null checks in processors |
| `Rate limit exceeded` | Too many AI API calls | Reduce `max_ai_requests_per_minute` |
| `JSONDecodeError` | Corrupted data file | Validate JSON before processing |
| `Memory error` | Dataset too large | Use batch processing |
| `Connection timeout` | AI API unreachable | Check internet/firewall settings |

## API Reference

### Core Classes

#### DeduplicationEngine
```python
class DeduplicationEngine:
    """Main deduplication orchestrator."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize with optional config file."""
        
    def analyze_database(
        self, 
        database_name: str, 
        records: List[Dict[str, Any]], 
        enable_ai: bool = True
    ) -> DeduplicationResult:
        """Analyze single database for duplicates."""
        
    def analyze_all_databases(
        self, 
        databases: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, DeduplicationResult]:
        """Analyze multiple databases."""
```

#### DeduplicationResult
```python
@dataclass
class DeduplicationResult:
    """Results from deduplication analysis."""
    total_entities: int
    potential_duplicates: int = 0
    high_confidence_matches: List[Dict[str, Any]]
    medium_confidence_matches: List[Dict[str, Any]]
    low_confidence_matches: List[Dict[str, Any]]
    auto_merged: int = 0
    flagged_for_review: int = 0
    processing_time: float = 0.0
    confidence_distribution: Dict[str, int]
```

#### Configuration Options
```python
DEFAULT_CONFIG = {
    # Thresholds
    "auto_merge_threshold": 90.0,
    "human_review_threshold": 70.0,
    
    # Processing
    "batch_size": 100,
    "enable_ai_analysis": True,
    "safety_mode": True,
    
    # AI Settings
    "max_ai_requests_per_minute": 10,
    "primary_ai_model": "claude-3-5-sonnet-20241022",
    "fallback_ai_model": "gpt-4",
    
    # Merge Settings
    "merge_strategy": "conservative",
    "preserve_all_data": True,
    "backup_before_merge": True,
    
    # Graph Analysis
    "enable_graph_analysis": True,
    "min_relationship_strength": 0.3,
    "clustering_threshold": 0.6
}
```

### Utility Functions

```python
# Get statistics
stats = engine.get_statistics()
print(f"Total comparisons: {stats['engine_stats']['total_comparisons']}")
print(f"AI analyses: {stats['engine_stats']['ai_analyses_performed']}")

# Get audit history
from blackcore.deduplication import DeduplicationAudit
audit = DeduplicationAudit()
history = audit.get_audit_history(days_back=7)

# Export results
export_deduplication_results(results, format="excel")

# Check data quality
quality_report = assess_data_quality(records)
print(f"Data quality score: {quality_report['quality_score']:.1f}%")
```

## Conclusion

The Blackcore Deduplication Engine provides enterprise-grade entity resolution with:
- 🛡️ **Safety-first design** - No accidental data loss
- 🎯 **High accuracy** - Multi-layer analysis with AI
- 📊 **Complete transparency** - Detailed match explanations
- 🔄 **Full reversibility** - Comprehensive audit trails
- 👥 **Human oversight** - Review workflows for uncertain cases

Start with dry runs, gradually build confidence, and deploy to production with complete assurance that your intelligence data integrity is maintained while eliminating duplicates efficiently.

For additional support:
- Review test examples in `scripts/test_deduplication_system.py`
- Check implementation details in `blackcore/deduplication/`
- Run diagnostics with `scripts/diagnose_deduplication.py`