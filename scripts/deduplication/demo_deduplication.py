#!/usr/bin/env python3
"""
Purpose: A simple demonstration script for the MVP (Minimum Viable Product) version of the deduplication feature.
Utility: It uses a hardcoded sample transcript and a basic configuration to show the deduplication logic in action, printing the expected outcomes to the console. It's useful for quick, isolated tests of the basic matching rules.
"""
#!/usr/bin/env python3
"""
Demo script showing deduplication in action for MVP Black Mini
"""

from datetime import datetime
from blackcore.minimal.models import TranscriptInput, Config, TranscriptSource
from blackcore.minimal.transcript_processor import TranscriptProcessor

# Sample transcript with entities that should match existing ones
sample_transcript = """
Meeting Notes - January 15, 2024

Attendees:
- Tony Smith from Nassau Council (email: anthony.smith@nassau.gov)
- Bob Johnson, IT Director
- Liz Taylor from Nassau Council Inc

Discussion:
Tony mentioned that the council is looking to upgrade their permit system.
Bob Johnson will review the technical requirements.
Elizabeth Taylor will handle the budget approvals.

Action Items:
1. Tony to provide current system documentation
2. Bob to assess integration requirements  
3. Liz to prepare budget proposal

Issues:
- Unauthorized construction at North Beach needs investigation
- Nassau Council received complaints about beach access
"""


def main():
    print("🚀 MVP Black Mini - Deduplication Demo\n")

    # Create test config
    config = Config()
    config.processing.verbose = True
    config.processing.dry_run = True  # Don't actually sync to Notion

    # Create processor
    processor = TranscriptProcessor(config=config)

    # Create transcript
    transcript = TranscriptInput(
        title="Council Meeting - System Upgrade Discussion",
        content=sample_transcript,
        date=datetime.now(),
        source=TranscriptSource.GOOGLE_MEET,
    )

    print("📝 Processing transcript...")
    print("-" * 60)

    # Process and show results
    result = processor.process_transcript(transcript)

    print("\n" + "=" * 60)
    print("🔍 DEDUPLICATION EXAMPLES:")
    print("=" * 60)
    print("\n✅ These would be matched as duplicates:")
    print("  • 'Tony Smith' → 'Anthony Smith' (nickname match)")
    print("  • 'Bob Johnson' → 'Robert Johnson' (nickname match)")
    print("  • 'Liz Taylor' → 'Elizabeth Taylor' (nickname match)")
    print("  • 'Nassau Council Inc' → 'Nassau Council' (suffix removal)")
    print("\n❌ These would create new entities:")
    print("  • New tasks and transgressions (no dedup for these types)")
    print("\n📊 Matching scores:")
    print("  • Email match: 95% (very high confidence)")
    print("  • Phone match: 92% (high confidence)")
    print("  • Nickname match: 90% (high confidence)")
    print("  • Same org boost: +15% (when names partially match)")


if __name__ == "__main__":
    main()
