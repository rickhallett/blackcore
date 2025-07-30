#!/usr/bin/env python3
"""
Demo script showing LLM-based deduplication in action
"""

import os
from datetime import datetime
from blackcore.minimal.models import (
    TranscriptInput,
    Config,
    TranscriptSource,
    ProcessingConfig,
)
from blackcore.minimal.transcript_processor import TranscriptProcessor
from blackcore.minimal.llm_scorer import LLMScorer

# Sample transcript with complex entity variations
sample_transcript = """
Meeting Notes - January 20, 2024

Attendees:
- Tony Smith from Nassau Municipal Council (anthony.smith@nassau.gov)
- Dr. Elizabeth Taylor-Johnson, Chief Financial Officer at Nassau Council
- Bob Johnson from IT (might be the same as Robert Johnson we met last week?)
- José Martinez (also goes by Joe Martinez in some documents)
- Alexandra "Alex" Chen from the Mayor's office

Discussion:
Tony mentioned that Anthony Smith (yes, same person) will be leading the permit system upgrade.
Elizabeth Taylor-Johnson (some know her as Liz Taylor) needs the budget by Friday.
Bob or Bobby Johnson - not sure if it's the same Robert from IT - will handle tech specs.
Joe Martinez (José on official docs) is coordinating with the Spanish-speaking community.
Alex Chen has been working closely with Alexandra Chen from the Mayor's team (same person!).

Organizations mentioned:
- Nassau Municipal Council (also referred to as Nassau Council)
- City of Nassau Council Inc. (the official incorporated name)
- IT Department of Nassau (part of the council)
- Mayor's Office of Nassau
- Nassau Community Outreach (NCO)

Action Items:
1. Tony/Anthony to provide system requirements
2. Liz (Dr. Taylor-Johnson) to prepare budget proposal
3. Bob/Bobby/Robert to assess technical needs
4. José/Joe to translate materials
5. Alexandra to coordinate with Mayor's office

Notes:
- There was confusion about whether "Nassau Council" and "Nassau Municipal Council" are the same
- Need to verify if Bob Johnson and Robert Johnson are the same person
- José prefers to be called Joe in informal settings
"""


def demo_simple_vs_llm():
    """Demonstrate the difference between simple and LLM scoring."""
    print("🔍 DEDUPLICATION COMPARISON: Simple vs LLM\n")
    print("=" * 80)

    # Test entities
    test_cases = [
        # Person examples
        {
            "entity1": {"name": "Tony Smith", "email": "anthony.smith@nassau.gov"},
            "entity2": {"name": "Anthony Smith", "email": "asmith@nassau.gov"},
            "type": "person",
            "description": "Nickname with email variation",
        },
        {
            "entity1": {"name": "Dr. Elizabeth Taylor-Johnson", "title": "CFO"},
            "entity2": {"name": "Liz Taylor", "organization": "Nassau Council"},
            "type": "person",
            "description": "Formal name vs nickname with title",
        },
        {
            "entity1": {"name": "José Martinez", "email": "jose@nassau.gov"},
            "entity2": {"name": "Joe Martinez", "department": "Community Outreach"},
            "type": "person",
            "description": "Cultural name variation",
        },
        {
            "entity1": {"name": "Bob Johnson", "department": "IT"},
            "entity2": {"name": "Robert Johnson", "role": "IT Director"},
            "type": "person",
            "description": "Nickname with same department",
        },
        # Organization examples
        {
            "entity1": {"name": "Nassau Municipal Council"},
            "entity2": {"name": "City of Nassau Council Inc."},
            "type": "organization",
            "description": "Official name vs common name",
        },
        {
            "entity1": {"name": "Nassau Council"},
            "entity2": {"name": "Nassau Community Outreach"},
            "type": "organization",
            "description": "Similar but different organizations",
        },
    ]

    # Initialize scorers
    from blackcore.minimal.simple_scorer import SimpleScorer

    simple_scorer = SimpleScorer()

    # Only initialize LLM scorer if API key is available
    llm_scorer = None
    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("AI_API_KEY")
    if api_key:
        try:
            llm_scorer = LLMScorer(api_key=api_key)
            print("✅ LLM Scorer initialized with Claude 3.5 Haiku\n")
        except Exception as e:
            print(f"⚠️  Could not initialize LLM scorer: {e}")
            print("   Running with simple scorer only\n")
    else:
        print("⚠️  No ANTHROPIC_API_KEY found in environment")
        print("   Set ANTHROPIC_API_KEY to enable LLM scoring\n")

    # Compare scoring methods
    for test in test_cases:
        print(f"\n{'=' * 60}")
        print(f"📋 {test['description']}")
        print(f"   Entity 1: {test['entity1']}")
        print(f"   Entity 2: {test['entity2']}")
        print(f"   Type: {test['type']}")
        print("-" * 60)

        # Simple scorer
        simple_score, simple_reason = simple_scorer.score_entities(
            test["entity1"], test["entity2"], test["type"]
        )
        print(f"🔧 Simple Score: {simple_score:.1f}% - {simple_reason}")

        # LLM scorer (if available)
        if llm_scorer:
            try:
                llm_score, llm_reason, llm_details = llm_scorer.score_entities(
                    test["entity1"],
                    test["entity2"],
                    test["type"],
                    context={"source_documents": ["Meeting Notes Demo"]},
                )
                print(f"🤖 LLM Score: {llm_score:.1f}% - {llm_reason}")

                if llm_details.get("evidence"):
                    print("   Evidence:")
                    for evidence in llm_details["evidence"][:3]:
                        print(f"   • {evidence}")

                # Show dimension scores if available
                if llm_details.get("dimensions"):
                    dims = llm_details["dimensions"]
                    if any(dims.values()):
                        print("   Dimensions analyzed:")
                        for dim, score in dims.items():
                            if score > 0:
                                print(f"   • {dim}: {score}%")

            except Exception as e:
                print(f"🤖 LLM Score: Error - {str(e)}")


def demo_full_pipeline():
    """Demonstrate full pipeline with LLM deduplication."""
    print("\n\n" + "=" * 80)
    print("🚀 FULL PIPELINE DEMO WITH LLM DEDUPLICATION")
    print("=" * 80 + "\n")

    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("AI_API_KEY")
    if not api_key:
        print("⚠️  No AI API key found. Please set ANTHROPIC_API_KEY")
        print("   The pipeline will use simple deduplication as fallback")

    # Create config with LLM scorer
    config = Config(
        notion={
            "api_key": os.getenv("NOTION_API_KEY", "dummy_key_for_demo"),
            "databases": {
                "people": {"id": "dummy_id"},
                "organizations": {"id": "dummy_id"},
                "tasks": {"id": "dummy_id"},
                "transcripts": {"id": "dummy_id"},
                "transgressions": {"id": "dummy_id"},
            },
        },
        ai={
            "provider": "claude",
            "api_key": api_key or "dummy_key_for_demo",
            "model": "claude-3-sonnet-20240229",
        },
        processing=ProcessingConfig(
            verbose=True,
            dry_run=True,  # Don't actually sync to Notion
            enable_deduplication=True,
            deduplication_scorer="llm" if api_key else "simple",
            llm_scorer_config={
                "model": "claude-3-5-haiku-20241022",
                "temperature": 0.1,
                "cache_ttl": 3600,
            },
        ),
    )

    # Create processor
    processor = TranscriptProcessor(config=config)

    # Create transcript
    transcript = TranscriptInput(
        title="Complex Entity Meeting - LLM Deduplication Demo",
        content=sample_transcript,
        date=datetime.now(),
        source=TranscriptSource.GOOGLE_MEET,
    )

    print("📝 Processing transcript with LLM deduplication...")
    print("-" * 60)

    # Process
    processor.process_transcript(transcript)

    print("\n" + "=" * 60)
    print("✨ LLM DEDUPLICATION ADVANTAGES:")
    print("=" * 60)
    print("\n1. **Cultural Name Understanding**:")
    print("   • José ↔ Joe Martinez (cultural variation)")
    print("   • No hardcoded mappings needed!")

    print("\n2. **Complex Name Patterns**:")
    print("   • Dr. Elizabeth Taylor-Johnson ↔ Liz Taylor")
    print("   • Handles titles, hyphenated names, formal/informal")

    print("\n3. **Contextual Analysis**:")
    print("   • Uses email domains for validation")
    print("   • Considers department/role information")
    print("   • Analyzes temporal and social patterns")

    print("\n4. **Organization Intelligence**:")
    print("   • Nassau Municipal Council ↔ City of Nassau Council Inc.")
    print("   • Understands official vs common names")
    print("   • No suffix removal rules needed")

    print("\n5. **Explainable Decisions**:")
    print("   • Provides evidence for each match")
    print("   • Shows confidence dimensions")
    print("   • Clear reasoning for decisions")


if __name__ == "__main__":
    # Run comparison demo
    demo_simple_vs_llm()

    # Run full pipeline demo
    demo_full_pipeline()

    print("\n\n" + "=" * 80)
    print("📚 To enable LLM deduplication in your project:")
    print("=" * 80)
    print("1. Set your Anthropic API key:")
    print("   export ANTHROPIC_API_KEY='your-key-here'")
    print("\n2. Update your config:")
    print('   "deduplication_scorer": "llm"')
    print("\n3. Run your transcript processing!")
    print("\nSee docs/llm-scorer-migration-guide.md for details.")
